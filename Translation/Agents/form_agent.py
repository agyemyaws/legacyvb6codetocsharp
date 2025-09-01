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
    
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient]):
        super().__init__("FormAgent", model_client)
        self.prompt_manager = get_prompt_manager()
        
        # Initialize RAG manager for context-aware translation
        try:
            from Knowledge.rag_manager import RAGManager
            self.rag_manager = RAGManager()
            self.logger.info("RAG manager initialized successfully")
        except Exception as e:
            self.rag_manager = None
            self.logger.warning(f"RAG manager not available: {e}")
    
    def translate(self, vb6_file: VB6File) -> CSharpComponent:
        """Translate VB6 form to C# form - implements BaseTranslationAgent interface"""
        self.logger.info(f"Translating form: {vb6_file.name}")
        
        try:
            # Use the existing translate_form method
            csharp_form = self.translate_form(vb6_file.parsed_data)
            
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
    
    def translate_form(self, parsed_form: VB6ParsedFile) -> Optional[CSharpForm]:
        """
        Translate a VB6 form (.frm) to C# WinForms using LLM with RAG
        
        Args:
            parsed_form: Parsed VB6 form file
            
        Returns:
            CSharpForm object containing translated form and designer code
        """
        self.logger.info(f"Translating VB6 form: {parsed_form.name}")
        
        try:
            # Read the VB6 source code
            with open(parsed_form.file_path, 'r', encoding='latin-1') as f:
                vb6_content = f.read()
            
            # Get RAG context for enhanced translation
            rag_context = self._get_rag_context(vb6_content, "form")
            
            # Create enhanced messages with RAG context for form translation
            messages = self._create_enhanced_messages("vb6_to_winforms", vb6_content, rag_context)
            
            if not messages:
                raise Exception("Failed to create prompt messages")
            
            response = self.model_client.chat(messages)
            
            if not response or not response.content:
                raise Exception("Empty response from LLM")
            
            # print("--------------------------------")
            # print(response.content)
            # print("--------------------------------")
            
            # Parse the LLM response to extract form and designer code
            form_code, designer_code = self._parse_llm_form_response(response.content)
            
            return CSharpForm(
                name=self._sanitize_name(parsed_form.name),
                namespace="Translated.Forms",
                form_class_code=form_code,
                designer_code=designer_code,
                using_statements=[],  # LLM handles using statements in the code
                metadata={
                    "original_file": str(parsed_form.file_path),
                    "translation_method": "llm_with_rag",
                    "model": response.model,
                    "provider": response.provider,
                    "rag_context_used": bool(rag_context)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Translation failed for {parsed_form.name}: {e}")
            return None
    
    def _get_rag_context(self, vb6_code: str, file_type: str) -> str:
        """Get RAG context from similar patterns"""
        if not self.rag_manager:
            return ""
        
        try:
            # Get context info for RAG search
            context_info = {
                "file_type": file_type, 
                "component_type": "form"
            }
            
            # Get pattern suggestions from RAG manager
            suggestions = self.rag_manager.get_pattern_suggestions(vb6_code, context_info)
            
            if not suggestions:
                return ""
            
            # Build context string from top patterns
            context_parts = ["Relevant form translation patterns for reference:"]
            for i, match in enumerate(suggestions[:3], 1):  # Top 3 patterns
                context_parts.append(f"\n{i}. {match.pattern.name}:")
                context_parts.append(f"   VB6: {match.pattern.vb6_code[:200]}...")
                context_parts.append(f"   C#: {match.pattern.csharp_code[:200]}...")
                context_parts.append(f"   Description: {match.pattern.description}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            self.logger.debug(f"RAG context generation failed: {e}")
        return ""
    
    def _create_enhanced_messages(self, prompt_type: str, vb6_content: str, rag_context: str) -> List[Dict[str, str]]:
        """Create messages with RAG context enhancement"""
        # Get base messages from prompt manager
        messages = self.prompt_manager.create_messages(prompt_type, source_code=vb6_content)
        
        if not messages:
            return []
        
        # Enhance with RAG context if available
        if rag_context:
            # Add RAG context to the system message
            for message in messages:
                if message.get("role") == "system":
                    message["content"] = f"{message['content']}\n\n{rag_context}\n\nUse these patterns as reference but adapt them to the specific VB6 form being translated."
                    break
        
        return messages
    
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
        
        if form_match and designer_match:
            form_code = form_match.group(1).strip()
            designer_code = designer_match.group(1).strip()
            
            self.logger.info("Successfully extracted both form and designer code using delimiters")
            
            # Clean the extracted code
            form_code = self._clean_llm_response(form_code)
            designer_code = self._clean_llm_response(designer_code)
            
            # Ensure proper namespace wrapping
            form_code = self._ensure_namespace_wrapper(form_code, "Translated.Forms")
            designer_code = self._ensure_namespace_wrapper(designer_code, "Translated.Forms")
            
            return form_code, designer_code
        
        self.logger.warning("Could not find proper delimiters in LLM response, attempting to extract from raw content")
        
        # Enhanced fallback: try to split the LLM response intelligently
        form_code, designer_code = self._extract_classes_from_raw_response(response_content)
        
        return form_code, designer_code
    

    
    def _extract_classes_from_raw_response(self, response_content: str) -> tuple:
        """
        Extract form and designer classes from raw LLM response without relying on delimiters.
        This method tries to intelligently split the response based on class patterns.
        Returns (form_code, designer_code)
        """
        import re
        
        self.logger.info("Attempting to extract classes from raw LLM response")
        
        # Clean the response content first
        cleaned_content = self._clean_llm_response(response_content)
        
        # Try to find class definitions in the response
        # Look for patterns like "public partial class" (form) and "partial class" (designer)
        class_pattern = r'(namespace\s+[\w.]+\s*\{.*?(?:public\s+partial\s+class|partial\s+class).*?\}(?:\s*\}))'
        
        classes = re.findall(class_pattern, cleaned_content, re.DOTALL | re.MULTILINE)
        
        if len(classes) >= 2:
            # Assume first class with "public partial class" is the form class
            # and first class with just "partial class" is the designer
            form_code = None
            designer_code = None
            
            for class_code in classes:
                if 'public partial class' in class_code and 'InitializeComponent' not in class_code:
                    form_code = class_code.strip()
                elif 'partial class' in class_code and 'InitializeComponent' in class_code:
                    designer_code = class_code.strip()
            
            # If we found both classes
            if form_code and designer_code:
                self.logger.info("Successfully extracted form and designer classes from raw content")
                return self._ensure_namespace_wrapper(form_code, "Translated.Forms"), self._ensure_namespace_wrapper(designer_code, "Translated.Forms")
        
        # If we can't split intelligently, try to split on common patterns
        # Look for "InitializeComponent" as a delimiter between form logic and designer
        if 'InitializeComponent' in cleaned_content:
            # Split on the first occurrence of a method that contains InitializeComponent
            parts = re.split(r'(private\s+void\s+InitializeComponent\s*\(\s*\))', cleaned_content, maxsplit=1)
            
            if len(parts) >= 3:
                # parts[0] = content before InitializeComponent
                # parts[1] = the InitializeComponent method signature
                # parts[2] = content after (the rest of InitializeComponent + other designer methods)
                
                form_part = parts[0].strip()
                designer_part = (parts[1] + parts[2]).strip()
                
                # Try to extract complete classes from each part
                form_code = self._extract_complete_class(form_part)
                designer_code = self._extract_complete_class_with_designer_content(designer_part, cleaned_content)
                
                if form_code and designer_code:
                    self.logger.info("Successfully split content based on InitializeComponent pattern")
                    return form_code, designer_code
        
        self.logger.warning("Could not intelligently split classes, extracting designer from full content")
        
        # Try to extract designer-specific content from the full response
        designer_code = self._extract_designer_from_full_content(cleaned_content)
        form_code = self._extract_form_from_full_content(cleaned_content)
        
        
        
        return form_code, designer_code

    def _extract_complete_class(self, content: str) -> str:
        """Extract a complete class definition from content"""
        import re
        
        # Look for a complete class definition
        class_match = re.search(r'(namespace\s+[\w.]+\s*\{.*?public\s+partial\s+class.*?\}(?:\s*\}))', content, re.DOTALL)
        if class_match:
            return self._ensure_namespace_wrapper(class_match.group(1).strip(), "Translated.Forms")
        return None

    def _extract_complete_class_with_designer_content(self, designer_part: str, full_content: str) -> str:
        """Extract complete designer class, ensuring we get the full class definition"""
        import re
        
        # Try to find the complete partial class definition that contains InitializeComponent
        class_match = re.search(r'(namespace\s+[\w.]+\s*\{.*?partial\s+class.*?InitializeComponent.*?\}(?:\s*\}))', full_content, re.DOTALL)
        if class_match:
            return self._ensure_namespace_wrapper(class_match.group(1).strip(), "Translated.Forms")
        
        # Fallback: try to construct from the designer part
        if 'namespace' not in designer_part:
            # Need to wrap in namespace and class
            return self._ensure_namespace_wrapper(f"partial class MainForm\n{{\n{designer_part}\n}}", "Translated.Forms")
        
        return self._ensure_namespace_wrapper(designer_part, "Translated.Forms")

    def _extract_designer_from_full_content(self, content: str) -> str:
        """Extract designer-specific content from full response"""
        import re
        
        # Look for designer-specific patterns
        designer_patterns = [
            r'(partial\s+class\s+\w+\s*\{[^}]*InitializeComponent[^}]*\})',
            r'(private\s+void\s+InitializeComponent\s*\(\s*\).*?(?=private\s+void|public\s+|protected\s+|\}$))',
            r'(private\s+.*?components\s*=.*?;.*?InitializeComponent.*?)',
        ]
        
        for pattern in designer_patterns:
            match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
            if match:
                designer_content = match.group(1).strip()
                # Ensure it's wrapped in a proper class structure
                if 'partial class' not in designer_content:
                    designer_content = f"partial class MainForm\n{{\nprivate System.ComponentModel.IContainer components = null;\n\n{designer_content}\n}}"
                return self._ensure_namespace_wrapper(designer_content, "Translated.Forms")
        
        return None

    def _extract_form_from_full_content(self, content: str) -> str:
        """Extract form-specific content (business logic) from full response"""
        import re
        
        # Try to extract everything except designer-specific content
        # Remove InitializeComponent and designer-specific methods
        form_content = re.sub(r'private\s+void\s+InitializeComponent\s*\(\s*\).*?(?=private\s+void|public\s+|protected\s+override\s+void\s+Dispose|\}$)', '', content, flags=re.DOTALL)
        form_content = re.sub(r'private\s+System\.ComponentModel\.IContainer\s+components.*?;', '', form_content)
        form_content = re.sub(r'private\s+.*?(TextBox|Button|Label|Control)\s+\w+\s*;', '', form_content, flags=re.MULTILINE)
        
        # Look for public partial class (form class)
        class_match = re.search(r'(namespace\s+[\w.]+\s*\{.*?public\s+partial\s+class.*?\}(?:\s*\}))', form_content, re.DOTALL)
        if class_match:
            return self._ensure_namespace_wrapper(class_match.group(1).strip(), "Translated.Forms")
        
        return None


        
    def _clean_llm_response(self, response_content: str) -> str:
        """Clean up LLM response content"""
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```(?:csharp|c#|cs)?\n?', '', response_content)
        cleaned = re.sub(r'```\n?$', '', cleaned, flags=re.MULTILINE)
        
        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _ensure_namespace_wrapper(self, code: str, namespace: str) -> str:
        """Ensure code is properly wrapped in namespace"""
        if not code.startswith('namespace ') and not code.startswith('using '):
            # Wrap in namespace if it's just class content
            if 'class ' in code and not 'namespace ' in code:
                code = f"""namespace {namespace}
{{{{
{self._indent_code(code, 1)}
}}}}"""
        return code
    
    def _indent_code(self, code: str, levels: int) -> str:
        """Indent code by specified levels (4 spaces per level)"""
        indent = '    ' * levels
        return '\n'.join(f"{indent}{line}" if line.strip() else line for line in code.split('\n'))
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize VB6 names for C# compatibility"""
        # Remove invalid characters and handle keywords
        sanitized = re.sub(r'[^\w]', '_', name)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        return sanitized
    



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
