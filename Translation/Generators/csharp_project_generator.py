"""
C# Project Generator - Individual Project Creation

This module handles the creation of individual C# projects (.csproj files) from translated VB6 code.
It organizes translated code into appropriate folder structures, manages NuGet package references,
and handles complex code organization tasks.

Key responsibilities:
- Generate .csproj files with appropriate settings
- Organize translated files into logical folder structures
- Manage NuGet package dependencies
- Handle different project types (WinForms, Console, Class Library)
- Create namespace organization
- Generate project-specific configuration
"""

import logging
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))


class ProjectType(Enum):
    """C# project types"""
    WINFORMS_APP = "WinExe"
    CONSOLE_APP = "Exe"
    CLASS_LIBRARY = "Library"
    WPF_APP = "WinExe"
    WEB_APP = "Web"


class TargetFramework(Enum):
    """Target .NET frameworks"""
    NET8_WINDOWS = "net8.0-windows"
    NET8 = "net8.0"
    NET_FRAMEWORK_48 = "net48"
    NET_STANDARD_21 = "netstandard2.1"


@dataclass
class NuGetPackage:
    """Represents a NuGet package reference"""
    name: str
    version: str
    include_assets: Optional[str] = None
    private_assets: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class ProjectReference:
    """Represents a project reference"""
    path: str
    name: str
    project_guid: Optional[str] = None


@dataclass
class FileItem:
    """Represents a file in the project"""
    path: Path
    item_type: str  # Compile, Content, EmbeddedResource, None, etc.
    dependent_upon: Optional[str] = None  # For designer files
    sub_type: Optional[str] = None  # Form, UserControl, Component, etc.
    copy_to_output: Optional[str] = None  # Always, PreserveNewest, Never


@dataclass
class FolderStructure:
    """Represents the project folder organization"""
    forms_folder: str = "Forms"
    business_logic_folder: str = "BusinessLogic"
    data_access_folder: str = "DataAccess"
    models_folder: str = "Models"
    services_folder: str = "Services"
    utilities_folder: str = "Utilities"
    resources_folder: str = "Resources"
    config_folder: str = "Configuration"


@dataclass
class ProjectSettings:
    """C# project configuration settings"""
    project_type: ProjectType
    target_framework: TargetFramework
    use_windows_forms: bool = False
    use_wpf: bool = False
    nullable_enabled: bool = True
    implicit_usings: bool = True
    treat_warnings_as_errors: bool = False
    warning_level: int = 4
    assembly_title: Optional[str] = None
    assembly_description: Optional[str] = None
    assembly_company: Optional[str] = None
    assembly_product: Optional[str] = None
    assembly_version: str = "1.0.0.0"
    file_version: str = "1.0.0.0"


