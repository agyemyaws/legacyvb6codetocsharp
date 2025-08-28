#!/usr/bin/env python3
"""
VB6 to C# Translation Pipeline - Main Entry Point

This is the primary interface for translating VB6 projects to modern C#.
Handles command-line arguments, initializes the system, and orchestrates the translation process.

Usage:
    python main.py <vb6_project_path> [options]
    
Examples:
    python main.py Data/Input/BMI/bmi.vbp
    python main.py Data/Input/BMI --output-dir Data/Output/BMI_Translated
    python main.py Data/Input/TrainPlan --max-workers 4
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent))

from Core.project_orchestrator import ProjectOrchestrator
from Utils.logging_config import setup_logging


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    
    parser = argparse.ArgumentParser(
        description="VB6 to C# Translation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s Data/Input/BMI/bmi.vbp
  %(prog)s Data/Input/BMI --output-dir Data/Output/BMI_Translated
  %(prog)s Data/Input/BMI --verbose"""
    )
    
    # Required arguments
    parser.add_argument(
        "project_path",
        help="Path to VB6 project file (.vbp) or directory containing VB6 code"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir", "-o",
        help="Output directory for translated C# files (default: <project_path>_Translated)"
    )
    
    parser.add_argument(
        "--max-workers", "-w",
        type=int,
        default=3,
        help="Maximum number of parallel workers (default: 3)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--log-file",
        help="Write log output to specific file (default: logs/vb6_analyzer_TIMESTAMP.log)"
    )
    
    parser.add_argument(
        "--enable-validation",
        action="store_true",
        help="Enable translation validation (requires evaluation framework)"
    )
    
    return parser.parse_args()


def setup_application(args: argparse.Namespace) -> None:
    """Initialize application settings and logging"""
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    
    setup_logging(
        level=log_level,
        log_file=args.log_file,
        task_name="translation"
    )
    
    logger = logging.getLogger(__name__)
    logger.info("VB6 to C# Translation Pipeline started")
    if args.verbose:
        logger.info(f"Arguments: {vars(args)}")


def validate_inputs(args: argparse.Namespace) -> bool:
    """Validate user inputs and project path"""
    
    project_path = Path(args.project_path)
    
    # Check if project path exists
    if not project_path.exists():
        print(f"❌ Error: Project path does not exist: {project_path}")
        return False
    
    # Check if it's a valid VB6 project
    if project_path.is_file():
        if project_path.suffix.lower() != '.vbp':
            print(f"❌ Error: File must be a VB6 project file (.vbp): {project_path}")
            return False
    elif project_path.is_dir():
        # Look for .vbp files in directory
        vbp_files = list(project_path.glob("*.vbp"))
        if not vbp_files:
            print(f"❌ Error: No VB6 project files (.vbp) found in directory: {project_path}")
            return False
    else:
        print(f"❌ Error: Invalid project path: {project_path}")
        return False
    
    # Validate max workers
    if args.max_workers < 1 or args.max_workers > 10:
        print(f"❌ Error: Max workers must be between 1 and 10, got: {args.max_workers}")
        return False
    
    return True


def display_startup_info(project_path: Path, output_dir: Path) -> None:
    """Display welcome message and project info"""
    
    print("🔄 VB6 to C# Translation Pipeline")
    print("=" * 50)
    print("Transforming legacy VB6 code to modern C#")
    print()
    print(f"📁 Project: {project_path.name}")
    print(f"📍 Source:  {project_path}")
    print(f"📍 Output:  {output_dir}")
    print()


def display_results(result, duration_str: str) -> None:
    """Display final translation results"""
    
    print("\n" + "=" * 50)
    
    if result.success:
        print("🎉 TRANSLATION COMPLETED SUCCESSFULLY!")
        print(f"✅ Project: {result.project_name}")
        print(f"📁 Output: {result.output_path}")
        print(f"📊 Files translated: {len(result.translated_files)}")
        print(f"⏱️  Duration: {duration_str}")
        
        print("\n🚀 Next Steps:")
        print("   1. Open the generated .sln file in Visual Studio")
        print("   2. Restore NuGet packages and test the code")
        
    else:
        print("❌ TRANSLATION FAILED")
        print(f"⏱️  Duration: {duration_str}")
        if hasattr(result, 'progress') and result.progress and hasattr(result.progress, 'errors') and result.progress.errors:
            print("Recent errors:")
            for error in result.progress.errors[:3]:
                print(f"   • {error}")
        print("\n💡 Try with --verbose flag for more details")


def main() -> int:
    """Main application entry point"""
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Validate inputs
        if not validate_inputs(args):
            return 1
        
        # Setup application
        setup_application(args)
        
        # Determine output directory
        project_path = Path(args.project_path)
        output_dir = Path(args.output_dir) if args.output_dir else project_path.parent / f"{project_path.stem}_Translated"
        
        # Display startup information
        display_startup_info(project_path, output_dir)
        
        # Initialize orchestrator
        config = {
            'max_workers': args.max_workers,
            'verbose': args.verbose,
            'enable_validation': args.enable_validation
        }
        
        orchestrator = ProjectOrchestrator(config)
        print("🚀 Starting translation...\n")
        
        # Execute translation with timing
        start_time = time.time()
        result = orchestrator.translate_project(str(project_path), str(output_dir))
        end_time = time.time()
        
        # Calculate duration
        duration = end_time - start_time
        duration_str = f"{duration:.1f} seconds" if duration < 60 else f"{duration/60:.1f} minutes"
        
        # Display results
        display_results(result, duration_str)
        
        # Log final status
        logger = logging.getLogger(__name__)
        if result.success:
            logger.info(f"🎉 Translation completed successfully in {duration_str}")
            return 0
        else:
            logger.error(f"❌ Translation failed after {duration_str}")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Translation interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logging.getLogger(__name__).exception("Unexpected error")
        return 1


if __name__ == "__main__":
    exit(main())
