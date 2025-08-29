"""
Project Orchestrator
Master coordinator for the entire VB6 to C# translation workflow.

This orchestrator:
1. Analyzes VB6 project structure and complexity
2. Plans optimal translation strategy
3. Coordinates between all translation agents
4. Monitors progress and handles errors
5. Manages validation and testing phases
6. Generates final structured output
"""

import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import json

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from Core.analyzer import VB6Analyzer, VB6Project, VB6File
from Translation.translator_orchestrator import TranslationOrchestrator, ComponentType, VB6Component
from Utils.dependency_resolver import DependencyResolver
from Utils.vb6_parser import VB6Parser
from Evaluation.evaluator import TranslationEvaluator


class TranslationPhase(Enum):
    """Translation workflow phases"""
    ANALYSIS = "analysis"
    PLANNING = "planning"
    TRANSLATION = "translation"
    VALIDATION = "validation"
    OUTPUT_GENERATION = "output_generation"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranslationPlan:
    """Represents a translation execution plan"""
    phases: List[TranslationPhase] = field(default_factory=list)
    agent_assignments: Dict[str, str] = field(default_factory=dict)  # component -> agent
    translation_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)


@dataclass
class TranslationProgress:
    """Tracks translation progress across all phases"""
    current_phase: TranslationPhase = TranslationPhase.ANALYSIS
    total_components: int = 0
    completed_components: int = 0
    failed_components: int = 0
    skipped_components: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    phase_times: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TranslationResult:
    """Final result of the translation process"""
    success: bool
    project_name: str
    output_path: Path
    progress: TranslationProgress
    plan: TranslationPlan
    translated_files: Dict[str, Path] = field(default_factory=dict)
    generated_projects: List[Path] = field(default_factory=list)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


