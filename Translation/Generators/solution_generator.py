"""
Solution Generator - Multi-Project Orchestration

This module handles the creation of Visual Studio solution files (.sln) that can contain
multiple C# projects. It manages relationships between projects, handles project dependencies,
and creates the overall solution structure.

Key responsibilities:
- Generate .sln files with proper formatting
- Manage multiple project relationships
- Handle project dependencies and build order
- Create solution folders for organization
- Generate solution-level configuration
- Manage GUIDs for projects and solution
"""

import logging
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class ProjectTypeGuid(Enum):
    """Visual Studio project type GUIDs"""
    CSHARP_PROJECT = "{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}"
    SOLUTION_FOLDER = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"
    WEB_PROJECT = "{E24C65DC-7377-472B-9ABA-BC803B73C61A}"
    DATABASE_PROJECT = "{00D1A9C2-B5F0-4AF3-8072-F6C62B433612}"


class BuildConfiguration(Enum):
    """Build configurations"""
    DEBUG = "Debug"
    RELEASE = "Release"


class Platform(Enum):
    """Target platforms"""
    ANY_CPU = "Any CPU"
    X86 = "x86"
    X64 = "x64"


@dataclass
class SolutionProject:
    """Represents a project in the solution"""
    name: str
    path: Path
    project_guid: str
    project_type_guid: str = ProjectTypeGuid.CSHARP_PROJECT.value
    dependencies: List[str] = field(default_factory=list)  # List of project GUIDs
    solution_folder: Optional[str] = None
    
    def __post_init__(self):
        """Ensure path uses forward slashes for solution file"""
        self.path = Path(str(self.path).replace('\\', '/'))


@dataclass
class SolutionFolder:
    """Represents a solution folder for organization"""
    name: str
    guid: str
    projects: List[str] = field(default_factory=list)  # List of project GUIDs
    
    def __post_init__(self):
        """Generate GUID if not provided"""
        if not self.guid:
            self.guid = str(uuid.uuid4()).upper()


@dataclass
class SolutionConfiguration:
    """Represents solution build configuration"""
    name: str
    platform: str
    project_configurations: Dict[str, Dict[str, str]] = field(default_factory=dict)
    # project_guid -> {"ConfigurationName": "Debug", "PlatformName": "Any CPU", "Build": "true"}


