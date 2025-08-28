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
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from Utils.vb6_parser import VB6Parser, VB6ParsedFile
from Utils.dependency_resolver import DependencyResolver
from Utils.model_interface import OllamaClient, ClaudeClient, ModelResponse
from settings import get_settings
from Utils.prompt_templates import get_prompt_manager, get_translation_prompt
from Translation.Agents.form_agent import FormAgent, CSharpForm
from Translation.Agents.business_logic_agent import BusinessLogicAgent, CSharpClass

class ComponentType(Enum):
    """VB6 component types that require different translation approaches"""
    FORM = "form"
    MODULE = "module"
    CLASS = "class"
    CONTROL = "control"
    PROJECT = "project"


class TranslationStatus(Enum):
    """Translation status for components"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VB6Component:
    """Represents a VB6 component to be translated"""
    name: str
    file_path: Path
    component_type: ComponentType
    parsed_data: Optional[VB6ParsedFile] = None
    dependencies: List[str] = field(default_factory=list)
    external_references: List[str] = field(default_factory=list)
    priority: int = 0  # Higher priority = translate first


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
    component: VB6Component
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
        self.supported_types: List[ComponentType] = []
    
    def can_handle(self, component: VB6Component) -> bool:
        """Check if this agent can handle the given component type"""
        return component.component_type in self.supported_types
    
    def translate(self, component: VB6Component) -> CSharpComponent:
        """Translate a VB6 component to C#"""
        raise NotImplementedError("Subclasses must implement translate method")
    
    def get_priority_score(self, component: VB6Component) -> int:
        """Get priority score for handling this component (higher = better match)"""
        if component.component_type in self.supported_types:
            return len(self.supported_types) - self.supported_types.index(component.component_type)
        return 0




class FormTranslationAgent(BaseTranslationAgent):
    """Agent specialized in translating VB6 forms to C# WinForms/WPF"""
    
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient]):
        super().__init__("FormAgent", model_client)
        self.supported_types = [ComponentType.FORM, ComponentType.CONTROL]
        
        # Initialize the actual form agent
        self.form_agent = FormAgent(model_client)
    
    def translate(self, component: VB6Component) -> CSharpComponent:
        """Translate VB6 form to C# form"""
        self.logger.info(f"Translating form: {component.name}")
        
        try:
            # Use the actual FormAgent for translation
            csharp_form = self.form_agent.translate_form(component.parsed_data)
            
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
                
        except Exception as e:
            self.logger.error(f"FormAgent translation failed: {e}")
        
        # Fallback to placeholder implementation
        form_content = self._generate_form_code(component)
        
        return CSharpComponent(
            name=component.name,
            content=form_content,
            file_type="cs",
            namespace=f"Translated.Forms",
            metadata={"original_file": str(component.file_path)}
        )
    
    def _generate_form_code(self, component: VB6Component) -> str:
        """Generate C# form code from VB6 component (fallback)"""
        return f"""using System;
using System.Windows.Forms;

namespace Translated.Forms
{{
    public partial class {component.name} : Form
    {{
        public {component.name}()
        {{
            InitializeComponent();
        }}
        
        // TODO: Implement form logic from {component.file_path}
    }}
}}"""


class BusinessLogicTranslationAgent(BaseTranslationAgent):
    """Agent specialized in translating VB6 modules and classes"""
    
    def __init__(self, model_client: Union[OllamaClient, ClaudeClient]):
        super().__init__("BusinessLogicAgent", model_client)
        self.supported_types = [ComponentType.MODULE, ComponentType.CLASS]
        
        # Initialize the actual business logic agent
        self.business_logic_agent = BusinessLogicAgent(model_client)
    
    def translate(self, component: VB6Component) -> CSharpComponent:
        """Translate VB6 module/class to C#"""
        self.logger.info(f"Translating business logic: {component.name}")
        
        try:
            # Use the actual BusinessLogicAgent for translation
            csharp_class = self.business_logic_agent.translate_module(component.parsed_data)
            
            if csharp_class:
                # Convert CSharpClass to CSharpComponent format expected by orchestrator
                return CSharpComponent(
                    name=csharp_class.name,
                    content=csharp_class.class_code,
                    file_type="cs",
                    namespace=csharp_class.namespace,
                    metadata={
                        "original_file": str(component.file_path),
                        "using_statements": csharp_class.using_statements,
                        **csharp_class.metadata
                    }
                )
        except Exception as e:
            self.logger.error(f"BusinessLogicAgent translation failed: {e}")
        
        # Fallback to placeholder implementation
        class_content = self._generate_class_code(component)
        
        return CSharpComponent(
            name=component.name,
            content=class_content,
            file_type="cs",
            namespace=f"Translated.Business",
            metadata={"original_file": str(component.file_path)}
        )
    
    def _generate_class_code(self, component: VB6Component) -> str:
        """Generate C# class code from VB6 component (fallback)"""
        class_type = "class" if component.component_type == ComponentType.CLASS else "static class"
        return f"""using System;

namespace Translated.Business
{{
    public {class_type} {component.name}
    {{
        // TODO: Implement logic from {component.file_path}
    }}
}}"""