class ProjectOrchestrator:
    """
    Master coordinator for VB6 to C# translation projects.
    
    Orchestrates the entire translation workflow from analysis to final output.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, progress_callback=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        self.progress_callback = progress_callback
        
        # Initialize core components
        self.analyzer = VB6Analyzer()
        self.translation_orchestrator = TranslationOrchestrator(
            max_workers=self.config.get('max_workers', 3),
            max_retries=self.config.get('max_retries', 2)
        )
        self.dependency_resolver = DependencyResolver()
        
        # Initialize evaluator if available
        try:
            self.evaluator = TranslationEvaluator()
            self.evaluation_available = True
        except Exception as e:
            self.logger.warning(f"TranslationEvaluator not available: {e}")
            self.evaluator = None
            self.evaluation_available = False
        
        # Workflow state
        self.current_project: Optional[VB6Project] = None
        self.current_plan: Optional[TranslationPlan] = None
        self.current_progress: Optional[TranslationProgress] = None
    
    def translate_project(self, vb6_project_path: str, output_path: str = None) -> TranslationResult:
        """
        Translate a complete VB6 project to C# using modern patterns and practices
        
        Args:
            vb6_project_path: Path to VB6 project file or directory
            output_path: Output directory for translated files
            
        Returns:
            TranslationResult containing all translation outcomes
        """
        
        project_path = Path(vb6_project_path)
        output_dir = Path(output_path) if output_path else project_path.parent / "Translated"
        
        self.logger.info(f"Starting project translation: {project_path}")
        
        # Initialize progress tracking
        self.current_progress = TranslationProgress(
            current_phase=TranslationPhase.ANALYSIS,
            start_time=time.time()
        )
        
        # Log overall start time
        self.logger.info(f"🚀 Starting translation workflow at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"📁 Project: {project_path}")
        self.logger.info(f"📍 Output: {output_dir}")
        
        try:
            # Phase 1: Analysis
            self.logger.info("Phase 1: Analyzing VB6 project structure")
            self.current_progress.current_phase = TranslationPhase.ANALYSIS
            self._report_progress("Starting project analysis")
            phase_start = time.time()
            
            vb6_project = self._analyze_project(project_path)
            if not vb6_project:
                return self._create_failed_result("Project analysis failed", output_dir)
            
            self.current_project = vb6_project
            self.current_progress.total_components = len(vb6_project.files)
            analysis_time = time.time() - phase_start
            self.current_progress.phase_times['analysis'] = analysis_time
            self.logger.info(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
            self.logger.info(f"📊 Found {len(vb6_project.files)} components: {dict(Counter(f.file_type for f in vb6_project.files.values()))}")
            self._report_progress(f"Analysis complete: {len(vb6_project.files)} components found")
            
            # Phase 2: Planning
            self.logger.info("Phase 2: Planning translation strategy")
            self.current_progress.current_phase = TranslationPhase.PLANNING
            self._report_progress("Creating translation plan")
            phase_start = time.time()
            
            translation_plan = self._create_translation_plan(vb6_project)
            self.current_plan = translation_plan
            planning_time = time.time() - phase_start
            self.current_progress.phase_times['planning'] = planning_time
            self.logger.info(f"⏱️  Planning completed in {planning_time:.2f} seconds")
            self.logger.info(f"📋 Plan: {translation_plan.complexity_score:.1f} complexity, {translation_plan.estimated_duration:.1f}min estimated")
            self._report_progress("Translation plan created using modernization approach")
            
            # Phase 3: Translation
            self.logger.info("Phase 3: Executing translation")
            self.current_progress.current_phase = TranslationPhase.TRANSLATION
            self._report_progress("Starting component translation")
            phase_start = time.time()
            
            translation_results = self._execute_translation(vb6_project, translation_plan, output_dir)
            translation_time = time.time() - phase_start
            self.current_progress.phase_times['translation'] = translation_time
            self.logger.info(f"⏱️  Translation completed in {translation_time:.2f} seconds")
            self.logger.info(f"📊 Success: {self.current_progress.completed_components}/{self.current_progress.total_components} components")
            self.logger.info(f"🔄 Rate: {self.current_progress.completed_components/max(translation_time, 1):.2f} components/second")
            self._report_progress(f"Translation completed: {len(translation_results)} files generated")
            
            # Phase 4: Validation (optional - can be enabled later)
            self.logger.info("Phase 4: Validation phase")
            self.current_progress.current_phase = TranslationPhase.VALIDATION
            phase_start = time.time()
            
            if self.evaluator and self.config.get('enable_validation', False):
                self.logger.info("Running translation validation")
                validation_results = self._validate_translation(translation_results, output_dir)
            else:
                self.logger.info("Skipping validation - evaluator not available or disabled")
                validation_results = {
                    "skipped": True, 
                    "reason": "Evaluator not available or validation disabled",
                    "evaluator_available": self.evaluation_available,
                    "validation_enabled": self.config.get('enable_validation', False)
                }
            
            validation_time = time.time() - phase_start
            self.current_progress.phase_times['validation'] = validation_time
            self.logger.info(f"⏱️  Validation completed in {validation_time:.2f} seconds")
            
            # Phase 5: Output Generation
            self.logger.info("Phase 5: Generating final output")
            self.current_progress.current_phase = TranslationPhase.OUTPUT_GENERATION
            self._report_progress("Generating project files and documentation")
            phase_start = time.time()
            
            final_output = self._generate_final_output(translation_results, output_dir)
            output_time = time.time() - phase_start
            self.current_progress.phase_times['output_generation'] = output_time
            self.logger.info(f"⏱️  Output generation completed in {output_time:.2f} seconds")
            self.logger.info(f"📦 Generated {len(final_output)} project files")
            self._report_progress(f"Output generation complete: {len(final_output)} project files created")
            
            # Complete
            self.current_progress.current_phase = TranslationPhase.COMPLETED
            self.current_progress.end_time = time.time()
            
            # Log comprehensive timing summary
            self._log_timing_summary()
            self._report_progress("Translation workflow completed successfully")
            
            return TranslationResult(
                success=True,
                project_name=vb6_project.name,
                output_path=output_dir,
                progress=self.current_progress,
                plan=translation_plan,
                translated_files=translation_results,
                generated_projects=final_output,
                validation_results=validation_results,
                metrics=self._calculate_metrics(),
                summary=self._generate_summary()
            )
            
        except Exception as e:
            self.logger.error(f"Project translation failed: {e}")
            self.current_progress.current_phase = TranslationPhase.FAILED
            self.current_progress.end_time = time.time()
            self.current_progress.errors.append(str(e))
            
            return self._create_failed_result(str(e), output_dir)
    
    def _analyze_project(self, project_path: Path) -> Optional[VB6Project]:
        """Analyze VB6 project structure and dependencies"""
        
        try:
            if project_path.is_file() and project_path.suffix.lower() == '.vbp':
                # Analyze project file
                vb6_project = self.analyzer.analyze_project(project_path)
            elif project_path.is_dir():
                # Analyze directory - returns list, take first project
                projects = self.analyzer.analyze_directory(str(project_path))
                vb6_project = projects[0] if projects else None
            else:
                raise ValueError(f"Invalid project path: {project_path}")
            
            if vb6_project:
                self.logger.info(f"Analyzed project: {vb6_project.name}")
                self.logger.info(f"  Files: {len(vb6_project.files)}")
                self.logger.info(f"  External dependencies: {len(vb6_project.external_dependencies)}")
                
                # Log file breakdown
                file_types = {}
                for vb6_file in vb6_project.files.values():
                    file_types[vb6_file.file_type] = file_types.get(vb6_file.file_type, 0) + 1
                
                for file_type, count in file_types.items():
                    self.logger.info(f"  {file_type.title()}s: {count}")
            
            return vb6_project
            
        except Exception as e:
            self.logger.error(f"Project analysis failed: {e}")
            return None
    
    def _create_translation_plan(self, vb6_project: VB6Project) -> TranslationPlan:
        """Create an optimal translation plan based on project analysis using modernization approach"""
        
        plan = TranslationPlan()
        
        # Calculate complexity score
        total_complexity = sum(file.complexity_score for file in vb6_project.files.values())
        total_files = len(vb6_project.files)
        plan.complexity_score = total_complexity / max(total_files, 1)
        
        # Note: Translation order will be determined by the translation orchestrator
        # based on proper dependency resolution during execution
        plan.translation_order = list(vb6_project.files.keys())  # Initial order, will be refined by translator
        
        # Assign agents based on file types
        plan.agent_assignments = self._assign_agents(vb6_project)
        
        # Identify risk factors
        plan.risk_factors = self._identify_risk_factors(vb6_project)
        
        # Create parallel execution groups (using modernization approach)
        plan.parallel_groups = self._create_parallel_groups(vb6_project)
        
        # Estimate duration (using modernization approach)
        plan.estimated_duration = self._estimate_duration(vb6_project)
        
        # Set standard phases for modernization
        plan.phases = [
            TranslationPhase.ANALYSIS,
            TranslationPhase.PLANNING,
            TranslationPhase.TRANSLATION,
            TranslationPhase.VALIDATION,
            TranslationPhase.OUTPUT_GENERATION
        ]
        
        self.logger.info(f"Created translation plan:")
        self.logger.info(f"  Approach: Modern C# patterns and practices")
        self.logger.info(f"  Complexity: {plan.complexity_score:.2f}")
        self.logger.info(f"  Estimated duration: {plan.estimated_duration:.1f} minutes")
        self.logger.info(f"  Risk factors: {len(plan.risk_factors)}")
        self.logger.info(f"  Parallel groups: {len(plan.parallel_groups)}")
        
        return plan
    
    def _assign_agents(self, vb6_project: VB6Project) -> Dict[str, str]:
        """Assign appropriate translation agents to each component"""
        
        assignments = {}
        
        for file_name, vb6_file in vb6_project.files.items():
            if vb6_file.file_type == 'form':
                assignments[file_name] = 'FormAgent'
            elif vb6_file.file_type in ['module', 'class']:
                # Check if it's a database module
                if self._is_database_module(vb6_file):
                    assignments[file_name] = 'DataAccessAgent'
                else:
                    assignments[file_name] = 'BusinessLogicAgent'
            elif vb6_file.file_type == 'control':
                assignments[file_name] = 'FormAgent'
            else:
                assignments[file_name] = 'BusinessLogicAgent'  # Default
        
        return assignments
    
    def _is_database_module(self, vb6_file: VB6File) -> bool:
        """Check if a VB6 file contains database-related code"""
        
        # Check for database-related keywords in dependencies
        db_keywords = {'ADODB', 'Database', 'Recordset', 'Connection', 'SQL'}
        
        if any(keyword.lower() in dep.lower() for dep in vb6_file.external_dependencies for keyword in db_keywords):
            return True
        
        # Check filename patterns
        db_patterns = ['database', 'data', 'db', 'dao', 'ado']
        if any(pattern in vb6_file.name.lower() for pattern in db_patterns):
            return True
        
        return False
    
    def _identify_risk_factors(self, vb6_project: VB6Project) -> List[str]:
        """Identify potential risks in the translation process"""
        
        risks = []
        
        # Check for complex dependencies
        if len(vb6_project.external_dependencies) > 10:
            risks.append("High number of external dependencies")
        
        # Check for large files
        large_files = [f for f in vb6_project.files.values() if f.lines_of_code > 1000]
        if large_files:
            risks.append(f"Large files detected ({len(large_files)} files > 1000 LOC)")
        
        # Check for complex forms
        complex_forms = [f for f in vb6_project.files.values() 
                        if f.file_type == 'form' and f.controls_count > 20]
        if complex_forms:
            risks.append(f"Complex forms with many controls ({len(complex_forms)} forms)")
        
        # Check for circular dependencies
        try:
            # This will raise an exception if circular dependencies exist
            deps = {name: list(file.dependencies) for name, file in vb6_project.files.items()}
            self.dependency_resolver.resolve_dependencies(deps)
        except Exception:
            risks.append("Circular dependencies detected")
        
        # Check for external COM components
        com_deps = [dep for dep in vb6_project.external_dependencies 
                   if any(ext in dep.lower() for ext in ['.ocx', '.dll', 'com', 'activex'])]
        if com_deps:
            risks.append(f"COM/ActiveX components detected ({len(com_deps)} components)")
        
        return risks
    
    def _create_parallel_groups(self, vb6_project: VB6Project) -> List[List[str]]:
        """Create groups of files that can be translated in parallel using modernization approach"""
        
        # Use moderate parallelization - group by file type for optimal balance
        # This allows parallel processing while maintaining good dependency handling
        return self._group_by_file_type(vb6_project)
    
    def _group_by_dependency_levels(self, vb6_project: VB6Project) -> List[List[str]]:
        """Group files by dependency levels for maximum parallelization"""
        
        # Build dependency graph
        deps = {name: list(file.dependencies) for name, file in vb6_project.files.items()}
        
        # Create dependency levels
        levels = []
        remaining = set(vb6_project.files.keys())
        
        while remaining:
            # Find files with no dependencies in remaining set
            level = []
            for file_name in list(remaining):
                file_deps = set(deps.get(file_name, []))
                if not (file_deps & remaining):  # No dependencies in remaining files
                    level.append(file_name)
            
            if not level:
                # Circular dependency or other issue - add remaining files
                level = list(remaining)
            
            levels.append(level)
            remaining -= set(level)
        
        return levels
    
    def _group_by_file_type(self, vb6_project: VB6Project) -> List[List[str]]:
        """Group files by type for moderate parallelization"""
        
        groups = {}
        for file_name, vb6_file in vb6_project.files.items():
            file_type = vb6_file.file_type
            if file_type not in groups:
                groups[file_type] = []
            groups[file_type].append(file_name)
        
        # Return groups in dependency order
        ordered_groups = []
        type_order = ['module', 'class', 'form', 'control']
        
        for file_type in type_order:
            if file_type in groups:
                ordered_groups.append(groups[file_type])
        
        # Add any remaining types
        for file_type, files in groups.items():
            if file_type not in type_order:
                ordered_groups.append(files)
        
        return ordered_groups
    
    def _estimate_duration(self, vb6_project: VB6Project) -> float:
        """Estimate translation duration in minutes using modernization approach"""
        
        base_time_per_file = {
            'form': 5.0,      # Forms take longer due to UI complexity
            'class': 3.0,     # Classes need careful property translation
            'module': 2.0,    # Modules are generally simpler
            'control': 4.0    # Controls similar to forms
        }
        
        total_time = 0.0
        
        for vb6_file in vb6_project.files.values():
            base_time = base_time_per_file.get(vb6_file.file_type, 2.0)
            
            # Adjust for complexity
            complexity_multiplier = 1.0 + (vb6_file.complexity_score / 100.0)
            
            # Adjust for file size
            size_multiplier = 1.0 + (vb6_file.lines_of_code / 1000.0)
            
            file_time = base_time * complexity_multiplier * size_multiplier
            total_time += file_time
        
        # Apply modernization multiplier (takes more time due to pattern transformation)
        total_time *= 1.2
        
        # Add overhead for analysis, planning, validation
        total_time *= 1.3
        
        return total_time
    
    def _execute_translation(self, vb6_project: VB6Project, plan: TranslationPlan, 
                           output_dir: Path) -> Dict[str, Path]:
        """Execute the translation according to the plan"""
        
        self.logger.info("Converting VB6Project to translation components")
        
        # Convert VB6Project to components for TranslationOrchestrator
        components = []
        
        for file_name, vb6_file in vb6_project.files.items():
            # Map file type to component type
            component_type_map = {
                'form': ComponentType.FORM,
                'class': ComponentType.CLASS,
                'module': ComponentType.MODULE,
                'control': ComponentType.CONTROL
            }
            
            component_type = component_type_map.get(vb6_file.file_type, ComponentType.MODULE)
            
            # Create VB6Component with parsed data
            component = VB6Component(
                name=file_name,
                file_path=vb6_file.path,
                component_type=component_type,
                dependencies=list(vb6_file.dependencies),
                external_references=list(vb6_file.external_dependencies)
            )
            
            # Parse the file content for translation
            try:
                parsed_data = self.translation_orchestrator.vb6_parser.parse_file(vb6_file.path)
                component.parsed_data = parsed_data
                self.logger.debug(f"Parsed component: {file_name}")
            except Exception as e:
                self.logger.warning(f"Failed to parse {file_name}: {e}")
                # Component will still be processed, but with limited information
            
            components.append(component)
        
        self.logger.info(f"Prepared {len(components)} components for translation")
        
        # Execute translation using the translation orchestrator
        # The translation orchestrator will handle proper dependency resolution and ordering
        translated_components = self.translation_orchestrator.translate_project(components)
        
        self.logger.info(f"Translation completed: {len(translated_components)} components translated")
        
        # Use the translation orchestrator's save functionality for consistent output
        project_name = vb6_project.name
        saved_files = self.translation_orchestrator.save_translated_project(output_dir, project_name)
        
        # Update progress tracking
        self.current_progress.completed_components = len(translated_components)
        self.current_progress.failed_components = len(components) - len(translated_components)
        
        # Convert saved_files structure to flat dictionary for compatibility
        translated_files = {}
        for category, file_list in saved_files.items():
            for file_path in file_list:
                # Use file stem as key, but ensure uniqueness
                key = file_path.stem
                if key in translated_files:
                    key = f"{key}_{category}"
                translated_files[key] = file_path
        
        return translated_files
    
    def _validate_translation(self, translated_files: Dict[str, Path], output_dir: Path) -> Dict[str, Any]:
        """Validate the translation results"""
        
        validation_results = {
            'compilation_check': False,
            'syntax_errors': [],
            'warnings': [],
            'metrics': {}
        }
        
        if self.evaluator:
            try:
                # Run evaluation if available
                eval_results = self.evaluator.evaluate_translation(translated_files, output_dir)
                validation_results.update(eval_results)
            except Exception as e:
                self.logger.warning(f"Evaluation failed: {e}")
                validation_results['evaluation_error'] = str(e)
        else:
            self.logger.info("Evaluation framework not available, skipping validation")
        
        return validation_results
    
    def _generate_final_output(self, translated_files: Dict[str, Path], output_dir: Path) -> List[Path]:
        """Generate final project structure and files"""
        
        generated_projects = []
        
        # Generate C# project file
        project_file = self._generate_csharp_project(translated_files, output_dir)
        if project_file:
            generated_projects.append(project_file)
        
        # Generate solution file
        solution_file = self._generate_solution_file(translated_files, output_dir)
        if solution_file:
            generated_projects.append(solution_file)
        
        # Generate README
        readme_file = self._generate_readme(output_dir)
        if readme_file:
            generated_projects.append(readme_file)
        
        return generated_projects
    
    def _generate_csharp_project(self, translated_files: Dict[str, Path], output_dir: Path) -> Optional[Path]:
        """Generate C# project file (.csproj)"""
        
        project_name = self.current_project.name if self.current_project else "TranslatedProject"
        project_file = output_dir / f"{project_name}.csproj"
        
        # Determine if this is a WinForms or console application
        has_forms = any('form' in str(path).lower() or 'designer' in str(path).lower() 
                       for path in translated_files.values())
        
        # Also check if the original project had forms
        if not has_forms and self.current_project:
            has_forms = any(file.file_type == 'form' for file in self.current_project.files.values())
        
        project_content = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>{"WinExe" if has_forms else "Exe"}</OutputType>
    <TargetFramework>net8.0-windows</TargetFramework>
    <UseWindowsForms>{"true" if has_forms else "false"}</UseWindowsForms>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.SqlServer" Version="8.0.0" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Tools" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Logging" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.DependencyInjection" Version="8.0.0" />
  </ItemGroup>