class CSharpProjectGenerator:
    """
    Generates C# project files and organizes translated VB6 code.
    
    This is the most complex generator as it handles:
    - Project file structure and organization
    - NuGet package management
    - Namespace organization
    - File categorization and dependencies
    """
    
    def __init__(self, project_name: str, output_path: Path):
        self.logger = logging.getLogger(__name__)
        self.project_name = project_name
        self.output_path = Path(output_path)
        self.project_guid = str(uuid.uuid4()).upper()
        
        # Initialize collections
        self.files: List[FileItem] = []
        self.nuget_packages: List[NuGetPackage] = []
        self.project_references: List[ProjectReference] = []
        self.using_statements: Set[str] = set()
        
        # Default settings
        self.settings = ProjectSettings(
            project_type=ProjectType.WINFORMS_APP,
            target_framework=TargetFramework.NET8_WINDOWS,
            use_windows_forms=True
        )
        
        self.folder_structure = FolderStructure()
        
        # Default NuGet packages for VB6 translations
        self._add_default_packages()
    
    def configure_project(self, project_type: ProjectType, has_forms: bool = False, 
                         has_data_access: bool = False, has_com_interop: bool = False) -> None:
        """Configure project based on translated VB6 components"""
        
        self.settings.project_type = project_type
        
        # Configure based on components
        if has_forms:
            self.settings.use_windows_forms = True
            self.settings.target_framework = TargetFramework.NET8_WINDOWS
            self._add_forms_packages()
        
        if has_data_access:
            self._add_data_access_packages()
        
        if has_com_interop:
            self._add_com_interop_packages()
        
        self.logger.info(f"Configured project: {project_type.value}, Forms: {has_forms}, "
                        f"Data: {has_data_access}, COM: {has_com_interop}")
    
    def add_translated_file(self, file_path: Path, original_vb6_type: str, 
                           namespace: str = None, has_designer: bool = False) -> None:
        """Add a translated file to the project with appropriate organization"""
        
        # Determine target folder and item type based on VB6 file type
        target_folder, item_type, sub_type = self._determine_file_organization(original_vb6_type)
        
        # Create organized path
        if target_folder:
            organized_path = Path(target_folder) / file_path.name
        else:
            organized_path = file_path
        
        # Add main file
        file_item = FileItem(
            path=organized_path,
            item_type=item_type,
            sub_type=sub_type
        )
        self.files.append(file_item)
        
        # Add designer file if exists
        if has_designer:
            designer_path = organized_path.with_suffix('.Designer.cs')
            designer_item = FileItem(
                path=designer_path,
                item_type="Compile",
                dependent_upon=organized_path.name
            )
            self.files.append(designer_item)
        
        # Add namespace to using statements
        if namespace:
            self.using_statements.add(namespace)
        
        self.logger.debug(f"Added file: {organized_path} (type: {original_vb6_type})")
    
    def add_nuget_package(self, package: NuGetPackage) -> None:
        """Add a NuGet package reference"""
        
        # Avoid duplicates
        if not any(pkg.name == package.name for pkg in self.nuget_packages):
            self.nuget_packages.append(package)
            self.logger.debug(f"Added NuGet package: {package.name} v{package.version}")
    
    def add_project_reference(self, reference: ProjectReference) -> None:
        """Add a project reference"""
        
        # Avoid duplicates
        if not any(ref.path == reference.path for ref in self.project_references):
            self.project_references.append(reference)
            self.logger.debug(f"Added project reference: {reference.name}")
    
    def organize_files_by_namespace(self, namespace_mapping: Dict[str, str]) -> None:
        """Organize files into folders based on namespace mapping"""
        
        organized_files = []
        
        for file_item in self.files:
            # Find matching namespace
            target_namespace = None
            for pattern, namespace in namespace_mapping.items():
                if pattern in str(file_item.path):
                    target_namespace = namespace
                    break
            
            if target_namespace:
                # Create namespace-based folder structure
                namespace_parts = target_namespace.split('.')
                if len(namespace_parts) > 1:  # Skip root namespace
                    folder_path = Path(*namespace_parts[1:])  # Skip first part (usually project name)
                    new_path = folder_path / file_item.path.name
                    
                    organized_files.append(FileItem(
                        path=new_path,
                        item_type=file_item.item_type,
                        dependent_upon=file_item.dependent_upon,
                        sub_type=file_item.sub_type,
                        copy_to_output=file_item.copy_to_output
                    ))
                else:
                    organized_files.append(file_item)
            else:
                organized_files.append(file_item)
        
        self.files = organized_files
        self.logger.info(f"Organized {len(self.files)} files by namespace")
    
    def generate_project_file(self) -> str:
        """Generate the .csproj file content"""
        
        # Create root project element
        project = ET.Element("Project", Sdk="Microsoft.NET.Sdk")
        
        # Property group - basic settings
        prop_group = ET.SubElement(project, "PropertyGroup")
        
        ET.SubElement(prop_group, "OutputType").text = self.settings.project_type.value
        ET.SubElement(prop_group, "TargetFramework").text = self.settings.target_framework.value
        
        if self.settings.use_windows_forms:
            ET.SubElement(prop_group, "UseWindowsForms").text = "true"
        
        if self.settings.use_wpf:
            ET.SubElement(prop_group, "UseWPF").text = "true"
        
        if self.settings.nullable_enabled:
            ET.SubElement(prop_group, "Nullable").text = "enable"
        
        if self.settings.implicit_usings:
            ET.SubElement(prop_group, "ImplicitUsings").text = "enable"
        
        ET.SubElement(prop_group, "WarningLevel").text = str(self.settings.warning_level)
        
        if self.settings.treat_warnings_as_errors:
            ET.SubElement(prop_group, "TreatWarningsAsErrors").text = "true"
        
        # Assembly information
        if self.settings.assembly_title:
            ET.SubElement(prop_group, "AssemblyTitle").text = self.settings.assembly_title
        if self.settings.assembly_description:
            ET.SubElement(prop_group, "AssemblyDescription").text = self.settings.assembly_description
        if self.settings.assembly_company:
            ET.SubElement(prop_group, "AssemblyCompany").text = self.settings.assembly_company
        if self.settings.assembly_product:
            ET.SubElement(prop_group, "AssemblyProduct").text = self.settings.assembly_product
        
        ET.SubElement(prop_group, "AssemblyVersion").text = self.settings.assembly_version
        ET.SubElement(prop_group, "FileVersion").text = self.settings.file_version
        
        # NuGet package references
        if self.nuget_packages:
            item_group = ET.SubElement(project, "ItemGroup")
            for package in self.nuget_packages:
                pkg_ref = ET.SubElement(item_group, "PackageReference", Include=package.name)
                pkg_ref.set("Version", package.version)
                
                if package.include_assets:
                    pkg_ref.set("IncludeAssets", package.include_assets)
                if package.private_assets:
                    pkg_ref.set("PrivateAssets", package.private_assets)
                if package.condition:
                    pkg_ref.set("Condition", package.condition)
        
        # Project references
        if self.project_references:
            item_group = ET.SubElement(project, "ItemGroup")
            for proj_ref in self.project_references:
                proj_elem = ET.SubElement(item_group, "ProjectReference", Include=proj_ref.path)
                if proj_ref.name:
                    ET.SubElement(proj_elem, "Name").text = proj_ref.name
        
        # File items (if not using default globbing)
        special_files = [f for f in self.files if f.dependent_upon or f.sub_type or f.copy_to_output]
        if special_files:
            item_group = ET.SubElement(project, "ItemGroup")
            for file_item in special_files:
                file_elem = ET.SubElement(item_group, file_item.item_type, Include=str(file_item.path))
                
                if file_item.dependent_upon:
                    ET.SubElement(file_elem, "DependentUpon").text = file_item.dependent_upon
                if file_item.sub_type:
                    ET.SubElement(file_elem, "SubType").text = file_item.sub_type
                if file_item.copy_to_output:
                    ET.SubElement(file_elem, "CopyToOutputDirectory").text = file_item.copy_to_output
        
        # Convert to pretty-printed XML
        xml_str = ET.tostring(project, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")[23:]  # Remove XML declaration
    
    def create_directory_structure(self) -> None:
        """Create the project directory structure"""
        
        # Create main project directory
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Create organized folders
        folders_to_create = set()
        
        for file_item in self.files:
            folder = file_item.path.parent
            if folder != Path('.'):
                folders_to_create.add(self.output_path / folder)
        
        # Add standard folders
        standard_folders = [
            self.folder_structure.forms_folder,
            self.folder_structure.business_logic_folder,
            self.folder_structure.data_access_folder,
            self.folder_structure.models_folder,
            self.folder_structure.services_folder,
            self.folder_structure.utilities_folder,
            self.folder_structure.resources_folder
        ]
        
        for folder_name in standard_folders:
            folders_to_create.add(self.output_path / folder_name)
        
        # Create all folders
        for folder_path in folders_to_create:
            folder_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Created {len(folders_to_create)} project directories")
    
    def save_project_file(self) -> Path:
        """Save the .csproj file to disk"""
        
        project_file_path = self.output_path / f"{self.project_name}.csproj"
        project_content = self.generate_project_file()
        
        with open(project_file_path, 'w', encoding='utf-8') as f:
            f.write(project_content)
        
        self.logger.info(f"Generated C# project file: {project_file_path}")
        return project_file_path
    
    def generate_global_usings_file(self) -> Optional[Path]:
        """Generate GlobalUsings.cs file for common using statements"""
        
        if not self.settings.implicit_usings and self.using_statements:
            global_usings_path = self.output_path / "GlobalUsings.cs"
            
            content = "// Global using statements for the project\n\n"
            for using_stmt in sorted(self.using_statements):
                content += f"global using {using_stmt};\n"
            
            with open(global_usings_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"Generated GlobalUsings.cs with {len(self.using_statements)} statements")
            return global_usings_path
        
        return None
    
    def _determine_file_organization(self, vb6_file_type: str) -> tuple[str, str, Optional[str]]:
        """Determine target folder, item type, and sub type for a VB6 file"""
        
        type_mappings = {
            'form': (self.folder_structure.forms_folder, "Compile", "Form"),
            'usercontrol': (self.folder_structure.forms_folder, "Compile", "UserControl"),
            'module': (self.folder_structure.business_logic_folder, "Compile", None),
            'class': (self.folder_structure.business_logic_folder, "Compile", None),
            'data_access': (self.folder_structure.data_access_folder, "Compile", None),
            'model': (self.folder_structure.models_folder, "Compile", None),
            'service': (self.folder_structure.services_folder, "Compile", None),
            'utility': (self.folder_structure.utilities_folder, "Compile", None),
            'config': (self.folder_structure.config_folder, "None", None),
            'resource': (self.folder_structure.resources_folder, "EmbeddedResource", None)
        }
        
        return type_mappings.get(vb6_file_type.lower(), ("", "Compile", None))
    
    def _add_default_packages(self) -> None:
        """Add default NuGet packages for VB6 translations"""
        
        default_packages = [
            NuGetPackage("Microsoft.Extensions.Logging", "8.0.0"),
            NuGetPackage("Microsoft.Extensions.Configuration", "8.0.0"),
            NuGetPackage("Microsoft.Extensions.Configuration.Json", "8.0.0"),
            NuGetPackage("Microsoft.Extensions.DependencyInjection", "8.0.0"),
        ]
        
        for package in default_packages:
            self.add_nuget_package(package)
    
    def _add_forms_packages(self) -> None:
        """Add Windows Forms specific packages"""
        
        forms_packages = [
            # Windows Forms packages are included with .NET 8 Windows target
        ]
        
        for package in forms_packages:
            self.add_nuget_package(package)
    
    def _add_data_access_packages(self) -> None:
        """Add data access packages for Entity Framework"""
        
        data_packages = [
            NuGetPackage("Microsoft.EntityFrameworkCore", "8.0.0"),
            NuGetPackage("Microsoft.EntityFrameworkCore.SqlServer", "8.0.0"),
            NuGetPackage("Microsoft.EntityFrameworkCore.Tools", "8.0.0"),
            NuGetPackage("Microsoft.EntityFrameworkCore.Design", "8.0.0"),
        ]
        
        for package in data_packages:
            self.add_nuget_package(package)
    
    def _add_com_interop_packages(self) -> None:
        """Add COM interop packages"""
        
        com_packages = [
            NuGetPackage("Microsoft.Office.Interop.Excel", "15.0.4795.1001", condition="'$(TargetFramework)' == 'net48'"),
            NuGetPackage("Microsoft.Office.Interop.Word", "15.0.4797.1004", condition="'$(TargetFramework)' == 'net48'"),
        ]
        
        for package in com_packages:
            self.add_nuget_package(package)
    
    def get_project_info(self) -> Dict[str, Any]:
        """Get project information for solution generation"""
        
        return {
            'name': self.project_name,
            'guid': self.project_guid,
            'path': f"{self.project_name}.csproj",
            'type': self.settings.project_type.value,
            'framework': self.settings.target_framework.value,
            'files_count': len(self.files),
            'packages_count': len(self.nuget_packages)
        }


def create_csharp_project(project_name: str, output_path: Path, translated_files: Dict[str, Any],
                         project_config: Dict[str, Any] = None) -> CSharpProjectGenerator:
    """
    Factory function to create a C# project from translated VB6 files
    
    Args:
        project_name: Name of the C# project
        output_path: Directory where project will be created
        translated_files: Dictionary of translated files with metadata
        project_config: Optional project configuration
        
    Returns:
        Configured CSharpProjectGenerator instance
    """
    
    generator = CSharpProjectGenerator(project_name, output_path)
    
    # Analyze translated files to determine project configuration
    has_forms = any('form' in file_info.get('type', '').lower() 
                   for file_info in translated_files.values())
    has_data_access = any('data' in file_info.get('type', '').lower() or 'database' in file_info.get('type', '').lower()
                         for file_info in translated_files.values())
    has_com_interop = any('com' in file_info.get('type', '').lower() or 'interop' in file_info.get('type', '').lower()
                         for file_info in translated_files.values())
    
    # Determine project type
    if has_forms:
        project_type = ProjectType.WINFORMS_APP
    else:
        project_type = ProjectType.CONSOLE_APP
    
    # Configure project
    generator.configure_project(project_type, has_forms, has_data_access, has_com_interop)
    
    # Add translated files
    for file_name, file_info in translated_files.items():
        file_path = Path(file_name)
        vb6_type = file_info.get('type', 'class')
        namespace = file_info.get('namespace')
        has_designer = file_info.get('has_designer', False)
        
        generator.add_translated_file(file_path, vb6_type, namespace, has_designer)
    
    # Apply custom configuration
    if project_config:
        if 'assembly_title' in project_config:
            generator.settings.assembly_title = project_config['assembly_title']
        if 'assembly_description' in project_config:
            generator.settings.assembly_description = project_config['assembly_description']
        if 'assembly_company' in project_config:
            generator.settings.assembly_company = project_config['assembly_company']
        if 'version' in project_config:
            generator.settings.assembly_version = project_config['version']
            generator.settings.file_version = project_config['version']
    
    return generator


def main():
    """Test the CSharpProjectGenerator"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Test project creation
    output_path = Path("./test_output")
    generator = CSharpProjectGenerator("TestProject", output_path)
    
    # Configure as WinForms project
    generator.configure_project(ProjectType.WINFORMS_APP, has_forms=True, has_data_access=True)
    
    # Add some test files
    generator.add_translated_file(Path("MainForm.cs"), "form", "TestProject.Forms", has_designer=True)
    generator.add_translated_file(Path("BusinessLogic.cs"), "class", "TestProject.BusinessLogic")
    generator.add_translated_file(Path("DataAccess.cs"), "data_access", "TestProject.DataAccess")
    
    # Create directory structure
    generator.create_directory_structure()
    
    # Generate project file
    project_file = generator.save_project_file()
    print(f"Generated project file: {project_file}")
    
    # Generate global usings
    global_usings = generator.generate_global_usings_file()
    if global_usings:
        print(f"Generated global usings: {global_usings}")
    
    # Show project info
    info = generator.get_project_info()
    print(f"Project info: {info}")


if __name__ == "__main__":
    main()
