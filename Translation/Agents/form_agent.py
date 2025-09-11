"""
Form Translation Agent
Specialized agent for translating VB6 forms (.frm files) to C# WinForms.

This agent handles:
- VB6 form structure parsing and translation using LLM
- Complete form-to-WinForms conversion with RAG context
- Event handler and control translation
- Designer file generation
"""

import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import re

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from Core.analyzer import VB6File
from Utils.vb6_parser import VB6ParsedFile
from Utils.prompt_templates import get_prompt_manager
from Utils.model_interface import OllamaClient, ClaudeClient, ModelResponse
from Utils.translation_utils import get_namespace_from_path, sanitize_csharp_name, clean_llm_response, generate_using_statements


@dataclass
class CSharpComponent:
    """Represents a translated C# component"""
    name: str
    content: str
    file_type: str  # .cs, .Designer.cs, .resx, etc.
    namespace: str
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CSharpForm:
    """Represents a translated C# WinForms form"""
    name: str
    namespace: str
    form_class_code: str
    designer_code: str
    using_statements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTranslationAgent:
    """Base class for all translation agents"""
    
    def __init__(self, name: str, model_client: Union[OllamaClient, ClaudeClient]):
        self.name = name
        self.model_client = model_client
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def translate(self, vb6_file: VB6File) -> CSharpComponent:
        """Translate a VB6 file to C#"""
        raise NotImplementedError("Subclasses must implement translate method")