</Project>"""
        
        try:
            with open(project_file, 'w', encoding='utf-8') as f:
                f.write(project_content)
            return project_file
        except Exception as e:
            self.logger.error(f"Failed to generate project file: {e}")
            return None
    
    def _generate_solution_file(self, translated_files: Dict[str, Path], output_dir: Path) -> Optional[Path]:
        """Generate Visual Studio solution file (.sln)"""
        
        project_name = self.current_project.name if self.current_project else "TranslatedProject"
        solution_file = output_dir / f"{project_name}.sln"
        
        # Generate a GUID for the project
        import uuid
        project_guid = str(uuid.uuid4()).upper()
        solution_guid = str(uuid.uuid4()).upper()
        
        solution_content = f"""
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 17
VisualStudioVersion = 17.0.31903.59
MinimumVisualStudioVersion = 10.0.40219.1
Project("{{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}}") = "{project_name}", "{project_name}.csproj", "{{{project_guid}}}"
EndProject
Global
	GlobalSection(SolutionConfigurationPlatforms) = preSolution
		Debug|Any CPU = Debug|Any CPU
		Release|Any CPU = Release|Any CPU
	EndGlobalSection
	GlobalSection(ProjectConfigurationPlatforms) = postSolution
		{{{project_guid}}}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
		{{{project_guid}}}.Debug|Any CPU.Build.0 = Debug|Any CPU
		{{{project_guid}}}.Release|Any CPU.ActiveCfg = Release|Any CPU
		{{{project_guid}}}.Release|Any CPU.Build.0 = Release|Any CPU
	EndGlobalSection
	GlobalSection(SolutionProperties) = preSolution
		HideSolutionNode = FALSE
	EndGlobalSection
	GlobalSection(ExtensibilityGlobals) = postSolution
		SolutionGuid = {{{solution_guid}}}
	EndGlobalSection
