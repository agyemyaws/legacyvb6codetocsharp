"""
Translation Utilities
Shared utility functions for the translation process.

This module contains utility functions that are used across multiple
translation agents and orchestrators to avoid circular dependencies.
"""

from pathlib import Path
from typing import Optional


def get_namespace_from_path(file_path: Path, project_root: Path) -> str:
    """Generate namespace from file path"""
    if not file_path:
        return project_root.name if project_root else "Translated"
    
    path_parts = list(file_path.parts)
    project_name = project_root.name
    dir_parts = path_parts[:-1]  # Remove filename
    
    try:
        project_index = -1
        for i, part in enumerate(dir_parts):
            if part.lower() == project_name.lower():
                project_index = i
                break
        
        if project_index == -1:
            return project_name
            
        # Get all subdirs after the project directory using actual directory names
        subdirs = dir_parts[project_index + 1:]
        # Use the actual project directory name from the path, not the project_root.name
        actual_project_name = dir_parts[project_index]
        return f"{actual_project_name}.{'.'.join(subdirs)}" if subdirs else actual_project_name
        
    except (ValueError, IndexError):
        return project_name


def generate_using_statements(vb6_file, project_files: dict, project_root: Path) -> str:
    """
    Generate project-specific using statements based on VB6 file dependencies
    
    This function only generates using statements for internal project dependencies
    (e.g., "using BMI.Models;" for CPerson dependency). Standard .NET using statements
    (System, System.Drawing, etc.) are handled by the prompt templates.
    
    Args:
        vb6_file: VB6File or VB6ParsedFile object with dependencies
        project_files: Dictionary of all project files {name: VB6File}
        project_root: Root directory of the VB6 project
        
    Returns:
        String containing project-specific using statements only (empty if no dependencies)
    """
    using_statements = set()
    
    if not hasattr(vb6_file, 'dependencies') or not vb6_file.dependencies:
        return ""  # Return empty string if no dependencies
    
    # Get file path - handle both VB6File and VB6ParsedFile
    file_path = getattr(vb6_file, 'file_path', None) or getattr(vb6_file, 'path', None)
    if not file_path:
        return ""  # Return empty string if no file path
        
    current_namespace = get_namespace_from_path(file_path, project_root)
    
    # Add using statements for each dependency
    for dependency in vb6_file.dependencies:
        if dependency in project_files:
            dependent_file = project_files[dependency]
            # Get path from dependent file - handle both VB6File and VB6ParsedFile
            dependent_path = getattr(dependent_file, 'path', None) or getattr(dependent_file, 'file_path', None)
            if dependent_path:
                dependent_namespace = get_namespace_from_path(dependent_path, project_root)
                
                # Only add if it's a different namespace than the current file
                if dependent_namespace != current_namespace:
                    using_statements.add(f"using {dependent_namespace};")
    
    # Sort using statements for consistency and return only project dependencies
    if using_statements:
        sorted_statements = sorted(using_statements)
        return "\n".join(sorted_statements)
    else:
        return ""  # Return empty string if no project dependencies


def sanitize_csharp_name(name: str) -> str:
    """
    Sanitize VB6 names for C# compatibility
    
    Args:
        name: The name to sanitize
        
    Returns:
        A C#-compatible name in PascalCase
    """
    import re
    
    # Remove invalid characters and handle keywords
    sanitized = re.sub(r'[^\w]', '_', name)
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    
    # Ensure PascalCase for class names
    if sanitized:
        sanitized = sanitized[0].upper() + sanitized[1:] if len(sanitized) > 1 else sanitized.upper()
    
    return sanitized if sanitized else "DefaultName"


def clean_llm_response(response_content: str) -> str:
    """
    Clean up LLM response content by removing markdown blocks and extra whitespace
    
    Args:
        response_content: Raw LLM response content
        
    Returns:
        Cleaned response content
    """
    import re
    
    # Remove markdown code blocks if present
    cleaned = re.sub(r'```(?:csharp|c#|cs)?\n?', '', response_content)
    cleaned = re.sub(r'```\n?$', '', cleaned, flags=re.MULTILINE)
    
    # Remove any leading/trailing whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def indent_code(code: str, levels: int) -> str:
    """
    Indent code by specified levels (4 spaces per level)
    
    Args:
        code: The code to indent
        levels: Number of indentation levels
        
    Returns:
        Indented code
    """
    indent = '    ' * levels
    return '\n'.join(f"{indent}{line}" if line.strip() else line for line in code.split('\n'))