class FormAgent(BaseTranslationAgent):
    """
    Form Translation Agent
    Specialized agent for translating VB6 forms (.frm files) to C# WinForms.

    This agent handles:
    - VB6 form structure parsing and complete translation using LLM
    - Control mapping and event handler translation
    - Designer file generation with proper WinForms structure
    - VB6 to C# WinForms conversion with RAG context
    """
    
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient], project_root: Path = None):
        super().__init__("FormAgent", model_client)
        self.prompt_manager = get_prompt_manager()
        self.project_root = project_root
        
        # Initialize RAG manager for context-aware translation
        try:
            from Knowledge.rag_manager import RAGManager
            self.rag_manager = RAGManager()
            self.logger.info("RAG manager initialized successfully")
        except Exception as e:
            self.rag_manager = None
            self.logger.warning(f"RAG manager not available: {e}")
    
    def translate(self, vb6_file: VB6File, project_files: dict = None) -> CSharpComponent:
        """Translate VB6 form to C# form - implements BaseTranslationAgent interface"""
        self.logger.info(f"Translating form: {vb6_file.name}")
        
        try:
            # Use parsed_data if available, otherwise use VB6File directly
            if vb6_file.parsed_data:
                csharp_form = self.translate_form(vb6_file.parsed_data, project_files)
            else:
                csharp_form = self.translate_form(vb6_file, project_files)
            
            if csharp_form:
                # Convert CSharpForm to CSharpComponent for main form file
                form_component = CSharpComponent(
                    name=csharp_form.name,
                    content=csharp_form.form_class_code,
                    file_type="cs",
                    namespace=csharp_form.namespace,
                    metadata=csharp_form.metadata
                )
                
                # Store designer code separately in metadata for later saving
                form_component.metadata["designer_code"] = csharp_form.designer_code
                form_component.metadata["using_statements"] = csharp_form.using_statements
                
                return form_component
            else:
                raise Exception("translate_form returned None - translation failed")
                
        except Exception as e:
            self.logger.error(f"FormAgent translation failed for {vb6_file.name}: {e}")
            raise Exception(f"Failed to translate VB6 form '{vb6_file.name}': {e}") from e
    
    def translate_form(self, parsed_form, project_files: dict = None) -> Optional[CSharpForm]:
        """
        Translate a VB6 form (.frm) to C# WinForms using LLM with RAG
        
        Args:
            parsed_form: Parsed VB6 form file
            project_files: Dictionary of all project files for dependency resolution
            
        Returns:
            CSharpForm object containing translated form and designer code
        """
        self.logger.info(f"Translating VB6 form: {parsed_form.name}")
        
        try:
            # Get file path - handle both VB6File and VB6ParsedFile
            file_path = getattr(parsed_form, 'file_path', None) or getattr(parsed_form, 'path', None)
            if not file_path:
                raise Exception(f"No valid file path found for {parsed_form.name}")
            
            # Read the VB6 source code
            with open(file_path, 'r', encoding='latin-1') as f:
                vb6_content = f.read()
            
            # Get RAG context for enhanced translation
            rag_context = self._get_rag_context(vb6_content, "form", project_files)
            
            # Note: dependency_context removed - now using smart using statements generation
            
            # Create enhanced messages with RAG context for form translation
            form_name = sanitize_csharp_name(parsed_form.name)
            messages = self._create_enhanced_messages(
                "vb6_to_winforms", 
                vb6_content, 
                rag_context, 
                form_name, 
                vb6_file=parsed_form,
                project_files=project_files
            )
            
            if not messages:
                raise Exception("Failed to create prompt messages")
            
            response = self.model_client.chat(messages)
            
            if not response or not response.content:
                raise Exception("Empty response from LLM")
            
            print("--------------------------------")
            print(response.content)
            print("--------------------------------")
            
            # Parse the LLM response to extract form and designer code
            form_code, designer_code = self._parse_llm_form_response(response.content)
            
            
            namespace = get_namespace_from_path(file_path, self.project_root)
            
            
            return CSharpForm(
                name=sanitize_csharp_name(parsed_form.name),
                namespace=namespace,
                form_class_code=form_code,
                designer_code=designer_code,
                using_statements=[],  # LLM handles using statements in the code
                metadata={
                    "original_file": str(file_path),
                    "translation_method": "llm_with_rag",
                    "model": response.model,
                    "provider": response.provider,
                    "rag_context_used": bool(rag_context)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Translation failed for {parsed_form.name}: {e}")
            return None
    
    def _get_rag_context(self, vb6_code: str, file_type: str, project_files: dict = None) -> str:
        """Get RAG context from similar patterns and project class information"""
        context_parts = []
        
        # Get RAG patterns if available
        if self.rag_manager:
            try:
                suggestions = []
                
                # Get form-specific patterns
                form_suggestions = self.rag_manager.retrieve_similar_patterns(vb6_code, top_k=2, category="form")
                if form_suggestions:
                    suggestions.extend(form_suggestions)
                
                # Get business logic patterns
                class_suggestions = self.rag_manager.retrieve_similar_patterns(vb6_code, top_k=2, category="class")
                if class_suggestions:
                    suggestions.extend(class_suggestions)
                
                # Try business_logic category
                try:
                    business_suggestions = self.rag_manager.retrieve_similar_patterns(vb6_code, top_k=1, category="business_logic")
                    if business_suggestions:
                        suggestions.extend(business_suggestions)
                except:
                    pass
                
                if suggestions:
                    context_parts.append("Relevant form translation patterns for reference:")
                    for i, match in enumerate(suggestions[:3], 1):
                        context_parts.append(f"\n{i}. Pattern (Score: {match.similarity_score:.3f}):")
                        context_parts.append(f"   VB6: {match.pattern.vb6_code}")
                        context_parts.append(f"   C#: {match.pattern.csharp_code}")
                        context_parts.append(f"   Category: {match.pattern.category}")
                        
            except Exception as e:
                self.logger.debug(f"RAG context generation failed: {e}")
        
        # Add project class information
        if project_files:
            context_parts.append("\nAVAILABLE PROJECT CLASSES:")
            for file_name, file_info in project_files.items():
                if hasattr(file_info, 'file_type') and file_info.file_type in ('cls', 'bas'):
                    class_name = sanitize_csharp_name(file_name)
                    context_parts.append(f"- {class_name} (from {file_name})")
        
        return "\n".join(context_parts)
    
    
    def _create_enhanced_messages(self, prompt_type: str, vb6_content: str, rag_context: str, form_name: str = "MainForm", vb6_file=None, project_files: dict = None) -> List[Dict[str, str]]:
        """Create messages with RAG context enhancement and smart using statements"""
        
        # Generate using statements and namespace from VB6 file
        using_statements = generate_using_statements(vb6_file, project_files or {}, self.project_root)
        
        # Get file path - handle both VB6File and VB6ParsedFile
        file_path = getattr(vb6_file, 'file_path', None) or getattr(vb6_file, 'path', None)
        namespace = get_namespace_from_path(file_path, self.project_root) if file_path else "Forms"
        
        # Get messages from prompt manager with context parameter
        messages = self.prompt_manager.create_messages(
            prompt_type, 
            source_code=vb6_content,
            context=rag_context,
            using_statements=using_statements,
            form_name=form_name,
            namespace=namespace
        )
        
        return messages if messages else []
    
    
    def _parse_llm_form_response(self, response_content: str) -> tuple:
        """
        Parse LLM response using reliable delimiters to extract form and designer code
        Returns (form_code, designer_code)
        """
        import re
        
        self.logger.info("Parsing LLM form response...")
        
        # Extract form class using delimiters
        form_match = re.search(
            r'<!-- FORM_CLASS_START -->(.*?)<!-- FORM_CLASS_END -->', 
            response_content, 
            re.DOTALL
        )
        
        # Extract designer class using delimiters
        designer_match = re.search(
            r'<!-- DESIGNER_CLASS_START -->(.*?)<!-- DESIGNER_CLASS_END -->', 
            response_content, 
            re.DOTALL
        )
        
        # Check for missing end delimiters and try to handle gracefully
        if not form_match:
            # Try to find form start without end delimiter
            form_start_match = re.search(
                r'<!-- FORM_CLASS_START -->(.*?)(?=<!-- DESIGNER_CLASS_START --|$)', 
                response_content, 
                re.DOTALL
            )
            if form_start_match:
                self.logger.warning("Found FORM_CLASS_START but missing FORM_CLASS_END delimiter")
                form_match = form_start_match
        
        if not designer_match:
            # Try to find designer start without end delimiter
            designer_start_match = re.search(
                r'<!-- DESIGNER_CLASS_START -->(.*?)$', 
                response_content, 
                re.DOTALL
            )
            if designer_start_match:
                self.logger.warning("Found DESIGNER_CLASS_START but missing DESIGNER_CLASS_END delimiter")
                designer_match = designer_start_match
        
        
        form_code = form_match.group(1).strip()
        designer_code = designer_match.group(1).strip()
        
        self.logger.info("Successfully extracted both form and designer code using delimiters")
        
        # Clean the extracted code
        form_code = clean_llm_response(form_code)
        designer_code = clean_llm_response(designer_code)
        
        return form_code, designer_code
        

    



def main():
    """Test the FormAgent with Claude client on mainfrm.frm"""
    import sys
    from pathlib import Path
    
    # Add project root to path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    # Setup logging
    from Utils.logging_config import setup_logging
    setup_logging(task_name="translation")
    
    from Utils.vb6_parser import VB6Parser
    from Utils.model_interface import ClaudeClient
    
    # Use mainfrm.frm file specifically
    vb6_file = Path(__file__).parent.parent.parent / "Data" / "Input" / "BMI" / "mainfrm.frm"
    
    if not vb6_file.exists():
        print(f"File not found: {vb6_file}")
        sys.exit(1)
    
    print(f"Translating VB6 form: {vb6_file}")
    
    # Parse VB6 file
    parser = VB6Parser()
    parsed_file = parser.parse_file(vb6_file)
    
    if not parsed_file:
        print(f"Failed to parse file: {vb6_file}")
        sys.exit(1)
    
    # Initialize agent with Claude client
    try:
        claude_client = ClaudeClient()
        agent = FormAgent(claude_client)
        print("Initialized FormAgent with Claude client")
    except Exception as e:
        print(f"Failed to initialize Claude client: {e}")
        print("Make sure CLAUDE_API_KEY is set in your environment")
        sys.exit(1)
    
    # Translate form
    try:
        print("Starting translation...")
        csharp_form = agent.translate_form(parsed_file)
        
        if csharp_form is None:
            print("Translation failed - check logs for details")
            sys.exit(1)
        
        print("Translation successful!")
        print(f"Form: {csharp_form.name}")
        print(f"Namespace: {csharp_form.namespace}")
        print(f"Translation method: {csharp_form.metadata.get('translation_method', 'unknown')}")
        print(f"RAG context used: {csharp_form.metadata.get('rag_context_used', False)}")
        
        # Save output files
        output_dir = Path(__file__).parent.parent.parent / "Data" / "Output" / "BMI_Form_Test"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save form class file
        form_file_path = output_dir / f"{csharp_form.name}.cs"
        with open(form_file_path, 'w', encoding='utf-8') as f:
            if csharp_form.using_statements:
                f.write('\n'.join(csharp_form.using_statements))
                f.write('\n\n')
            f.write(csharp_form.form_class_code)
        
        # Save designer file
        designer_file_path = output_dir / f"{csharp_form.name}.Designer.cs"
        with open(designer_file_path, 'w', encoding='utf-8') as f:
            if csharp_form.using_statements:
                f.write('\n'.join(csharp_form.using_statements))
                f.write('\n\n')
            f.write(csharp_form.designer_code)
        
        print(f"Files saved to:")
        print(f"  - {form_file_path}")
        print(f"  - {designer_file_path}")
        
    except Exception as e:
        print(f"Translation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
