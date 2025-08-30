"""
VB6 Parser Utilities
Provides parsing functionality for VB6 files (forms, modules, classes).
"""

import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
import logging


@dataclass
class VB6Control:
    """Represents a VB6 control"""
    name: str
    control_type: str
    properties: Dict[str, str] = field(default_factory=dict)
    events: List[str] = field(default_factory=list)


@dataclass
class VB6Method:
    """Represents a VB6 method (Sub/Function/Property)"""
    name: str
    method_type: str  # 'Sub', 'Function', 'Property'
    visibility: str   # 'Public', 'Private', 'Friend'
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    body: str = ""
    line_start: int = 0
    line_end: int = 0


@dataclass
class VB6Variable:
    """Represents a VB6 variable declaration"""
    name: str
    var_type: str
    scope: str  # 'Public', 'Private', 'Dim'
    is_array: bool = False
    default_value: Optional[str] = None


@dataclass
class VB6ParsedFile:
    """Represents a parsed VB6 file"""
    file_path: Path
    file_type: str
    name: str
    variables: List[VB6Variable] = field(default_factory=list)
    methods: List[VB6Method] = field(default_factory=list)
    controls: List[VB6Control] = field(default_factory=list)
    dependencies: Set[str] = field(default_factory=set)
    external_references: Set[str] = field(default_factory=set)
    imports: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    complexity_score: int = 0