class TranslationOrchestrator:
    """
    Central coordinator for the VB6 to C# translation process.
    
    Responsibilities:
    - Manage translation agents
    - Coordinate translation workflow
    - Handle dependencies and translation order
    - Monitor progress and handle errors
    """
    
    def __init__(self, max_workers: int = 3, max_retries: int = 2):
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.max_retries = max_retries
        
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
        self._initialize_agents()
        
        # Translation state
        self.tasks: Dict[str, TranslationTask] = {}
        self.completed_translations: Dict[str, CSharpComponent] = {}
        self.failed_translations: Dict[str, str] = {}
    
    def _initialize_agents(self):
        """Initialize all available translation agents"""
        self.agents = {
            "form": FormTranslationAgent(self.model_client),
            "business_logic": BusinessLogicTranslationAgent(self.model_client)
        }
        
        self.logger.info(f"Initialized {len(self.agents)} translation agents")
    
    def analyze_vb6_project(self, project_path: Path) -> List[VB6Component]:
        """
        Analyze VB6 project and identify all components to translate
        
        Args:
            project_path: Path to VB6 project directory or .vbp file
            
        Returns:
            List of VB6 components ready for translation
        """
        self.logger.info(f"Analyzing VB6 project: {project_path}")
        
        components = []
        
        if project_path.is_file() and project_path.suffix.lower() == '.vbp':
            # Parse project file to get component list
            components = self._parse_project_file(project_path)
        elif project_path.is_dir():
            # Scan directory for VB6 files
            components = self._scan_directory(project_path)
        else:
            raise ValueError(f"Invalid project path: {project_path}")
        
        # Parse each component
        for component in components:
            try:
                parsed_data = self.vb6_parser.parse_file(component.file_path)
                component.parsed_data = parsed_data
                
                if parsed_data:
                    component.dependencies = list(parsed_data.dependencies)
                    component.external_references = list(parsed_data.external_references)
            except Exception as e:
                self.logger.warning(f"Failed to parse {component.file_path}: {e}")
        
        self.logger.info(f"Found {len(components)} components to translate")
        return components
    
    def _parse_project_file(self, vbp_path: Path) -> List[VB6Component]:
        """Parse .vbp file to extract component list"""
        components = []
        project_dir = vbp_path.parent
        
        try:
            with open(vbp_path, 'r', encoding='latin-1') as f:
                content = f.read()
            
            for line in content.split('\n'):
                line = line.strip()
                
                if line.startswith('Form='):
                    # Form=frmMain.frm
                    form_file = line.split('=', 1)[1]
                    form_path = project_dir / form_file
                    if form_path.exists():
                        components.append(VB6Component(
                            name=form_path.stem,
                            file_path=form_path,
                            component_type=ComponentType.FORM
                        ))
                
                elif line.startswith('Module='):
                    # Module=modUtilities; modUtilities.bas
                    parts = line.split('=', 1)[1].split(';')
                    if len(parts) >= 2:
                        module_name = parts[0].strip()
                        module_file = parts[1].strip()
                        module_path = project_dir / module_file
                        if module_path.exists():
                            components.append(VB6Component(
                                name=module_name,
                                file_path=module_path,
                                component_type=ComponentType.MODULE
                            ))
                
                elif line.startswith('Class='):
                    # Class=clsPerson; clsPerson.cls
                    parts = line.split('=', 1)[1].split(';')
                    if len(parts) >= 2:
                        class_name = parts[0].strip()
                        class_file = parts[1].strip()
                        class_path = project_dir / class_file
                        if class_path.exists():
                            components.append(VB6Component(
                                name=class_name,
                                file_path=class_path,
                                component_type=ComponentType.CLASS
                            ))
        
        except Exception as e:
            self.logger.error(f"Error parsing project file {vbp_path}: {e}")
        
        return components
    
    def _scan_directory(self, directory: Path) -> List[VB6Component]:
        """Scan directory for VB6 files"""
        components = []
        
        # File type mappings
        type_mappings = {
            '.frm': ComponentType.FORM,
            '.cls': ComponentType.CLASS,
            '.bas': ComponentType.MODULE,
            '.ctl': ComponentType.CONTROL
        }
        
        for file_path in directory.rglob('*'):
            if file_path.suffix.lower() in type_mappings:
                component_type = type_mappings[file_path.suffix.lower()]
                components.append(VB6Component(
                    name=file_path.stem,
                    file_path=file_path,
                    component_type=component_type
                ))
        
        return components
    
    def translate_project(self, components: List[VB6Component]) -> Dict[str, CSharpComponent]:
        """
        Translate entire project with proper dependency handling
        
        Args:
            components: List of VB6 components to translate
            
        Returns:
            Dictionary mapping component names to translated C# components
        """
        self.logger.info(f"Starting translation of {len(components)} components")
        
        # Create translation tasks
        self.tasks = {
            comp.name: TranslationTask(component=comp)
            for comp in components
        }
        
        # Resolve dependencies and get translation order
        try:
            translation_order = self._get_translation_order(components)
        except Exception as e:
            self.logger.error(f"Failed to resolve dependencies: {e}")
            # Fallback to simple ordering
            translation_order = [comp.name for comp in components]
        
        # Execute translations
        self._execute_translations(translation_order)
        
        # Log translation timing summary
        self._log_translation_timing_summary()
        
        self.logger.info(f"Translation completed. {len(self.completed_translations)} successful, {len(self.failed_translations)} failed")
        
        return self.completed_translations
    
    def _get_translation_order(self, components: List[VB6Component]) -> List[str]:
        """Determine optimal translation order based on dependencies"""
        # Build dependency map
        dependencies = {}
        for comp in components:
            # Filter dependencies to only include components in this project
            project_deps = [
                dep for dep in comp.dependencies 
                if any(other.name == dep for other in components)
            ]
            dependencies[comp.name] = project_deps
        
        # Use dependency resolver to get order
        return self.dependency_resolver.resolve_dependencies(dependencies)
    
    def _execute_translations(self, translation_order: List[str]):
        """Execute translations in the specified order"""
        
        if self.max_workers == 1:
            # Sequential processing
            for component_name in translation_order:
                self._translate_component(component_name)
        else:
            # Parallel processing with dependency constraints
            self._execute_parallel_translations(translation_order)
    
    def _execute_parallel_translations(self, translation_order: List[str]):
        """Execute translations in parallel while respecting dependencies"""
        
        completed = set()
        remaining = set(translation_order)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while remaining:
                # Find components ready for translation (dependencies satisfied)
                ready = []
                for comp_name in remaining:
                    task = self.tasks[comp_name]
                    deps_satisfied = all(
                        dep in completed or dep not in remaining
                        for dep in task.component.dependencies
                    )
                    if deps_satisfied:
                        ready.append(comp_name)
                
                if not ready:
                    # No components ready - might indicate circular dependencies
                    # Translate remaining components anyway
                    ready = list(remaining)[:self.max_workers]
                    self.logger.warning("Possible circular dependencies detected, proceeding with remaining components")
                
                # Submit translation tasks
                future_to_name = {}
                for comp_name in ready[:self.max_workers]:
                    future = executor.submit(self._translate_component, comp_name)
                    future_to_name[future] = comp_name
                    remaining.remove(comp_name)
                
                # Wait for completion
                for future in as_completed(future_to_name):
                    comp_name = future_to_name[future]
                    try:
                        future.result()  # This will raise any exception that occurred
                        completed.add(comp_name)
                    except Exception as e:
                        self.logger.error(f"Translation failed for {comp_name}: {e}")
                        self.failed_translations[comp_name] = str(e)
    
    def _translate_component(self, component_name: str) -> bool:
        """
        Translate a single component
        
        Returns:
            True if translation successful, False otherwise
        """
        task = self.tasks[component_name]
        task.status = TranslationStatus.IN_PROGRESS
        task.start_time = time.time()
        
        try:
            # Select best agent for this component
            agent = self._select_agent(task.component)
            if not agent:
                raise ValueError(f"No suitable agent found for {task.component.component_type}")
            
            task.assigned_agent = agent.name
            self.logger.info(f"Translating {component_name} with {agent.name}")
            
            # Perform translation
            result = agent.translate(task.component)
            
            # Store results
            task.result = result
            task.status = TranslationStatus.COMPLETED
            task.end_time = time.time()
            
            self.completed_translations[component_name] = result
            
            duration = task.end_time - task.start_time
            self.logger.info(f"✅ Successfully translated {component_name} in {duration:.2f}s using {agent.name}")
            
            # Log component-specific timing details
            component_type = task.component.component_type.value
            self.logger.debug(f"📊 {component_name} ({component_type}): {duration:.2f}s")
            
            return True
            
        except Exception as e:
            task.status = TranslationStatus.FAILED
            task.end_time = time.time()
            task.error = str(e)
            
            # Retry logic
            if task.retry_count < self.max_retries:
                task.retry_count += 1
                self.logger.warning(f"Translation failed for {component_name}, retrying ({task.retry_count}/{self.max_retries}): {e}")
                return self._translate_component(component_name)  # Retry
            else:
                self.logger.error(f"Translation failed for {component_name} after {self.max_retries} retries: {e}")
                self.failed_translations[component_name] = str(e)
                return False
    
    def _select_agent(self, component: VB6Component) -> Optional[BaseTranslationAgent]:
        """Select the best agent for translating the given component"""
        
        # Find agents that can handle this component type
        capable_agents = [
            agent for agent in self.agents.values()
            if agent.can_handle(component)
        ]
        
        if not capable_agents:
            return None
        
        # Select agent with highest priority score
        best_agent = max(capable_agents, key=lambda a: a.get_priority_score(component))
        return best_agent
    
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
                component_type = task.component.component_type.value
                self.logger.info(f"  • {task.component.name} ({component_type}): {duration:.2f}s [{task.assigned_agent}]")
        
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
                # Determine file category and save location
                if component.namespace == "Translated.Forms":
                    category = "forms"
                elif component.namespace == "Translated.Business":
                    category = "business_logic"
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
                
                # Additional metadata
                for key, value in component.metadata.items():
                    if key not in ['original_file', 'using_statements', 'designer_code']:
                        f.write(f"  - {key}: {value}\n")