class SolutionGenerator:
    """
    Generates Visual Studio solution files (.sln) for multiple C# projects.
    
    This is simpler than the project generator as it mostly deals with file templates
    and GUIDs, but it's crucial for organizing complex translations with multiple projects.
    """
    
    def __init__(self, solution_name: str, output_path: Path):
        self.logger = logging.getLogger(__name__)
        self.solution_name = solution_name
        self.output_path = Path(output_path)
        self.solution_guid = str(uuid.uuid4()).upper()
        
        # Collections
        self.projects: Dict[str, SolutionProject] = {}  # guid -> project
        self.solution_folders: Dict[str, SolutionFolder] = {}  # guid -> folder
        self.configurations: List[SolutionConfiguration] = []
        
        # Default configurations
        self._create_default_configurations()
        
        # Visual Studio version info
        self.vs_version = "17"
        self.vs_full_version = "17.0.31903.59"
        self.min_vs_version = "10.0.40219.1"
    
    def add_project(self, name: str, project_path: Path, project_guid: str = None,
                   project_type: str = None, solution_folder: str = None,
                   dependencies: List[str] = None) -> str:
        """
        Add a project to the solution
        
        Args:
            name: Project display name
            project_path: Path to .csproj file relative to solution
            project_guid: Project GUID (generated if not provided)
            project_type: Project type GUID (defaults to C# project)
            solution_folder: Name of solution folder to place project in
            dependencies: List of project GUIDs this project depends on
            
        Returns:
            Project GUID
        """
        
        if not project_guid:
            project_guid = str(uuid.uuid4()).upper()
        
        if not project_type:
            project_type = ProjectTypeGuid.CSHARP_PROJECT.value
        
        if not dependencies:
            dependencies = []
        
        project = SolutionProject(
            name=name,
            path=project_path,
            project_guid=project_guid,
            project_type_guid=project_type,
            dependencies=dependencies,
            solution_folder=solution_folder
        )
        
        self.projects[project_guid] = project
        
        # Add to solution folder if specified
        if solution_folder:
            self.add_to_solution_folder(solution_folder, project_guid)
        
        # Add project to all configurations
        for config in self.configurations:
            config.project_configurations[project_guid] = {
                "ConfigurationName": config.name,
                "PlatformName": config.platform,
                "Build": "true",
                "Deploy": "false"
            }
        
        self.logger.info(f"Added project: {name} ({project_guid})")
        return project_guid
    
    def add_solution_folder(self, folder_name: str, folder_guid: str = None) -> str:
        """
        Add a solution folder for organizing projects
        
        Args:
            folder_name: Display name of the folder
            folder_guid: Folder GUID (generated if not provided)
            
        Returns:
            Folder GUID
        """
        
        if not folder_guid:
            folder_guid = str(uuid.uuid4()).upper()
        
        if folder_guid not in self.solution_folders:
            folder = SolutionFolder(name=folder_name, guid=folder_guid)
            self.solution_folders[folder_guid] = folder
            self.logger.info(f"Added solution folder: {folder_name} ({folder_guid})")
        
        return folder_guid
    
    def add_to_solution_folder(self, folder_name: str, project_guid: str) -> None:
        """Add a project to a solution folder"""
        
        # Find or create the folder
        folder_guid = None
        for guid, folder in self.solution_folders.items():
            if folder.name == folder_name:
                folder_guid = guid
                break
        
        if not folder_guid:
            folder_guid = self.add_solution_folder(folder_name)
        
        # Add project to folder
        if project_guid not in self.solution_folders[folder_guid].projects:
            self.solution_folders[folder_guid].projects.append(project_guid)
    
    def add_project_dependency(self, dependent_project_guid: str, dependency_project_guid: str) -> None:
        """Add a dependency relationship between projects"""
        
        if dependent_project_guid in self.projects:
            if dependency_project_guid not in self.projects[dependent_project_guid].dependencies:
                self.projects[dependent_project_guid].dependencies.append(dependency_project_guid)
                self.logger.info(f"Added dependency: {dependent_project_guid} -> {dependency_project_guid}")
    
    def create_standard_folder_structure(self) -> None:
        """Create a standard solution folder structure"""
        
        standard_folders = [
            "Source Code",
            "Tests",
            "Documentation",
            "Configuration",
            "Resources"
        ]
        
        for folder_name in standard_folders:
            self.add_solution_folder(folder_name)
    
    def organize_projects_by_type(self) -> None:
        """Automatically organize projects into solution folders by type"""
        
        # Define folder mappings based on project names/paths
        folder_mappings = {
            "Forms": ["form", "ui", "winform", "wpf"],
            "Business Logic": ["business", "logic", "core", "domain"],
            "Data Access": ["data", "dal", "repository", "entity"],
            "Services": ["service", "api", "web"],
            "Utilities": ["util", "helper", "common", "shared"],
            "Tests": ["test", "spec", "unit", "integration"]
        }
        
        # Create folders
        for folder_name in folder_mappings.keys():
            self.add_solution_folder(folder_name)
        
        # Organize projects
        for project_guid, project in self.projects.items():
            project_name_lower = project.name.lower()
            project_path_lower = str(project.path).lower()
            
            # Find matching folder
            for folder_name, keywords in folder_mappings.items():
                if any(keyword in project_name_lower or keyword in project_path_lower 
                      for keyword in keywords):
                    self.add_to_solution_folder(folder_name, project_guid)
                    break
    
    def generate_solution_content(self) -> str:
        """Generate the complete .sln file content"""
        
        lines = []
        
        # Header
        lines.append("")
        lines.append(f"Microsoft Visual Studio Solution File, Format Version 12.00")
        lines.append(f"# Visual Studio Version {self.vs_version}")
        lines.append(f"VisualStudioVersion = {self.vs_full_version}")
        lines.append(f"MinimumVisualStudioVersion = {self.min_vs_version}")
        
        # Projects section
        for project_guid, project in self.projects.items():
            lines.append(f'Project("{project.project_type_guid}") = "{project.name}", "{project.path}", "{{{project_guid}}}"')
            
            # Project dependencies
            if project.dependencies:
                lines.append("\tProjectSection(ProjectDependencies) = postProject")
                for dep_guid in project.dependencies:
                    lines.append(f"\t\t{{{dep_guid}}} = {{{dep_guid}}}")
                lines.append("\tEndProjectSection")
            
            lines.append("EndProject")
        
        # Solution folders
        for folder_guid, folder in self.solution_folders.items():
            lines.append(f'Project("{ProjectTypeGuid.SOLUTION_FOLDER.value}") = "{folder.name}", "{folder.name}", "{{{folder_guid}}}"')
            lines.append("EndProject")
        
        # Global section
        lines.append("Global")
        
        # Solution configuration platforms
        if self.configurations:
            lines.append("\tGlobalSection(SolutionConfigurationPlatforms) = preSolution")
            for config in self.configurations:
                config_name = f"{config.name}|{config.platform}"
                lines.append(f"\t\t{config_name} = {config_name}")
            lines.append("\tEndGlobalSection")
            
            # Project configuration platforms
            lines.append("\tGlobalSection(ProjectConfigurationPlatforms) = postSolution")
            for config in self.configurations:
                config_name = f"{config.name}|{config.platform}"
                for project_guid, proj_config in config.project_configurations.items():
                    lines.append(f"\t\t{{{project_guid}}}.{config_name}.ActiveCfg = {config_name}")
                    if proj_config.get("Build", "false") == "true":
                        lines.append(f"\t\t{{{project_guid}}}.{config_name}.Build.0 = {config_name}")
                    if proj_config.get("Deploy", "false") == "true":
                        lines.append(f"\t\t{{{project_guid}}}.{config_name}.Deploy.0 = {config_name}")
            lines.append("\tEndGlobalSection")
        
        # Solution properties
        lines.append("\tGlobalSection(SolutionProperties) = preSolution")
        lines.append("\t\tHideSolutionNode = FALSE")
        lines.append("\tEndGlobalSection")
        
        # Nested projects (solution folders)
        if self.solution_folders and any(folder.projects for folder in self.solution_folders.values()):
            lines.append("\tGlobalSection(NestedProjects) = preSolution")
            for folder_guid, folder in self.solution_folders.items():
                for project_guid in folder.projects:
                    lines.append(f"\t\t{{{project_guid}}} = {{{folder_guid}}}")
            lines.append("\tEndGlobalSection")
        
        # Extensibility globals
        lines.append("\tGlobalSection(ExtensibilityGlobals) = postSolution")
        lines.append(f"\t\tSolutionGuid = {{{self.solution_guid}}}")
        lines.append("\tEndGlobalSection")
        
        lines.append("EndGlobal")
        
        return "\n".join(lines)
    
    def save_solution_file(self) -> Path:
        """Save the .sln file to disk"""
        
        solution_file_path = self.output_path / f"{self.solution_name}.sln"
        solution_content = self.generate_solution_content()
        
        # Ensure output directory exists
        solution_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(solution_file_path, 'w', encoding='utf-8') as f:
            f.write(solution_content)
        
        self.logger.info(f"Generated solution file: {solution_file_path}")
        return solution_file_path
    
    def _create_default_configurations(self) -> None:
        """Create default Debug and Release configurations"""
        
        debug_config = SolutionConfiguration(
            name=BuildConfiguration.DEBUG.value,
            platform=Platform.ANY_CPU.value
        )
        
        release_config = SolutionConfiguration(
            name=BuildConfiguration.RELEASE.value,
            platform=Platform.ANY_CPU.value
        )
        
        self.configurations = [debug_config, release_config]
    
    def get_solution_info(self) -> Dict[str, Any]:
        """Get solution information summary"""
        
        return {
            'name': self.solution_name,
            'guid': self.solution_guid,
            'projects_count': len(self.projects),
            'folders_count': len(self.solution_folders),
            'configurations_count': len(self.configurations),
            'projects': [
                {
                    'name': project.name,
                    'path': str(project.path),
                    'guid': project_guid,
                    'dependencies_count': len(project.dependencies)
                }
                for project_guid, project in self.projects.items()
            ]
        }