class VB6Parser:
    """Parser for VB6 files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # VB6 keywords and patterns
        self.vb6_keywords = {
            'visibility': ['Public', 'Private', 'Friend'],
            'method_types': ['Sub', 'Function', 'Property'],
            'variable_types': ['String', 'Integer', 'Long', 'Double', 'Single', 
                             'Boolean', 'Variant', 'Object', 'Date', 'Currency', 'Byte'],
            'control_types': ['TextBox', 'Label', 'CommandButton', 'ListBox', 'ComboBox',
                            'CheckBox', 'OptionButton', 'Frame', 'PictureBox', 'Image',
                            'Timer', 'CommonDialog', 'Data', 'Grid', 'MSFlexGrid']
        }
        
        # Compiled regex patterns
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for parsing"""
        return {
            # Method declarations
            'method_start': re.compile(
                r'^\s*(Public|Private|Friend)?\s*(Sub|Function|Property)\s+(\w+)\s*(\([^)]*\))?\s*(As\s+(\w+))?\s*$',
                re.IGNORECASE | re.MULTILINE
            ),
            'method_end': re.compile(
                r'^\s*End\s+(Sub|Function|Property)\s*$',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Variable declarations
            'variable_decl': re.compile(
                r'^\s*(Public|Private|Dim|Static)\s+(\w+)(?:\([^)]*\))?\s+As\s+(\w+)(?:\s*=\s*(.+))?\s*$',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Control declarations (in forms)
            'control_begin': re.compile(
                r'Begin\s+VB\.(\w+)\s+(\w+)',
                re.IGNORECASE
            ),
            'control_end': re.compile(
                r'End\s*$',
                re.IGNORECASE
            ),
            
            # Properties
            'property': re.compile(
                r'^\s*(\w+)\s*=\s*(.+)\s*$',
                re.MULTILINE
            ),
            
            # Attributes
            'attribute': re.compile(
                r'^Attribute\s+(\w+)\s*=\s*(.+)\s*$',
                re.IGNORECASE | re.MULTILINE
            ),
            
            # Dependencies and references
            'new_object': re.compile(
                r'New\s+(\w+)',
                re.IGNORECASE
            ),
            'set_object': re.compile(
                r'Set\s+\w+\s*=\s*(?:New\s+)?(\w+)',
                re.IGNORECASE
            ),
            'create_object': re.compile(
                r'CreateObject\s*\(\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            ),
            'get_object': re.compile(
                r'GetObject\s*\(\s*["\']([^"\']+)["\']',
                re.IGNORECASE
            ),
            
            # External library declarations
            'declare_statement': re.compile(
                r'Declare\s+(Function|Sub)\s+(\w+)\s+Lib\s+["\']([^"\']+)["\']',
                re.IGNORECASE
            ),
            
            # Comments
            'comment': re.compile(r"^\s*'.*$", re.MULTILINE),
            'rem_comment': re.compile(r"^\s*REM\s+.*$", re.IGNORECASE | re.MULTILINE)
        }
    
    def parse_file(self, file_path: Path) -> Optional[VB6ParsedFile]:
        """
        Parse a VB6 file and extract its structure
        
        Args:
            file_path: Path to the VB6 file
            
        Returns:
            VB6ParsedFile object or None if parsing fails
        """
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return None
        
        try:
            # Determine file type
            file_type = self._get_file_type(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
            
            # Create parsed file object
            parsed_file = VB6ParsedFile(
                file_path=file_path,
                file_type=file_type,
                name=file_path.stem
            )
            
            # Parse based on file type
            if file_type == 'form':
                self._parse_form(parsed_file, content)
            elif file_type == 'class':
                self._parse_class(parsed_file, content)
            elif file_type == 'module':
                self._parse_module(parsed_file, content)
            elif file_type == 'project':
                self._parse_project(parsed_file, content)
            
            # Extract common elements
            self._extract_attributes(parsed_file, content)
            self._extract_dependencies(parsed_file, content)
            self._extract_external_references(parsed_file, content)
            
            # Calculate complexity
            parsed_file.complexity_score = self._calculate_complexity(parsed_file)
            
            return parsed_file
            
        except Exception as e:
            self.logger.error(f"Error parsing file {file_path}: {e}")
            return None
    
    def _get_file_type(self, file_path: Path) -> str:
        """Determine VB6 file type from extension"""
        extension = file_path.suffix.lower()
        type_mapping = {
            '.vbp': 'project',
            '.frm': 'form',
            '.cls': 'class',
            '.bas': 'module',
            '.ctl': 'control',
            '.pag': 'property_page'
        }
        return type_mapping.get(extension, 'unknown')
    
    def _parse_form(self, parsed_file: VB6ParsedFile, content: str):
        """Parse VB6 form file"""
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Parse form header
            if line.startswith('VERSION'):
                parsed_file.attributes['version'] = line.split()[1]
            elif line.startswith('Begin VB.Form'):
                # Extract form name
                parts = line.split()
                if len(parts) > 2:
                    parsed_file.name = parts[2]
            
            # Parse controls
            elif line.startswith('Begin VB.'):
                control, end_line = self._parse_control(lines, i)
                if control:
                    parsed_file.controls.append(control)
                i = end_line
            
            # Parse code section (after form definition)
            elif line.startswith('Attribute VB_Name'):
                # Start of code section
                code_start = i
                code_content = '\n'.join(lines[code_start:])
                self._parse_code_section(parsed_file, code_content)
                break
            
            i += 1
    
    def _parse_class(self, parsed_file: VB6ParsedFile, content: str):
        """Parse VB6 class file"""
        # Class files are mostly code with some attributes at the top
        self._parse_code_section(parsed_file, content)
    
    def _parse_module(self, parsed_file: VB6ParsedFile, content: str):
        """Parse VB6 module file"""
        # Module files are mostly code
        self._parse_code_section(parsed_file, content)
    
    def _parse_project(self, parsed_file: VB6ParsedFile, content: str):
        """Parse VB6 project file"""
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('Name='):
                parsed_file.name = line.split('=', 1)[1].strip('"')
            elif line.startswith('Reference='):
                parsed_file.imports.append(line)
            elif line.startswith('Object='):
                parsed_file.imports.append(line)
    
    def _parse_control(self, lines: List[str], start_index: int) -> Tuple[Optional[VB6Control], int]:
        """Parse a control definition from form file"""
        start_line = lines[start_index].strip()
        
        # Extract control type and name
        match = self.patterns['control_begin'].match(start_line)
        if not match:
            return None, start_index + 1
        
        control_type = match.group(1)
        control_name = match.group(2)
        
        control = VB6Control(name=control_name, control_type=control_type)
        
        # Parse control properties
        i = start_index + 1
        while i < len(lines):
            line = lines[i].strip()
            
            if self.patterns['control_end'].match(line):
                break
            elif line.startswith('Begin VB.'):
                # Nested control
                nested_control, end_line = self._parse_control(lines, i)
                i = end_line
                continue
            else:
                # Property line
                prop_match = self.patterns['property'].match(line)
                if prop_match:
                    prop_name = prop_match.group(1)
                    prop_value = prop_match.group(2).strip('"')
                    control.properties[prop_name] = prop_value
            
            i += 1
        
        return control, i + 1
    
    def _parse_code_section(self, parsed_file: VB6ParsedFile, content: str):
        """Parse the code section of a VB6 file"""
        # Extract variables
        self._extract_variables(parsed_file, content)
        
        # Extract methods
        self._extract_methods(parsed_file, content)
    
    def _extract_variables(self, parsed_file: VB6ParsedFile, content: str):
        """Extract variable declarations"""
        matches = self.patterns['variable_decl'].findall(content)
        
        for match in matches:
            scope, name, var_type, default_value = match
            
            variable = VB6Variable(
                name=name,
                var_type=var_type,
                scope=scope,
                is_array='(' in name,  # Simple array detection
                default_value=default_value if default_value else None
            )
            
            parsed_file.variables.append(variable)
    
    def _extract_methods(self, parsed_file: VB6ParsedFile, content: str):
        """Extract method definitions"""
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for method start
            match = self.patterns['method_start'].match(line)
            if match:
                visibility = match.group(1) or 'Public'
                method_type = match.group(2)
                method_name = match.group(3)
                parameters = match.group(4) or '()'
                return_type = match.group(6) if match.group(5) else None
                
                # Find method end
                method_body_lines = []
                j = i + 1
                while j < len(lines):
                    if self.patterns['method_end'].match(lines[j]):
                        break
                    method_body_lines.append(lines[j])
                    j += 1
                
                method = VB6Method(
                    name=method_name,
                    method_type=method_type,
                    visibility=visibility,
                    parameters=self._parse_parameters(parameters),
                    return_type=return_type,
                    body='\n'.join(method_body_lines),
                    line_start=i + 1,
                    line_end=j + 1
                )
                
                parsed_file.methods.append(method)
                i = j
            
            i += 1
    
    def _parse_parameters(self, param_string: str) -> List[str]:
        """Parse method parameters"""
        if not param_string or param_string == '()':
            return []
        
        # Remove parentheses and split by comma
        params = param_string.strip('()').split(',')
        return [param.strip() for param in params if param.strip()]
    
    def _extract_attributes(self, parsed_file: VB6ParsedFile, content: str):
        """Extract VB6 attributes"""
        matches = self.patterns['attribute'].findall(content)
        
        for match in matches:
            attr_name, attr_value = match
            parsed_file.attributes[attr_name] = attr_value.strip('"')
    
    def _extract_dependencies(self, parsed_file: VB6ParsedFile, content: str):
        """Extract internal dependencies (other VB6 modules/classes)"""
        dependencies = set()
        
        # New object instantiation
        matches = self.patterns['new_object'].findall(content)
        dependencies.update(matches)
        
        # Set statements with object creation
        matches = self.patterns['set_object'].findall(content)
        dependencies.update(matches)
        
        # Filter out built-in types
        builtin_types = set(self.vb6_keywords['variable_types'])
        builtin_types.update(['Form', 'Control', 'Collection', 'Err', 'App'])
        
        parsed_file.dependencies = dependencies - builtin_types
    
    def _extract_external_references(self, parsed_file: VB6ParsedFile, content: str):
        """Extract external references (COM objects, DLLs)"""
        external_refs = set()
        
        # COM object creation
        matches = self.patterns['create_object'].findall(content)
        external_refs.update(matches)
        
        # GetObject calls
        matches = self.patterns['get_object'].findall(content)
        external_refs.update(matches)
        
        # DLL declarations
        matches = self.patterns['declare_statement'].findall(content)
        for match in matches:
            # match is (Function/Sub, function_name, library_name)
            external_refs.add(match[2])  # Library name
        
        parsed_file.external_references = external_refs
    
    def _calculate_complexity(self, parsed_file: VB6ParsedFile) -> int:
        """Calculate cyclomatic complexity from parsed VB6 methods"""
        total_complexity = 1  # Base complexity for the file
        
        for method in parsed_file.methods:
            method_complexity = 1  # Base complexity for each method
            
            # Count decision points in method body
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
                matches = re.findall(pattern, method.body, re.IGNORECASE)
                method_complexity += len(matches)
            
            total_complexity += method_complexity
        
        return total_complexity
    
    def get_file_summary(self, parsed_file: VB6ParsedFile) -> Dict[str, Any]:
        """Generate a summary of the parsed file"""
        return {
            'name': parsed_file.name,
            'type': parsed_file.file_type,
            'variables_count': len(parsed_file.variables),
            'methods_count': len(parsed_file.methods),
            'controls_count': len(parsed_file.controls),
            'complexity_score': parsed_file.complexity_score,
            'dependencies': list(parsed_file.dependencies),
            'external_references': list(parsed_file.external_references),
            'attributes': parsed_file.attributes,
            'methods': [
                {
                    'name': method.name,
                    'type': method.method_type,
                    'visibility': method.visibility,
                    'parameters': method.parameters,
                    'return_type': method.return_type
                }
                for method in parsed_file.methods
            ],
            'variables': [
                {
                    'name': var.name,
                    'type': var.var_type,
                    'scope': var.scope,
                    'is_array': var.is_array
                }
                for var in parsed_file.variables
            ]
        }


def main():
    """Test function for the parser"""
    import sys
    from pathlib import Path
    import json
    
    if len(sys.argv) != 2:
        print("Usage: python vb6_parser.py <file_path>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    parser = VB6Parser()
    
    parsed_file = parser.parse_file(file_path)
    if parsed_file:
        summary = parser.get_file_summary(parsed_file)
        print(json.dumps(summary, indent=2))
    else:
        print("Failed to parse file")


if __name__ == "__main__":
    main()