def run_standalone_translation(project_path: str, output_dir: str = None, 
                              max_workers: int = 3, max_retries: int = 2) -> Dict[str, Any]:
    """
    Standalone function for running translation directly (for testing/debugging)
    
    Args:
        project_path: Path to VB6 project file or directory
        output_dir: Output directory for translated files
        max_workers: Maximum number of parallel workers
        max_retries: Maximum number of retries for failed translations
        
    Returns:
        Dictionary with translation results and summary
    """
    # Initialize orchestrator
    orchestrator = TranslationOrchestrator(
        max_workers=max_workers,
        max_retries=max_retries
    )
    
    try:
        # Analyze project
        project_path_obj = Path(project_path)
        components = orchestrator.analyze_vb6_project(project_path_obj)
        
        # Translate project
        results = orchestrator.translate_project(components)
        
        # Get summary
        summary = orchestrator.get_translation_summary()
        
        # Save results if output directory specified
        saved_files = {}
        if output_dir:
            output_dir_obj = Path(output_dir)
            output_dir_obj.mkdir(parents=True, exist_ok=True)
            
            # Save the entire project with proper structure
            project_name = project_path_obj.stem if project_path_obj.is_file() else project_path_obj.name
            saved_files = orchestrator.save_translated_project(output_dir_obj, project_name)
        
        return {
            'success': True,
            'components': len(components),
            'results': results,
            'summary': summary,
            'saved_files': saved_files
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'components': 0,
            'results': {},
            'summary': {},
            'saved_files': {}
        }


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
    parser.add_argument("--max-workers", type=int, default=3, help="Maximum number of parallel workers")
    parser.add_argument("--max-retries", type=int, default=2, help="Maximum number of retries for failed translations")
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
    
    # Run standalone translation
    result = run_standalone_translation(
        args.project_path,
        args.output_dir,
        args.max_workers,
        args.max_retries
    )
    
    if result['success']:
        print(f"Found {result['components']} components to translate")
        
        # Print summary
        summary = result['summary']
        if summary and 'progress' in summary:
            print(f"\nTranslation Summary:")
            print(f"  Total components: {summary['progress']['total']}")
            print(f"  Successful: {summary['progress']['completed']}")
            print(f"  Failed: {summary['progress']['failed']}")
            print(f"  Success rate: {summary['progress']['success_rate']:.1f}%")
            print(f"  Average time per component: {summary['average_translation_time']:.2f}s")
            
            if summary.get('failed_components'):
                print(f"  Failed components: {', '.join(summary['failed_components'])}")
        
        # Print saved files info
        saved_files = result['saved_files']
        if saved_files:
            print(f"\nSaved translated project:")
            for category, files in saved_files.items():
                if files:
                    print(f"  {category.replace('_', ' ').title()}: {len(files)} files")
        
        return 0
    else:
        print(f"Translation failed: {result['error']}")
        return 1


if __name__ == "__main__":
    exit(main())