def create_solution_for_translated_project(solution_name: str, output_path: Path,
                                         projects_info: List[Dict[str, Any]],
                                         organize_by_type: bool = True) -> SolutionGenerator:
    """
    Factory function to create a solution from translated VB6 project information
    
    Args:
        solution_name: Name of the solution
        output_path: Directory where solution will be created
        projects_info: List of project information dictionaries
        organize_by_type: Whether to organize projects into solution folders
        
    Returns:
        Configured SolutionGenerator instance
    """
    
    generator = SolutionGenerator(solution_name, output_path)
    
    # Add all projects
    project_guids = {}
    for project_info in projects_info:
        project_name = project_info['name']
        project_path = Path(project_info['path'])
        project_guid = project_info.get('guid', str(uuid.uuid4()).upper())
        
        added_guid = generator.add_project(
            name=project_name,
            project_path=project_path,
            project_guid=project_guid
        )
        
        project_guids[project_name] = added_guid
    
    # Add dependencies if specified
    for project_info in projects_info:
        if 'dependencies' in project_info:
            project_name = project_info['name']
            project_guid = project_guids[project_name]
            
            for dep_name in project_info['dependencies']:
                if dep_name in project_guids:
                    generator.add_project_dependency(project_guid, project_guids[dep_name])
    
    # Organize projects if requested
    if organize_by_type:
        generator.organize_projects_by_type()
    
    return generator


def main():
    """Test the SolutionGenerator"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test solution creation
    output_path = Path("./test_output")
    generator = SolutionGenerator("TestSolution", output_path)
    
    # Add some test projects
    main_project_guid = generator.add_project(
        name="MainApplication",
        project_path=Path("MainApplication/MainApplication.csproj")
    )
    
    business_project_guid = generator.add_project(
        name="BusinessLogic",
        project_path=Path("BusinessLogic/BusinessLogic.csproj")
    )
    
    data_project_guid = generator.add_project(
        name="DataAccess",
        project_path=Path("DataAccess/DataAccess.csproj")
    )
    
    test_project_guid = generator.add_project(
        name="Tests",
        project_path=Path("Tests/Tests.csproj")
    )
    
    # Add dependencies
    generator.add_project_dependency(main_project_guid, business_project_guid)
    generator.add_project_dependency(main_project_guid, data_project_guid)
    generator.add_project_dependency(business_project_guid, data_project_guid)
    generator.add_project_dependency(test_project_guid, main_project_guid)
    
    # Organize projects
    generator.organize_projects_by_type()
    
    # Generate solution file
    solution_file = generator.save_solution_file()
    print(f"Generated solution file: {solution_file}")
    
    # Show solution info
    info = generator.get_solution_info()
    print(f"Solution info: {info}")


if __name__ == "__main__":
    main()
