"""
Translation Orchestrator
Manages the actual code translation process and agent coordination.

This is the central component that:
1. Coordinates between different translation agents
2. Manages translation workflow and dependencies
3. Handles component type detection and agent selection
4. Monitors translation progress and handles errors
"""

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from Core.analyzer import VB6File
from settings import get_settings
from Translation.Agents.business_logic_agent import BusinessLogicAgent, CSharpClass
from Translation.Agents.form_agent import FormAgent
from Translation.Agents.syntax_solver_and_optimization_agent import SyntaxSolverAndOptimizationAgent
from Utils.dependency_resolver import DependencyResolver
from Utils.model_interface import OllamaClient, ClaudeClient, ModelResponse
from Utils.prompt_templates import get_prompt_manager, get_translation_prompt
from Utils.vb6_parser import VB6Parser, VB6ParsedFile
from Utils.translation_utils import get_namespace_from_path


class TranslationStatus(Enum):
    """Translation status for components"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


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
class TranslationTask:
    """Represents a translation task"""
    component: VB6File
    status: TranslationStatus = TranslationStatus.PENDING
    assigned_agent: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[CSharpComponent] = None
    error: Optional[str] = None
    retry_count: int = 0


class BaseTranslationAgent:
    """Base class for all translation agents"""
    
    def __init__(self, name: str, model_client: Union[OllamaClient, ClaudeClient]):
        self.name = name
        self.model_client = model_client
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def translate(self, vb6_file: VB6File) -> CSharpComponent:
        """Translate a VB6 file to C#"""
        raise NotImplementedError("Subclasses must implement translate method")