EndGlobal
"""
        
        try:
            with open(solution_file, 'w', encoding='utf-8') as f:
                f.write(solution_content.strip())
            return solution_file
        except Exception as e:
            self.logger.error(f"Failed to generate solution file: {e}")
            return None
    
    def _generate_readme(self, output_dir: Path) -> Optional[Path]:
        """Generate README file with translation information"""
        
        readme_file = output_dir / "README.md"
        project_name = self.current_project.name if self.current_project else "Translated Project"
        
        readme_content = f"""# {project_name} - Translated from VB6 to C#

This project has been automatically translated from VB6 to C# using the Legacy Code Translation Pipeline.

## Translation Summary

- **Original Language**: VB6
- **Target Language**: C# (.NET 8)
- **Translation Approach**: Modern C# patterns and practices
- **Files Translated**: {self.current_progress.completed_components if self.current_progress else 'Unknown'}
- **Translation Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}

## Project Structure

The translated project follows modern C# conventions:

- **Forms**: Translated to WinForms with proper designer files
- **Business Logic**: Converted to modern C# classes with proper error handling
- **Data Access**: Migrated to Entity Framework Core with repository pattern
- **Dependencies**: Updated to modern NuGet packages

## Getting Started

1. Open the solution file in Visual Studio 2022 or later
2. Restore NuGet packages
3. Update connection strings in appsettings.json if needed
4. Build and run the application

