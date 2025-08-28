import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
import re

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from Utils.vb6_parser import VB6ParsedFile
from Utils.prompt_templates import get_prompt_manager
from Utils.model_interface import OllamaClient, ClaudeClient, ModelResponse

@dataclass
class CSharpClass:
    """Represents a translated C# class or static class"""
    name: str
    namespace: str
    class_code: str
    using_statements: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BusinessLogicAgent:
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
        
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient]):
        self.model_client = model_client
        self.logger = logging.getLogger(__name__)
        self.prompt_manager = get_prompt_manager()
        
        # Initialize RAG manager for context-aware translation
        try:
            from Knowledge.rag_manager import RAGManager
            self.rag_manager = RAGManager()
            self.logger.info("RAG manager initialized successfully")
        except Exception as e:
            self.rag_manager = None
            self.logger.warning(f"RAG manager not available: {e}")

    
    def translate_module(self, parsed_file: VB6ParsedFile) -> Optional[CSharpClass]:
        """
        Translate a VB6 module (.bas) or class (.cls) to C# using LLM with RAG
        
        Args:
            parsed_file: Parsed VB6 file
            
        Returns:
            CSharpClass object containing translated code
        """
        self.logger.info(f"Translating VB6 {parsed_file.file_type}: {parsed_file.name}")
        
        try:
            # Read the VB6 source code
            with open(parsed_file.file_path, 'r', encoding='latin-1') as f:
                vb6_content = f.read()
            
            # Select appropriate prompt based on file type
            prompt_type = "vb6_class_to_csharp" if parsed_file.file_type == 'class' else "vb6_module_to_csharp"
            
            # Get RAG context for enhanced translation
            rag_context = self._get_rag_context(vb6_content, parsed_file.file_type)
            
            # Create enhanced messages with RAG context
            messages = self._create_enhanced_messages(prompt_type, vb6_content, rag_context)
            
            if not messages:
                raise Exception("Failed to create prompt messages")
            
            
            response = self.model_client.chat(messages)
            
            if not response or not response.content:
                raise Exception("Empty response from LLM")
            
            # Clean and process the response
            translated_code = self._clean_llm_response(response.content)
            
            return CSharpClass(
                name=self._sanitize_name(parsed_file.name),
                namespace="Translated.Business",
                class_code=translated_code,
                using_statements=[],  # LLM handles using statements in the code
                metadata={
                    "original_file": str(parsed_file.file_path),
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
            return ""
        
        try:
            # Get context info for RAG search
            context_info = {
                "file_type": file_type, 
                "component_type": "business_logic"
            }
            
            # Get pattern suggestions from RAG manager
            suggestions = self.rag_manager.get_pattern_suggestions(vb6_code, context_info)
            
            if not suggestions:
                return ""
            
            # Build context string from top patterns
            context_parts = ["Relevant translation patterns for reference:"]
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
                    message["content"] = f"{message['content']}\n\n{rag_context}\n\nUse these patterns as reference but adapt them to the specific VB6 code being translated."
                    break
        
        return messages
    
    def _clean_llm_response(self, response_content: str) -> str:
        """Clean up LLM response content"""
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```(?:csharp|c#|cs)?\n?', '', response_content)
        cleaned = re.sub(r'```\n?$', '', cleaned, flags=re.MULTILINE)
        
        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()
        
        # Ensure proper namespace structure if not present
        if not cleaned.startswith('namespace ') and not cleaned.startswith('using '):
            # Wrap in namespace if it's just class content
            if 'class ' in cleaned and not 'namespace ' in cleaned:
                indented_code = self._indent_code(cleaned, 1)
                cleaned = f"namespace Translated.Business\n{{\n{indented_code}\n}}"
        
        return cleaned
    
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
