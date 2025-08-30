"""
VB6 Code Analyzer
Analyzes VB6 projects to extract dependencies, metrics, and determine translation order.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import logging

sys.path.append(str(Path(__file__).parent.parent))

from Utils.vb6_parser import VB6Parser
from Utils.logging_config import setup_logging


@dataclass
class VB6File:
    """Represents a VB6 file with its metadata"""
    path: Path
    name: str
    file_type: str  # 'form', 'module', 'class', 'project'
    dependencies: Set[str] = field(default_factory=set)
    external_dependencies: Set[str] = field(default_factory=set)
    complexity_score: int = 0
    lines_of_code: int = 0
    functions_count: int = 0
    classes_count: int = 0
    controls_count: int = 0  # For forms
    
    def __post_init__(self):
        """Ensure dependencies are sets"""
        if not isinstance(self.dependencies, set):
            self.dependencies = set(self.dependencies)
        if not isinstance(self.external_dependencies, set):
            self.external_dependencies = set(self.external_dependencies)


@dataclass
class VB6Project:
    """Represents a complete VB6 project"""
    name: str
    path: Path
    project_file: Path
    files: Dict[str, VB6File] = field(default_factory=dict)
    references: List[str] = field(default_factory=list)
    external_dependencies: Set[str] = field(default_factory=set)
    translation_order: List[str] = field(default_factory=list)
    
    def add_file(self, vb6_file: VB6File):
        """Add a VB6 file to the project"""
        self.files[vb6_file.name] = vb6_file
        
    def get_total_complexity(self) -> int:
        """Get total complexity score for the project"""
        return sum(file.complexity_score for file in self.files.values())
    
    def get_total_loc(self) -> int:
        """Get total lines of code for the project"""
        return sum(file.lines_of_code for file in self.files.values())


class VB6Analyzer:
    """Main analyzer for VB6 projects"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.parser = VB6Parser()
        
        # VB6 file extensions
        self.vb6_extensions = {
            '.vbp': 'project',
            '.frm': 'form',
            '.cls': 'class',
            '.bas': 'module',
            '.ctl': 'control',
            '.pag': 'property_page'
        }
        
        # Common external dependencies patterns
        self.external_patterns = {
            'ocx': re.compile(r'Object=\{[^}]+\}#[^#]+#[^#]+#(.+\.ocx)', re.IGNORECASE),
            'dll': re.compile(r'Reference=.*?#(.+\.dll)', re.IGNORECASE),
            'tlb': re.compile(r'Reference=.*?#(.+\.tlb)', re.IGNORECASE),
            'com': re.compile(r'Reference=\*\\G\{([^}]+)\}', re.IGNORECASE)
        }
    
    def analyze_directory(self, directory_path: str) -> List[VB6Project]:
        """
        Analyze a directory for VB6 projects
        
        Args:
            directory_path: Path to directory containing VB6 code
            
        Returns:
            List of analyzed VB6 projects
        """
        directory = Path(directory_path)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        projects = []
        
        # Find all .vbp files
        for vbp_file in directory.rglob("*.vbp"):
            try:
                project = self.analyze_project(vbp_file)
                if project:
                    projects.append(project)
                    self.logger.info(f"Analyzed project: {project.name}")
            except Exception as e:
                self.logger.error(f"Error analyzing project {vbp_file}: {e}")
        
        return projects
    
    def analyze_project(self, vbp_path: Path) -> Optional[VB6Project]:
        """
        Analyze a single VB6 project file
        
        Args:
            vbp_path: Path to the .vbp file
            
        Returns:
            VB6Project object or None if analysis fails
        """
        if not vbp_path.exists():
            self.logger.error(f"Project file not found: {vbp_path}")
            return None
        
        project_dir = vbp_path.parent
        project_name = vbp_path.stem
        
        project = VB6Project(
            name=project_name,
            path=project_dir,
            project_file=vbp_path
        )
        
        # Parse the .vbp file
        self._parse_vbp_file(project, vbp_path)
        
        # Analyze all files referenced in the project
        for file_info in self._get_project_files(vbp_path):
            file_path = project_dir / file_info['path']
            if file_path.exists():
                vb6_file = self._analyze_file(file_path, file_info['type'])
                if vb6_file:
                    project.add_file(vb6_file)
        
        # Resolve dependencies and determine translation order
        project.translation_order = self._determine_translation_order(project)
        
        return project
    
    def _parse_vbp_file(self, project: VB6Project, vbp_path: Path):
        """Parse VB6 project file for references and metadata"""
        try:
            with open(vbp_path, 'r', encoding='latin-1') as file:
                content = file.read()
            
            # Extract references
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('Reference='):
                    project.references.append(line)
                    # Check for external dependencies
                    for dep_type, pattern in self.external_patterns.items():
                        match = pattern.search(line)
                        if match:
                            project.external_dependencies.add(match.group(1))
                            
        except Exception as e:
            self.logger.error(f"Error parsing VBP file {vbp_path}: {e}")
    
    def _get_project_files(self, vbp_path: Path) -> List[Dict[str, str]]:
        """Extract file references from VB6 project file"""
        files = []
        
        try:
            with open(vbp_path, 'r', encoding='latin-1') as file:
                content = file.read()
            
            # Parse different file types
            patterns = {
                'form': re.compile(r'^Form=(.+\.frm)$', re.MULTILINE),
                'module': re.compile(r'^Module=([^;]+);(.+\.bas)$', re.MULTILINE),
                'class': re.compile(r'^Class=([^;]+);(.+\.cls)$', re.MULTILINE),
                'control': re.compile(r'^UserControl=(.+\.ctl)$', re.MULTILINE),
                'property_page': re.compile(r'^PropertyPage=(.+\.pag)$', re.MULTILINE)
            }
            
            for file_type, pattern in patterns.items():
                matches = pattern.findall(content)
                for match in matches:
                    if file_type in ['module', 'class']:
                        # These have name;path format - strip whitespace from both
                        files.append({
                            'name': match[0].strip(),
                            'path': match[1].strip(),
                            'type': file_type
                        })
                    else:
                        # These have just path - strip whitespace
                        clean_path = match.strip()
                        files.append({
                            'name': Path(clean_path).stem,
                            'path': clean_path,
                            'type': file_type
                        })
                        
        except Exception as e:
            self.logger.error(f"Error getting project files from {vbp_path}: {e}")
        
        return files
    
    def _analyze_file(self, file_path: Path, file_type: str) -> Optional[VB6File]:
        """Analyze a single VB6 file"""
        try:
            vb6_file = VB6File(
                path=file_path,
                name=file_path.stem,
                file_type=file_type
            )
            
            # Read file content
            with open(file_path, 'r', encoding='latin-1') as file:
                content = file.read()
            
            # Analyze file content using VB6Parser with regex fallback
            dependencies, complexity, functions_count, classes_count, external_deps = self._analyze_file_content(file_path, content)
            
            # Set all metrics from analysis
            vb6_file.dependencies = dependencies
            vb6_file.external_dependencies = external_deps
            vb6_file.complexity_score = complexity
            vb6_file.functions_count = functions_count
            vb6_file.classes_count = classes_count
            vb6_file.lines_of_code = len(content.splitlines())
            
            return vb6_file
            
        except Exception as e:
            self.logger.error(f"Error analyzing file {file_path}: {e}")
            return None
    
    def _analyze_file_content(self, file_path: Path, content: str) -> Tuple[Set[str], int, int, int, Set[str]]:
        """Analyze file content using VB6Parser with regex fallback"""
        try:
            # Use the sophisticated parser
            parsed_file = self.parser.parse_file(file_path)
            if parsed_file:
                dependencies = parsed_file.dependencies
                external_deps = parsed_file.external_references
                complexity = len(parsed_file.methods) + 1  # Base + methods count
                functions_count = len([m for m in parsed_file.methods if m.method_type in ['Function', 'Sub']])
                classes_count = 1 if parsed_file.file_type == 'class' else 0
                
                return dependencies, complexity, functions_count, classes_count, external_deps
        except Exception as e:
            self.logger.warning(f"Parser failed for {file_path}, using fallback: {e}")
        
        # Fallback to regex approach
        return self._analyze_with_regex(content)
    
    def _analyze_with_regex(self, content: str) -> Tuple[Set[str], int, int, int, Set[str]]:
        """Fallback regex-based analysis for dependencies, complexity, functions, and external deps"""
        dependencies = set()
        external_deps = set()
        complexity = 1  # Base complexity
        functions_count = 0
        classes_count = 0
        
        # Count decision points for complexity
        decision_patterns = [
            r'\bIf\b',
            r'\bElseIf\b', 
            r'\bFor\b',
            r'\bWhile\b',
            r'\bDo\b',
            r'\bSelect\s+Case\b',
            r'\bCase\b',
            r'\bOn\s+Error\b'
        ]
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            complexity += len(matches)
        
        # Count functions and subs
        func_pattern = re.compile(r'^\s*(Public|Private|Friend)?\s*(Sub|Function)\s+\w+', re.MULTILINE | re.IGNORECASE)
        functions_count = len(func_pattern.findall(content))
        
        # Count classes
        class_pattern = re.compile(r'^\s*(Public|Private|Friend)?\s*(Class)\s+\w+', re.MULTILINE | re.IGNORECASE)
        classes_count = len(class_pattern.findall(content))
        
        # Look for references to other modules/classes
        patterns = [
            re.compile(r'New\s+(\w+)', re.IGNORECASE),  # Object instantiation
            re.compile(r'(\w+)\.', re.MULTILINE),        # Method calls
            re.compile(r'As\s+(\w+)', re.IGNORECASE),    # Type declarations
            re.compile(r'Dim\s+\w+\s+As\s+(\w+)', re.IGNORECASE)  # Variable declarations
        ]
        
        for pattern in patterns:
            matches = pattern.findall(content)
            dependencies.update(matches)
        
        # Filter out built-in VB6 types
        builtin_types = {'String', 'Integer', 'Long', 'Double', 'Single', 'Boolean', 
                        'Variant', 'Object', 'Date', 'Currency', 'Byte'}
        dependencies = dependencies - builtin_types
        
        # Look for external dependencies (COM objects, DLLs)
        external_patterns = [
            re.compile(r'CreateObject\("([^"]+)"\)', re.IGNORECASE),
            re.compile(r'GetObject\("([^"]+)"\)', re.IGNORECASE),
            re.compile(r'Declare\s+(?:Function|Sub)\s+\w+\s+Lib\s+"([^"]+)"', re.IGNORECASE)
        ]
        
        for pattern in external_patterns:
            matches = pattern.findall(content)
            external_deps.update(matches)
        
        return dependencies, complexity, functions_count, classes_count, external_deps
    
    def _determine_translation_order(self, project: VB6Project) -> List[str]:
        """Order files by complexity (simple to complex)"""
        return sorted(project.files.keys(), 
                      key=lambda x: project.files[x].complexity_score)
    
    def get_analysis_summary(self, projects: List[VB6Project]) -> Dict[str, Any]:
        """Generate a summary of the analysis results"""
        total_files = sum(len(p.files) for p in projects)
        total_loc = sum(p.get_total_loc() for p in projects)
        total_complexity = sum(p.get_total_complexity() for p in projects)
        
        file_types = defaultdict(int)
        all_external_deps = set()
        
        for project in projects:
            all_external_deps.update(project.external_dependencies)
            for file in project.files.values():
                file_types[file.file_type] += 1
                all_external_deps.update(file.external_dependencies)
        
        return {
            'projects_count': len(projects),
            'total_files': total_files,
            'total_lines_of_code': total_loc,
            'total_complexity': total_complexity,
            'average_complexity': total_complexity / total_files if total_files > 0 else 0,
            'file_types': dict(file_types),
            'external_dependencies': sorted(list(all_external_deps)),
            'projects': [
                {
                    'name': p.name,
                    'files_count': len(p.files),
                    'lines_of_code': p.get_total_loc(),
                    'complexity': p.get_total_complexity(),
                    'translation_order': p.translation_order,
                    'external_dependencies': sorted(list(p.external_dependencies))
                }
                for p in projects
            ]
        }