## Notes

- Review all TODO comments in the generated code
- Test thoroughly before production use
- Consider updating deprecated patterns to modern C# features
- Validate all database operations and connection strings

## Translation Metrics

{self._format_metrics_for_readme()}

---
*Generated by Legacy Code Translation Pipeline*
"""
        
        try:
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            return readme_file
        except Exception as e:
            self.logger.error(f"Failed to generate README: {e}")
            return None
    
    def _format_metrics_for_readme(self) -> str:
        """Format metrics for README display"""
        if not self.current_progress:
            return "No metrics available"
        
        total_time = (self.current_progress.end_time or time.time()) - (self.current_progress.start_time or 0)
        
        return f"""
- **Total Translation Time**: {total_time/60:.1f} minutes
- **Components Processed**: {self.current_progress.total_components}
- **Successfully Translated**: {self.current_progress.completed_components}
- **Failed**: {self.current_progress.failed_components}
- **Warnings**: {len(self.current_progress.warnings)}
- **Errors**: {len(self.current_progress.errors)}
"""
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calculate translation metrics"""
        
        if not self.current_progress:
            return {}
        
        total_time = (self.current_progress.end_time or time.time()) - (self.current_progress.start_time or 0)
        
        return {
            'total_time_seconds': total_time,
            'total_time_minutes': total_time / 60,
            'components_per_minute': self.current_progress.completed_components / max(total_time / 60, 1),
            'success_rate': self.current_progress.completed_components / max(self.current_progress.total_components, 1),
            'phase_breakdown': self.current_progress.phase_times,
            'estimated_vs_actual': {
                'estimated_minutes': self.current_plan.estimated_duration if self.current_plan else 0,
                'actual_minutes': total_time / 60,
                'accuracy': abs(1 - (total_time / 60) / max(self.current_plan.estimated_duration if self.current_plan else 1, 1))
            }
        }
    
    def _generate_summary(self) -> str:
        """Generate a human-readable summary of the translation"""
        
        if not self.current_progress or not self.current_project:
            return "Translation summary not available"
        
        success_rate = self.current_progress.completed_components / max(self.current_progress.total_components, 1) * 100
        total_time = (self.current_progress.end_time or time.time()) - (self.current_progress.start_time or 0)
        
        summary = f"""Translation of '{self.current_project.name}' completed with {success_rate:.1f}% success rate.

Processed {self.current_progress.total_components} components in {total_time/60:.1f} minutes:
- Successfully translated: {self.current_progress.completed_components}
- Failed: {self.current_progress.failed_components}
- Skipped: {self.current_progress.skipped_components}

Approach used: Modern C# patterns and practices
"""
        
        if self.current_progress.errors:
            summary += f"\nErrors encountered: {len(self.current_progress.errors)}"
        
        if self.current_progress.warnings:
            summary += f"\nWarnings: {len(self.current_progress.warnings)}"
        
        return summary
    
    def _create_failed_result(self, error_message: str, output_dir: Path) -> TranslationResult:
        """Create a failed translation result"""
        
        if not self.current_progress:
            self.current_progress = TranslationProgress(
                current_phase=TranslationPhase.FAILED,
                start_time=time.time(),
                end_time=time.time()
            )
        
        self.current_progress.errors.append(error_message)
        
        return TranslationResult(
            success=False,
            project_name="Unknown",
            output_path=output_dir,
            progress=self.current_progress,
            plan=self.current_plan or TranslationPlan(),
            summary=f"Translation failed: {error_message}"
        )
    
    def get_progress(self) -> Optional[TranslationProgress]:
        """Get current translation progress"""
        return self.current_progress
    
    def get_plan(self) -> Optional[TranslationPlan]:
        """Get current translation plan"""
        return self.current_plan
    
    def _report_progress(self, message: str):
        """Report progress to callback if available"""
        if self.progress_callback:
            try:
                self.progress_callback({
                    'phase': self.current_progress.current_phase.value if self.current_progress else 'unknown',
                    'message': message,
                    'progress': self.current_progress,
                    'timestamp': time.time()
                })
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")
    
    def _log_timing_summary(self):
        """Log comprehensive timing summary"""
        if not self.current_progress:
            return
        
        total_time = self.current_progress.end_time - self.current_progress.start_time
        
        self.logger.info("=" * 60)
        self.logger.info("🏁 TRANSLATION TIMING SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"🕐 Total Duration: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        self.logger.info(f"📊 Components: {self.current_progress.completed_components}/{self.current_progress.total_components}")
        self.logger.info(f"🚀 Overall Rate: {self.current_progress.completed_components/max(total_time, 1):.2f} components/second")
        
        # Phase breakdown
        self.logger.info("\n📋 Phase Breakdown:")
        for phase, duration in self.current_progress.phase_times.items():
            percentage = (duration / total_time) * 100 if total_time > 0 else 0
            self.logger.info(f"  • {phase.title()}: {duration:.2f}s ({percentage:.1f}%)")
        
        # Performance metrics
        if self.current_plan:
            estimated = self.current_plan.estimated_duration * 60  # Convert to seconds
            accuracy = abs(total_time - estimated) / max(estimated, 1) * 100
            self.logger.info(f"\n📈 Performance:")
            self.logger.info(f"  • Estimated: {estimated:.1f}s")
            self.logger.info(f"  • Actual: {total_time:.1f}s")
            self.logger.info(f"  • Accuracy: ±{accuracy:.1f}%")
        
        self.logger.info("=" * 60)


def main():
    """Test the ProjectOrchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VB6 to C# Project Translation Orchestrator")
    parser.add_argument("project_path", help="Path to VB6 project file or directory")
    parser.add_argument("--output-dir", help="Output directory for translated files")
    parser.add_argument("--max-workers", type=int, default=3, help="Maximum number of parallel workers")
    parser.add_argument("--config", help="Configuration file path")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration if provided
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
    
    config['max_workers'] = args.max_workers
    
    # Initialize orchestrator
    orchestrator = ProjectOrchestrator(config)
    
    try:
        # Execute translation using modernization approach
        result = orchestrator.translate_project(
            args.project_path,
            args.output_dir
        )
        
        # Print results
        print("\n" + "="*60)
        print("TRANSLATION COMPLETE")
        print("="*60)
        print(result.summary)
        
        if result.success:
            print(f"\nOutput directory: {result.output_path}")
            print(f"Generated files: {len(result.translated_files)}")
            
            if result.generated_projects:
                print("\nGenerated project files:")
                for project_file in result.generated_projects:
                    print(f"  - {project_file}")
        
        print("\nMetrics:")
        for key, value in result.metrics.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        return 0 if result.success else 1
        
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
