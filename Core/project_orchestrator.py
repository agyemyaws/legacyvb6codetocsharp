"""
Project Orchestrator
Master coordinator for the entire VB6 to C# translation workflow.

This orchestrator:
1. Analyzes VB6 project structure and complexity
2. Plans optimal translation strategy
3. Coordinates between all translation agents
4. Monitors progress and handles errors
6. Generates final structured output
"""

import logging
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from Core.analyzer import VB6Analyzer, VB6Project
from settings import get_settings
from Translation.translator_orchestrator import TranslationOrchestrator


class TranslationPhase(Enum):
    """Translation workflow phases"""
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    OUTPUT_GENERATION = "output_generation"
    COMPLETED = "completed"
    FAILED = "failed"


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
    translated_files: Dict[str, Path] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


class ProjectOrchestrator:
    """
    Master coordinator for VB6 to C# translation projects.
    
    Orchestrates the entire translation workflow from analysis to final output.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.settings = get_settings()
        
        # Initialize core components
        self.analyzer = VB6Analyzer()
        self.translation_orchestrator = None  # Will be created when project is analyzed
        
        # Initialize state tracking
        self.current_progress: Optional[TranslationProgress] = None
        self.current_project: Optional[VB6Project] = None
        
    
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
            phase_start = time.time()
            
            vb6_project = self._analyze_project(project_path)
            if not vb6_project:
                return self._create_failed_result("Project analysis failed", output_dir)
            
            self.current_project = vb6_project
            self.current_progress.total_components = len(vb6_project.files)
            
            # Create translation orchestrator with project root
            self.translation_orchestrator = TranslationOrchestrator(
                max_workers=self.settings.MAX_WORKERS,
                max_retries=self.settings.MAX_RETRIES,
                project_root=Path(vb6_project.name)
            )
            
            analysis_time = time.time() - phase_start
            self.current_progress.phase_times['analysis'] = analysis_time
            self.logger.info(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
            self.logger.info(f"📊 Found {len(vb6_project.files)} components: {dict(Counter(f.file_type for f in vb6_project.files.values()))}")
            self.logger.info(f"📋 Translation order: {' → '.join(vb6_project.translation_order)}")
            
            # Phase 2: Translation 
            self.logger.info("Phase 2: Executing translation")
            self.current_progress.current_phase = TranslationPhase.TRANSLATION
            phase_start = time.time()
            
            translation_results = self._execute_translation(vb6_project, output_dir)
            translation_time = time.time() - phase_start
            self.current_progress.phase_times['translation'] = translation_time
            self.logger.info(f"⏱️  Translation completed in {translation_time:.2f} seconds")
            self.logger.info(f"📊 Success: {self.current_progress.completed_components}/{self.current_progress.total_components} components")
            self.logger.info(f"🔄 Rate: {self.current_progress.completed_components/max(translation_time, 1):.2f} components/second")
            
            # Phase 3: Finalization
            self.logger.info("Phase 3: Finalizing translation")
            self.current_progress.current_phase = TranslationPhase.OUTPUT_GENERATION
            phase_start = time.time()
            
            # Translation is complete - files are already saved by TranslationOrchestrator
            output_time = time.time() - phase_start
            self.current_progress.phase_times['output_generation'] = output_time
            self.logger.info(f"⏱️  Translation finalized in {output_time:.2f} seconds")
            self.logger.info(f"📁 Translated files available in: {output_dir}")
            
            # Complete
            self.current_progress.current_phase = TranslationPhase.COMPLETED
            self.current_progress.end_time = time.time()
            
            # Log total translation time
            total_time = self.current_progress.end_time - self.current_progress.start_time
            self.logger.info(f"Translation completed in {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
            
            return TranslationResult(
                success=True,
                project_name=vb6_project.name,
                output_path=output_dir,
                progress=self.current_progress,
                translated_files=translation_results,
                metrics=self._calculate_metrics(),
                summary=f"Translation of '{vb6_project.name}' completed successfully."
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
                self.logger.info(f"Files: {len(vb6_project.files)}")
                self.logger.info(f"External dependencies: {len(vb6_project.external_dependencies)}")
                
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
    

    
    def _execute_translation(self, vb6_project: VB6Project, output_dir: Path) -> Dict[str, Path]:
        """Execute translation using analyzer's translation order with controlled concurrency"""
        
        self.logger.info("Converting VB6Project to their corresponding C# components")
        
        # Use VB6Files from analyzer
        components_map = vb6_project.files
        
        # Set project context on translation orchestrator for smart dependency resolution
        self.translation_orchestrator.set_project_context(components_map)
        
        # Initialize translation orchestrator's task tracking
        self.translation_orchestrator.tasks = {}
        self.translation_orchestrator.completed_translations = {}
        self.translation_orchestrator.failed_translations = {}
        
        # Execute translation using analyzer's order with controlled concurrency
        completed = set()
        remaining = set(vb6_project.translation_order)
        max_concurrent = self.settings.MAX_WORKERS
        
        self.logger.info(f"Starting ordered translation with max {max_concurrent} concurrent workers")
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            while remaining:
                # Find components ready for translation (dependencies satisfied)
                ready = []
                for comp_name in remaining:
                    if comp_name not in components_map:
                        continue
                        
                    vb6_file = components_map[comp_name]
                    deps_satisfied = all(
                        dep in completed or dep not in remaining
                        for dep in vb6_file.dependencies
                    )
                    if deps_satisfied:
                        ready.append(comp_name)
                
                if not ready:
                    # No components ready - might indicate circular dependencies
                    # Take the first few components anyway to make progress
                    ready = list(remaining)[:max_concurrent]
                    self.logger.warning("Possible circular dependencies detected, proceeding with remaining components")
                
                # Submit translation tasks (up to max_concurrent)
                future_to_name = {}
                for comp_name in ready[:max_concurrent]:
                    vb6_file = components_map[comp_name]  # Get the VB6File object
                    future = executor.submit(self.translation_orchestrator._translate_component, comp_name, vb6_file)
                    future_to_name[future] = comp_name
                    remaining.remove(comp_name)
                    self.logger.info(f"Started translation of {comp_name}")
                
                # Wait for completion
                for future in as_completed(future_to_name):
                    comp_name = future_to_name[future]
                    try:
                        success = future.result()  # This will raise any exception that occurred
                        if success:
                            completed.add(comp_name)
                            self.logger.info(f"✅ Completed translation of {comp_name}")
                        else:
                            self.logger.error(f"❌ Failed translation of {comp_name}")
                    except Exception as e:
                        self.logger.error(f"Translation failed for {comp_name}: {e}")
        
        translated_components = self.translation_orchestrator.completed_translations
        self.logger.info(f"Translation completed: {len(translated_components)} components translated")
        
        # Use the translation orchestrator's save functionality for consistent output
        project_name = vb6_project.name
        saved_files = self.translation_orchestrator.save_translated_project(output_dir, project_name)
        
        # Update progress tracking
        self.current_progress.completed_components = len(translated_components)
        self.current_progress.failed_components = len(components_map) - len(translated_components)
        
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
            'phase_breakdown': self.current_progress.phase_times
        }
    

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
            summary=f"Translation failed: {error_message}"
        )


def main():
    """Test the ProjectOrchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="VB6 to C# Project Translation Orchestrator")
    parser.add_argument("project_path", help="Path to VB6 project file or directory")
    parser.add_argument("--output-dir", help="Output directory for translated files")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize orchestrator (uses settings.py for configuration)
    orchestrator = ProjectOrchestrator()
    
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
