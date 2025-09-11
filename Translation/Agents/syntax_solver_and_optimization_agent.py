"""
Syntax Solver and Optimization Agent
Specialized agent for fixing syntax issues and optimizing translated C# code.

This agent handles:
- Post-translation syntax validation and fixing
- Code optimization and modernization
- Naming convention corrections
- Performance improvements
- Best practices enforcement
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
class OptimizationResult:
    """Result of syntax solving and optimization"""
    optimized_code: str
    fixes_applied: List[str]
    optimizations_applied: List[str]
    warnings: List[str] = field(default_factory=list)
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


class SyntaxSolverAndOptimizationAgent(BaseTranslationAgent):
    """
    Syntax Solver and Optimization Agent
    
    This agent takes already translated C# code and:
    1. Fixes syntax issues and compilation errors
    2. Corrects naming conventions
    3. Optimizes code for performance and readability
    4. Applies modern C# best practices
    5. Ensures code follows established patterns
    """
    
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient]):
        super().__init__("SyntaxSolverAndOptimizationAgent", model_client)
        self.prompt_manager = get_prompt_manager()
    
    def process_translated_code(self, 
                              translated_component: CSharpComponent, 
                              original_vb6_code: str,
                              original_vb6_file: Optional[VB6File] = None) -> CSharpComponent:
        """
        Process and optimize already translated C# code
        
        Args:
            translated_component: The initially translated C# component
            original_vb6_code: Original VB6 source code for reference
            original_vb6_file: Optional original VB6 file for additional context
            
        Returns:
            Optimized CSharpComponent with fixes and improvements applied
        """
        self.logger.info(f"Processing translated code: {translated_component.name}")
        
        try:
            # Create optimization messages
            messages = self._create_optimization_messages(
                translated_component.content,
                original_vb6_code,
                translated_component.file_type,
                translated_component.namespace,
                original_vb6_file
            )
            
            if not messages:
                raise Exception("Failed to create optimization prompt messages")
            
            # Get optimization from LLM
            response = self.model_client.chat(messages)
            
            if not response or not response.content:
                raise Exception("Empty response from LLM during optimization")
            
            # Parse optimization result
            optimization_result = self._parse_optimization_response(response.content)
            
            # Create optimized component
            optimized_component = CSharpComponent(
                name=translated_component.name,
                content=optimization_result.optimized_code,
                file_type=translated_component.file_type,
                namespace=translated_component.namespace,
                dependencies=translated_component.dependencies,
                metadata={
                    **translated_component.metadata,
                    "optimization_applied": True,
                    "fixes_applied": optimization_result.fixes_applied,
                    "optimizations_applied": optimization_result.optimizations_applied,
                    "optimization_warnings": optimization_result.warnings,
                    "optimization_model": response.model,
                    "optimization_provider": response.provider
                }
            )
            
            self.logger.info(f"✅ Successfully optimized {translated_component.name}")
            self.logger.info(f"   Fixes applied: {len(optimization_result.fixes_applied)}")
            self.logger.info(f"   Optimizations applied: {len(optimization_result.optimizations_applied)}")
            
            return optimized_component
            
        except Exception as e:
            self.logger.error(f"Optimization failed for {translated_component.name}: {e}")
            # Return original component if optimization fails
            translated_component.metadata["optimization_failed"] = str(e)
            return translated_component
    
    def _create_optimization_messages(self, 
                                    translated_code: str,
                                    original_vb6_code: str,
                                    file_type: str,
                                    namespace: str,
                                    original_vb6_file: Optional[VB6File] = None) -> List[Dict[str, str]]:
        """Create messages for code optimization"""
        
        # Determine the optimization context based on file type
        context_info = self._build_context_info(file_type, namespace, original_vb6_file)
        
        # Get messages from prompt manager
        messages = self.prompt_manager.create_messages(
            "syntax_optimization",
            translated_code=translated_code,
            original_vb6_code=original_vb6_code,
            file_type=file_type,
            namespace=namespace,
            context_info=context_info
        )
        
        return messages if messages else []
    
    def _build_context_info(self, file_type: str, namespace: str, original_vb6_file: Optional[VB6File]) -> str:
        """Build context information for optimization"""
        context_parts = []
        
        # Add file type specific context
        if file_type == "cs":
            if "Form" in namespace:
                context_parts.append("This is a WinForms form class - focus on UI event handling and control management.")
            elif "Business" in namespace:
                context_parts.append("This is a business logic class - focus on data processing and validation.")
            else:
                context_parts.append("This is a general C# class - apply standard optimization practices.")
        
        # Add VB6 file context if available
        if original_vb6_file:
            if original_vb6_file.file_type == "form":
                context_parts.append("Original was a VB6 form - ensure event handlers and control references are correct.")
            elif original_vb6_file.file_type == "class":
                context_parts.append("Original was a VB6 class - ensure property patterns and methods are properly converted.")
            elif original_vb6_file.file_type == "module":
                context_parts.append("Original was a VB6 module - ensure static methods and utility functions are correct.")
        
        return " ".join(context_parts) if context_parts else ""
    
    def _parse_optimization_response(self, response_content: str) -> OptimizationResult:
        """Parse the LLM optimization response"""
        
        # Look for structured response with delimiters
        optimized_code_match = re.search(
            r'<!-- OPTIMIZED_CODE_START -->(.*?)<!-- OPTIMIZED_CODE_END -->',
            response_content,
            re.DOTALL
        )
        
        fixes_match = re.search(
            r'<!-- FIXES_APPLIED_START -->(.*?)<!-- FIXES_APPLIED_END -->',
            response_content,
            re.DOTALL
        )
        
        optimizations_match = re.search(
            r'<!-- OPTIMIZATIONS_APPLIED_START -->(.*?)<!-- OPTIMIZATIONS_APPLIED_END -->',
            response_content,
            re.DOTALL
        )
        
        warnings_match = re.search(
            r'<!-- WARNINGS_START -->(.*?)<!-- WARNINGS_END -->',
            response_content,
            re.DOTALL
        )
        
        # Extract optimized code
        if optimized_code_match:
            optimized_code = optimized_code_match.group(1).strip()
        else:
            # Fallback: try to extract code blocks
            code_blocks = re.findall(r'```(?:csharp|c#|cs)?\n?(.*?)\n?```', response_content, re.DOTALL)
            optimized_code = code_blocks[0].strip() if code_blocks else response_content.strip()
        
        # Extract fixes applied
        fixes_applied = []
        if fixes_match:
            fixes_text = fixes_match.group(1).strip()
            fixes_applied = [fix.strip() for fix in fixes_text.split('\n') if fix.strip()]
        
        # Extract optimizations applied
        optimizations_applied = []
        if optimizations_match:
            optimizations_text = optimizations_match.group(1).strip()
            optimizations_applied = [opt.strip() for opt in optimizations_text.split('\n') if opt.strip()]
        
        # Extract warnings
        warnings = []
        if warnings_match:
            warnings_text = warnings_match.group(1).strip()
            warnings = [warning.strip() for warning in warnings_text.split('\n') if warning.strip()]
        
        # Clean up the optimized code
        optimized_code = self._clean_optimized_code(optimized_code)
        
        return OptimizationResult(
            optimized_code=optimized_code,
            fixes_applied=fixes_applied,
            optimizations_applied=optimizations_applied,
            warnings=warnings
        )
    
    def _clean_optimized_code(self, code: str) -> str:
        """Clean up the optimized code"""
        # Remove markdown code blocks if present
        cleaned = re.sub(r'```(?:csharp|c#|cs)?\n?', '', code)
        cleaned = re.sub(r'```\n?$', '', cleaned, flags=re.MULTILINE)
        
        # Remove any leading/trailing whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    # Implement BaseTranslationAgent interface (not typically used for this agent)
    def translate(self, vb6_file: VB6File) -> CSharpComponent:
        """Not typically used - this agent processes already translated code"""
        raise NotImplementedError("SyntaxSolverAndOptimizationAgent processes already translated code via process_translated_code()")


def main():
    """Test the SyntaxSolverAndOptimizationAgent"""
    import sys
    from pathlib import Path
    
    # Add project root to path
    sys.path.append(str(Path(__file__).parent.parent.parent))
    
    # Setup logging
    from Utils.logging_config import setup_logging
    setup_logging(task_name="optimization")
    
    from Utils.model_interface import ClaudeClient
    
    # Sample translated code for testing
    sample_translated_code = '''using System;
using System.Windows.Forms;

namespace Forms
{
    public partial class MainForm : Form
    {
        public MainForm()
        {
            InitializeComponent();
        }
        
        private void button1_Click(object sender, EventArgs e)
        {
            string message = "Hello " + textBox1.Text;
            MessageBox.Show(message);
        }
    }
}'''
    
    sample_vb6_code = '''Private Sub Command1_Click()
    Dim msg As String
    msg = "Hello " & Text1.Text
    MsgBox msg
End Sub'''
    
    # Initialize agent with Claude client
    try:
        claude_client = ClaudeClient()
        agent = SyntaxSolverAndOptimizationAgent(claude_client)
        print("Initialized SyntaxSolverAndOptimizationAgent with Claude client")
    except Exception as e:
        print(f"Failed to initialize Claude client: {e}")
        print("Make sure CLAUDE_API_KEY is set in your environment")
        sys.exit(1)
    
    # Create sample component
    sample_component = CSharpComponent(
        name="MainForm",
        content=sample_translated_code,
        file_type="cs",
        namespace="Forms",
        metadata={"original_file": "mainfrm.frm"}
    )
    
    # Process the code
    try:
        print("Starting optimization...")
        optimized_component = agent.process_translated_code(
            sample_component,
            sample_vb6_code
        )
        
        print("Optimization successful!")
        print(f"Fixes applied: {len(optimized_component.metadata.get('fixes_applied', []))}")
        print(f"Optimizations applied: {len(optimized_component.metadata.get('optimizations_applied', []))}")
        
        # Save output file
        output_dir = Path(__file__).parent.parent.parent / "Data" / "Output" / "Optimization_Test"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file_path = output_dir / f"{optimized_component.name}_Optimized.cs"
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(optimized_component.content)
        
        print(f"Optimized file saved to: {output_file_path}")
        
    except Exception as e:
        print(f"Optimization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