def main():
    setup_logging(level=logging.INFO, task_name="analysis")
    
    if len(sys.argv) != 2:
        print("Usage: python analyzer.py <directory_path>")
        sys.exit(1)
    
    directory_path = sys.argv[1]
    analyzer = VB6Analyzer()
    
    try:
        projects = analyzer.analyze_directory(directory_path)
        summary = analyzer.get_analysis_summary(projects)
        
        print(f"\n=== VB6 Analysis Summary ===")
        print(f"Projects found: {summary['projects_count']}")
        print(f"Total files: {summary['total_files']}")
        print(f"Total lines of code: {summary['total_lines_of_code']}")
        print(f"Total complexity: {summary['total_complexity']}")
        print(f"Average complexity: {summary['average_complexity']:.2f}")
        
        print(f"\nFile types:")
        for file_type, count in summary['file_types'].items():
            print(f"  {file_type}: {count}")
        
        print(f"\nExternal dependencies:")
        for dep in summary['external_dependencies']:
            print(f"  {dep}")
        
        for project_info in summary['projects']:
            print(f"\n--- Project: {project_info['name']} ---")
            print(f"Files: {project_info['files_count']}")
            print(f"Lines of code: {project_info['lines_of_code']}")
            print(f"Complexity: {project_info['complexity']}")
            print(f"Translation order: {', '.join(project_info['translation_order'])}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
