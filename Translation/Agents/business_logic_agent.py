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
class CSharpClass:
    """Represents a translated C# class or static class"""
    name: str
    namespace: str
    class_code: str
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


class BusinessLogicAgent(BaseTranslationAgent):
    """
    Business Logic Translation Agent
    Specialized agent for translating VB6 modules (.bas) and class files (.cls) to C#.

    This agent handles:
    - VB6 module/class structure parsing
    - Function/Sub to C# method translation
    - VB6 error handling conversion (On Error GoTo -> try/catch)
    - Data type conversion (Variant, Integer, etc.)
    - Property translation (Property Get/Let/Set)
    - VB6-specific constructs (Select Case, Option Explicit, etc.)
    """
        
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient], project_root: Path = None):
        super().__init__("BusinessLogicAgent", model_client)
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
        """Translate VB6 module/class to C# - implements BaseTranslationAgent interface"""
        self.logger.info(f"Translating business logic: {vb6_file.name}")
        
        try:
            # Use parsed_data if available, otherwise use VB6File directly
            if vb6_file.parsed_data:
                csharp_class = self.translate_module(vb6_file.parsed_data, project_files)
            else:
                csharp_class = self.translate_module(vb6_file, project_files)
            
            if csharp_class:
                # Convert CSharpClass to CSharpComponent
                return CSharpComponent(
                    name=csharp_class.name,
                    content=csharp_class.class_code,
                    file_type="cs",
                    namespace=csharp_class.namespace,
                    metadata=csharp_class.metadata
                )
            else:
                raise Exception("translate_class returned None - translation failed")
                
        except Exception as e:
            self.logger.error(f"BusinessLogicAgent translation failed for {vb6_file.name}: {e}")
            raise Exception(f"Failed to translate VB6 business logic '{vb6_file.name}': {e}") from e

    
    def translate_module(self, parsed_file, project_files: dict = None) -> Optional[CSharpClass]:
        """
        Translate a VB6 module (.bas) or class (.cls) to C# using LLM with RAG
        
        Args:
            parsed_file: Parsed VB6 file
            project_files: Dictionary of all project files for dependency resolution
            
        Returns:
            CSharpClass object containing translated code
        """
        self.logger.info(f"Translating VB6 {parsed_file.file_type}: {parsed_file.name}")
        
        try:
            # Get file path - handle both VB6File and VB6ParsedFile
            file_path = getattr(parsed_file, 'file_path', None) or getattr(parsed_file, 'path', None)
            if not file_path:
                raise Exception(f"No valid file path found for {parsed_file.name}")
            
            # Read the VB6 source code
            with open(file_path, 'r', encoding='latin-1') as f:
                vb6_content = f.read()
            
            # Select appropriate prompt based on file type
            prompt_type = "vb6_class_to_csharp" if parsed_file.file_type == 'class' else "vb6_module_to_csharp"
            
            # Get RAG context for enhanced translation
            rag_context = self._get_rag_context(vb6_content, parsed_file.file_type)
            print("--------------------------------")
            print(rag_context)
            print("--------------------------------")
            # Create enhanced messages with RAG context and smart using statements
            messages = self._create_enhanced_messages(
                prompt_type, 
                vb6_content, 
                rag_context, 
                vb6_file=parsed_file,
                project_files=project_files
            )
            
            if not messages:
                raise Exception("Failed to create prompt messages")
            
            
            response = self.model_client.chat(messages)
            
            if not response or not response.content:
                raise Exception("Empty response from LLM")
            
            # Clean and process the response
            translated_code = clean_llm_response(response.content)
            
            # Get file path - handle both VB6File and VB6ParsedFile
            file_path = getattr(parsed_file, 'file_path', None) or getattr(parsed_file, 'path', None)
            namespace = get_namespace_from_path(file_path, self.project_root) if file_path else "Translated"
            
            return CSharpClass(
                name=sanitize_csharp_name(parsed_file.name),
                namespace=namespace,
                class_code=translated_code,
                using_statements=[],  # LLM handles using statements in the code
                metadata={
                    "original_file": str(file_path) if file_path else "unknown",
                    "model": response.model,
                    "provider": response.provider,
                    "rag_context_used": bool(rag_context)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Translation failed for {parsed_file.name}: {e}")
            return None
    
    
    def _get_rag_context(self, vb6_code: str, file_type: str) -> str:
        """Get RAG context from similar patterns"""
        if not self.rag_manager:
            self.logger.warning("RAG manager not available")
            return ""
        
        try:
            # Map to RAG categories used by the knowledge loader
            # "class" covers business_logic patterns; modules also map best to "class"
            rag_category = "class"
            
            # Get pattern suggestions from RAG manager
            suggestions = self.rag_manager.retrieve_similar_patterns(vb6_code, category=rag_category)
            
            if not suggestions:
                return ""
            
            # Build context string from top patterns
            context_parts = ["Relevant translation patterns for reference:"]
            for i, match in enumerate(suggestions[:3], 1):  # Top 3 patterns
                context_parts.append(f"\n{i}. Pattern (Score: {match.similarity_score:.3f}):")
                context_parts.append(f"   VB6: {match.pattern.vb6_code}")
                context_parts.append(f"   C#: {match.pattern.csharp_code}")
                context_parts.append(f"   Category: {match.pattern.category}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.debug(f"RAG context generation failed: {e}")
            return ""
    
    def _create_enhanced_messages(self, prompt_type: str, vb6_content: str, rag_context: str, vb6_file=None, project_files: dict = None) -> List[Dict[str, str]]:
        
        using_statements = generate_using_statements(vb6_file, project_files or {}, self.project_root)
        
        # Get file path - handle both VB6File and VB6ParsedFile
        file_path = getattr(vb6_file, 'file_path', None) or getattr(vb6_file, 'path', None)
        namespace = get_namespace_from_path(file_path, self.project_root) if file_path else "Translated"
        
        messages = self.prompt_manager.create_messages(
            prompt_type, 
            source_code=vb6_content,
            context=rag_context if rag_context else "",
            using_statements=using_statements,
            namespace=namespace
        )
        
        return messages if messages else []
    


def main():
    """Test the BusinessLogicAgent with Claude client on CPerson.cls"""
    import sys
    from pathlib import Path
    
    # Add project root to path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    # Setup logging
    from Utils.logging_config import setup_logging
    setup_logging(task_name="translation")
    
    from Utils.vb6_parser import VB6Parser
    from Utils.model_interface import ClaudeClient
    
    # Use CPerson.cls file specifically
    vb6_file = Path(__file__).parent.parent.parent / "Data" / "Input" / "BMI" / "CPerson.cls"
    
    if not vb6_file.exists():
        print(f"File not found: {vb6_file}")
        sys.exit(1)
    
    print(f"Translating VB6 file: {vb6_file}")
    
    # Parse VB6 file
    parser = VB6Parser()
    parsed_file = parser.parse_file(vb6_file)
    
    if not parsed_file:
        print(f"Failed to parse file: {vb6_file}")
        sys.exit(1)
    
    # Initialize agent with Claude client
    try:
        claude_client = ClaudeClient()
        agent = BusinessLogicAgent(claude_client)
        print("Initialized BusinessLogicAgent with Claude client")
    except Exception as e:
        print(f"Failed to initialize Claude client: {e}")
        print("Make sure CLAUDE_API_KEY is set in your environment")
        sys.exit(1)
    
    # Translate file
    try:
        print("Starting translation...")
        csharp_class = agent.translate_module(parsed_file)
        
        print("Translation successful!")
        print(f"Class: {csharp_class.name}")
        print(f"Namespace: {csharp_class.namespace}")
       
        
        # Save output file
        output_dir = Path(__file__).parent.parent.parent / "Data" / "Output" / "BMI_Claude_Test_new_2"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save class file
        class_file_path = output_dir / f"{csharp_class.name}.cs"
        with open(class_file_path, 'w', encoding='utf-8') as f:
            if csharp_class.using_statements:
                f.write('\n'.join(csharp_class.using_statements))
                f.write('\n\n')
            f.write(csharp_class.class_code)
        
        print(f"File saved to: {class_file_path}")
        
    except Exception as e:
        print(f"Translation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