class TranslationOrchestrator:
    """
    Central coordinator for the VB6 to C# translation process.
    
    Responsibilities:
    - Manage translation agents
    - Coordinate translation workflow
    - Handle dependencies and translation order
    - Monitor progress and handle errors
    """
    
    def __init__(self, max_workers: int = None, max_retries: int = None, project_root: Path = None):
        self.logger = logging.getLogger(__name__)
        settings = get_settings()
        self.max_workers = max_workers if max_workers is not None else settings.MAX_WORKERS
        self.max_retries = max_retries if max_retries is not None else settings.MAX_RETRIES
        self.project_root = project_root
        
        # Initialize components
        self.vb6_parser = VB6Parser()
        self.dependency_resolver = DependencyResolver()
        
        # Initialize model client
        settings = get_settings()
        try:
            if settings.DEFAULT_PROVIDER == "claude" and settings.CLAUDE_API_KEY:
                self.model_client = ClaudeClient()
            else:
                self.model_client = OllamaClient()
        except Exception as e:
            self.logger.error(f"Failed to initialize model client: {e}")
            raise
        
        # Initialize agents
        self.agents: Dict[str, BaseTranslationAgent] = {}
        self.optimization_agent: Optional[SyntaxSolverAndOptimizationAgent] = None
        self._initialize_agents()
        
        # Translation state
        self.tasks: Dict[str, TranslationTask] = {}
        self.completed_translations: Dict[str, CSharpComponent] = {}
        self.failed_translations: Dict[str, str] = {}
        self.original_vb6_files: Dict[str, VB6File] = {}  # Store original files for optimization
        self.project_files: Dict[str, VB6File] = {}  # Project context for dependency resolution
    
    def _initialize_agents(self):
        """Initialize all available translation agents"""
        self.agents = {
            "form": FormAgent(self.model_client, self.project_root),
            "business_logic": BusinessLogicAgent(self.model_client, self.project_root)
        }
        
        # Initialize optimization agent
        try:
            self.optimization_agent = SyntaxSolverAndOptimizationAgent(self.model_client)
            self.logger.info("Initialized syntax solver and optimization agent")
        except Exception as e:
            self.logger.warning(f"Failed to initialize optimization agent: {e}")
            self.optimization_agent = None
        
        self.logger.info(f"Initialized {len(self.agents)} translation agents")
    
    def set_project_context(self, project_files: dict):
        """Store project context for passing to agents during translation"""
        self.project_files = project_files
    
    
    def _translate_component(self, component_name: str, vb6_file: VB6File) -> bool:
        """
        Translate a single component
        
        Args:
            component_name: Name of the component
            vb6_file: VB6File object containing all file information
        
        Returns:
            True if translation successful, False otherwise
        """
        # Create or get task
        if component_name not in self.tasks:
            self.tasks[component_name] = TranslationTask(component=vb6_file)
        
        task = self.tasks[component_name]
        task.status = TranslationStatus.IN_PROGRESS
        task.start_time = time.time()
        
        try:
            # Store original VB6 file for optimization
            self.original_vb6_files[component_name] = vb6_file
            
            # Select agent based on file type - simple and direct
            if vb6_file.file_type in ['form', 'control']:
                agent = self.agents.get('form')
            else:  # 'class', 'module', or anything else
                agent = self.agents.get('business_logic')
            
            if not agent:
                raise ValueError(f"No suitable agent found for {vb6_file.file_type}")
            
            task.assigned_agent = agent.name
            self.logger.info(f"Translating {component_name} with {agent.name}")
            
            # Perform initial translation
            result = agent.translate(vb6_file, self.project_files)
            
            # Apply syntax solving and optimization if agent is available
            if self.optimization_agent and result:
                self.logger.info(f"Applying syntax solving and optimization to {component_name}")
                try:
                    # Read original VB6 code for reference
                    original_vb6_code = ""
                    if vb6_file.file_path and vb6_file.file_path.exists():
                        with open(vb6_file.file_path, 'r', encoding='latin-1') as f:
                            original_vb6_code = f.read()
                    
                    # Apply optimization
                    optimized_result = self.optimization_agent.process_translated_code(
                        result, 
                        original_vb6_code,
                        vb6_file
                    )
                    
                    if optimized_result:
                        result = optimized_result
                        self.logger.info(f"✅ Applied optimization to {component_name}")
                    else:
                        self.logger.warning(f"Optimization returned None for {component_name}, using original translation")
                        
                except Exception as e:
                    self.logger.warning(f"Optimization failed for {component_name}: {e}")
                    # Continue with original translation if optimization fails
            else:
                if not self.optimization_agent:
                    self.logger.debug(f"No optimization agent available for {component_name}")
            
            # Store results
            task.result = result
            task.status = TranslationStatus.COMPLETED
            task.end_time = time.time()
            
            self.completed_translations[component_name] = result
            
            duration = task.end_time - task.start_time
            optimization_status = "with optimization" if self.optimization_agent else "without optimization"
            self.logger.info(f"✅ Successfully translated {component_name} in {duration:.2f}s using {agent.name} {optimization_status}")
            
            # Log component-specific timing details
            file_type = vb6_file.file_type
            self.logger.debug(f"📊 {component_name} ({file_type}): {duration:.2f}s")
            
            return True
            
        except Exception as e:
            task.status = TranslationStatus.FAILED
            task.end_time = time.time()
            task.error = str(e)
            
            # Retry logic
            if task.retry_count < self.max_retries:
                task.retry_count += 1
                self.logger.warning(f"Translation failed for {component_name}, retrying ({task.retry_count}/{self.max_retries}): {e}")
                return self._translate_component(component_name, vb6_file)  # Retry
            else:
                self.logger.error(f"Translation failed for {component_name} after {self.max_retries} retries: {e}")
                self.failed_translations[component_name] = str(e)
                return False
    
    def get_translation_progress(self) -> Dict[str, Any]:
        """Get current translation progress statistics"""
        total = len(self.tasks)
        completed = len([t for t in self.tasks.values() if t.status == TranslationStatus.COMPLETED])
        failed = len([t for t in self.tasks.values() if t.status == TranslationStatus.FAILED])
        in_progress = len([t for t in self.tasks.values() if t.status == TranslationStatus.IN_PROGRESS])
        pending = len([t for t in self.tasks.values() if t.status == TranslationStatus.PENDING])
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
            "success_rate": (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
        }
    
    def get_translation_summary(self) -> Dict[str, Any]:
        """Get detailed translation summary"""
        progress = self.get_translation_progress()
        
        # Calculate timing statistics
        completed_tasks = [t for t in self.tasks.values() if t.status == TranslationStatus.COMPLETED]
        if completed_tasks:
            durations = [t.end_time - t.start_time for t in completed_tasks if t.start_time and t.end_time]
            avg_duration = sum(durations) / len(durations) if durations else 0
        else:
            avg_duration = 0
        
        return {
            "progress": progress,
            "average_translation_time": avg_duration,
            "agents_used": list(set(t.assigned_agent for t in self.tasks.values() if t.assigned_agent)),
            "failed_components": list(self.failed_translations.keys()),
            "successful_components": list(self.completed_translations.keys())
        }
    
    def _log_translation_timing_summary(self):
        """Log detailed timing summary for individual components"""
        if not self.tasks:
            return
        
        completed_tasks = [t for t in self.tasks.values() if t.status == TranslationStatus.COMPLETED]
        failed_tasks = [t for t in self.tasks.values() if t.status == TranslationStatus.FAILED]
        
        if not completed_tasks:
            return
        
        self.logger.info("-" * 50)
        self.logger.info("🔄 COMPONENT TRANSLATION TIMING")
        self.logger.info("-" * 50)
        
        # Sort by duration (longest first)
        completed_tasks.sort(key=lambda t: t.end_time - t.start_time if t.start_time and t.end_time else 0, reverse=True)
        
        total_translation_time = 0
        for task in completed_tasks:
            if task.start_time and task.end_time:
                duration = task.end_time - task.start_time
                total_translation_time += duration
                file_type = task.component.file_type
                self.logger.info(f"  • {task.component.name} ({file_type}): {duration:.2f}s [{task.assigned_agent}]")
        
        # Summary statistics
        durations = [t.end_time - t.start_time for t in completed_tasks if t.start_time and t.end_time]
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            self.logger.info(f"\n📊 Translation Statistics:")
            self.logger.info(f"  • Total Components: {len(completed_tasks)}")
            self.logger.info(f"  • Total Time: {total_translation_time:.2f}s")
            self.logger.info(f"  • Average Time: {avg_duration:.2f}s")
            self.logger.info(f"  • Fastest: {min_duration:.2f}s")
            self.logger.info(f"  • Slowest: {max_duration:.2f}s")
            
            # Agent performance
            agent_times = {}
            for task in completed_tasks:
                if task.assigned_agent and task.start_time and task.end_time:
                    duration = task.end_time - task.start_time
                    if task.assigned_agent not in agent_times:
                        agent_times[task.assigned_agent] = []
                    agent_times[task.assigned_agent].append(duration)
            
            if agent_times:
                self.logger.info(f"\n🤖 Agent Performance:")
                for agent, times in agent_times.items():
                    avg_time = sum(times) / len(times)
                    self.logger.info(f"  • {agent}: {len(times)} components, {avg_time:.2f}s avg")
        
        if failed_tasks:
            self.logger.info(f"\n❌ Failed Components: {len(failed_tasks)}")
            for task in failed_tasks:
                self.logger.info(f"  • {task.component.name}: {task.error}")
        
        self.logger.info("-" * 50)
    
    def save_translated_project(self, output_dir: Path, project_name: str) -> Dict[str, List[Path]]:
        """
        Save all translated components to the output directory with proper structure
        
        Args:
            output_dir: Base output directory
            project_name: Name of the project for the output folder
            
        Returns:
            Dictionary mapping file types to lists of saved file paths
        """
        project_output_dir = output_dir / project_name
        project_output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {
            "forms": [],
            "business_logic": [],
            "other": []
        }
        
        self.logger.info(f"Saving translated project to: {project_output_dir}")
        
        for name, component in self.completed_translations.items():
            try:
                # Determine file category and save location based on namespace
                if "UI" in component.namespace or "Forms" in component.namespace:
                    category = "forms"
                elif "Models" in component.namespace or "Business" in component.namespace:
                    category = "business_logic"
                elif "Utilities" in component.namespace or "Utils" in component.namespace:
                    category = "business_logic"  # Group utilities with business logic
                else:
                    category = "other"
                
                # Save main file
                main_file_path = project_output_dir / f"{component.name}.{component.file_type}"
                self._save_component_file(main_file_path, component)
                saved_files[category].append(main_file_path)
                
                # Save designer file if it exists (for forms)
                if "designer_code" in component.metadata and component.metadata["designer_code"]:
                    designer_file_path = project_output_dir / f"{component.name}.Designer.{component.file_type}"
                    self._save_designer_file(designer_file_path, component)
                    saved_files[category].append(designer_file_path)
                
                self.logger.info(f"Saved {name} to {main_file_path}")
                
            except Exception as e:
                self.logger.error(f"Failed to save component {name}: {e}")
        
        # Create project summary file
        summary_file = project_output_dir / "translation_summary.txt"
        self._save_project_summary(summary_file)
        saved_files["other"].append(summary_file)
        
        self.logger.info(f"Project saved successfully. Total files: {sum(len(files) for files in saved_files.values())}")
        return saved_files
    
    def _save_component_file(self, file_path: Path, component: CSharpComponent):
        """Save a single component file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            # Add using statements if they exist
            using_statements = component.metadata.get("using_statements", [])
            if using_statements:
                f.write('\n'.join(using_statements))
                f.write('\n\n')
            
            f.write(component.content)
    
    def _save_designer_file(self, file_path: Path, component: CSharpComponent):
        """Save a designer file for forms"""
        designer_code = component.metadata.get("designer_code", "")
        if designer_code:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Add using statements if they exist
                using_statements = component.metadata.get("using_statements", [])
                if using_statements:
                    f.write('\n'.join(using_statements))
                    f.write('\n\n')
                
                f.write(designer_code)
    
    def _save_project_summary(self, summary_file: Path):
        """Save project translation summary"""
        summary = self.get_translation_summary()
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("VB6 to C# Translation Summary\n")
            f.write("=" * 40 + "\n\n")
            
            # Progress information
            progress = summary["progress"]
            f.write(f"Total Components: {progress['total']}\n")
            f.write(f"Successfully Translated: {progress['completed']}\n")
            f.write(f"Failed: {progress['failed']}\n")
            f.write(f"Success Rate: {progress['success_rate']:.1f}%\n")
            f.write(f"Average Translation Time: {summary['average_translation_time']:.2f}s\n\n")
            
            # Agents used
            f.write(f"Translation Agents Used:\n")
            for agent in summary["agents_used"]:
                f.write(f"  - {agent}\n")
            if self.optimization_agent:
                f.write(f"  - {self.optimization_agent.name} (syntax solving and optimization)\n")
            f.write("\n")
            
            # Successful components
            f.write("Successfully Translated Components:\n")
            for component in summary["successful_components"]:
                f.write(f"  - {component}\n")
            f.write("\n")
            
            # Failed components
            if summary["failed_components"]:
                f.write("Failed Components:\n")
                for component in summary["failed_components"]:
                    f.write(f"  - {component}: {self.failed_translations.get(component, 'Unknown error')}\n")
                f.write("\n")
            
            # Translation details
            f.write("Translation Details:\n")
            for name, component in self.completed_translations.items():
                f.write(f"\n{name}:\n")
                f.write(f"  - Original file: {component.metadata.get('original_file', 'Unknown')}\n")
                f.write(f"  - Namespace: {component.namespace}\n")
                f.write(f"  - File type: {component.file_type}\n")
                
                # Optimization information
                if component.metadata.get('optimization_applied'):
                    f.write(f"  - Optimization applied: Yes\n")
                    fixes_count = len(component.metadata.get('fixes_applied', []))
                    optimizations_count = len(component.metadata.get('optimizations_applied', []))
                    f.write(f"  - Syntax fixes applied: {fixes_count}\n")
                    f.write(f"  - Optimizations applied: {optimizations_count}\n")
                    
                    if component.metadata.get('optimization_warnings'):
                        warnings_count = len(component.metadata.get('optimization_warnings', []))
                        f.write(f"  - Optimization warnings: {warnings_count}\n")
                else:
                    f.write(f"  - Optimization applied: No\n")
                    if component.metadata.get('optimization_failed'):
                        f.write(f"  - Optimization failed: {component.metadata.get('optimization_failed')}\n")
                
                # Additional metadata
                for key, value in component.metadata.items():
                    if key not in ['original_file', 'using_statements', 'designer_code', 
                                 'optimization_applied', 'fixes_applied', 'optimizations_applied', 
                                 'optimization_warnings', 'optimization_failed', 'optimization_model', 'optimization_provider']:
                        f.write(f"  - {key}: {value}\n")




def main():
    """Test function for the translation orchestrator (deprecated - use ProjectOrchestrator instead)"""
    import argparse
    
    print("WARNING: Running TranslationOrchestrator directly is deprecated.")
    print("Please use ProjectOrchestrator from Core.project_orchestrator for full workflow coordination.")
    print("This function is provided for testing and debugging purposes only.\n")
    
    # Add project root to path for imports
    sys.path.append(str(Path(__file__).parent.parent))
    from Utils.logging_config import setup_logging
    
    parser = argparse.ArgumentParser(description="VB6 to C# Translation Orchestrator (Deprecated)")
    parser.add_argument("project_path", help="Path to VB6 project file or directory")
    parser.add_argument("--max-workers", type=int, help="Maximum number of parallel workers (default: from settings)")
    parser.add_argument("--max-retries", type=int, help="Maximum number of retries for failed translations (default: from settings)")
    parser.add_argument("--output-dir", help="Output directory for translated files")
    parser.add_argument("--log-file", help="Path to log file (optional, creates default if not specified)")
    
    args = parser.parse_args()
    
    # Setup logging with file output
    setup_logging(
        level=logging.INFO,
        log_file=args.log_file,
        console=True,
        task_name="translation"
    )
    

if __name__ == "__main__":
    exit(main())
