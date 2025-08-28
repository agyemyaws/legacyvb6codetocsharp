import re
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AnonymizationMapping:
    """Data class to store anonymization mappings"""
    placeholder: str
    original: str
    category: str
    line_number: Optional[int] = None


class Anonymizer:
    def __init__(self, config_path: str):
        """Initialize anonymizer with config file"""
        self.config_path = config_path
        self.sensitive_patterns = self._load_config()
        self.forward_mapping: Dict[str, AnonymizationMapping] = {}
        self.reverse_mapping: Dict[str, str] = {}
        self.placeholder_counter = 0
        
    def _load_config(self) -> Dict[str, List[str]]:
        """Load sensitive patterns from configuration file"""
        if not os.path.exists(self.config_path):
            return {}
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config from {self.config_path}: {e}")
    
    def _generate_placeholder(self, category: str) -> str:
        """Generate a unique placeholder for the given category"""
        self.placeholder_counter += 1
        return f"__{category.upper()}_{self.placeholder_counter:04d}__"
    
    def _find_sensitive_patterns(self, code_text: str) -> List[Tuple[str, str, int]]:
        """Find all sensitive patterns in the code text"""
        matches = []
        lines = code_text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for category, patterns in self.sensitive_patterns.items():
                if category == "custom_patterns":
                    continue
                    
                for pattern in patterns:
                    regex_pattern = r'\b' + re.escape(pattern) + r'\b'
                    if re.search(regex_pattern, line, re.IGNORECASE):
                        matches.append((pattern, category, line_num))
        
        # Check for custom patterns if defined
        if "custom_patterns" in self.sensitive_patterns:
            for pattern in self.sensitive_patterns["custom_patterns"]:
                for match in re.finditer(pattern, code_text, re.IGNORECASE):
                    matches.append((match.group(), "custom", 0))
        
        return matches
    
    def anonymize(self, code_text: str) -> str:
        """Anonymize sensitive information in code"""
        if not self.sensitive_patterns:
            return code_text
        
        anonymized_text = code_text
        matches = self._find_sensitive_patterns(code_text)
        
        # Process matches and create mappings
        for matched_text, category, line_number in matches:
            if matched_text not in self.reverse_mapping:
                placeholder = self._generate_placeholder(category)
                
                mapping = AnonymizationMapping(
                    placeholder=placeholder,
                    original=matched_text,
                    category=category,
                    line_number=line_number
                )
                
                self.forward_mapping[placeholder] = mapping
                self.reverse_mapping[matched_text] = placeholder
        
        # Replace all sensitive patterns with placeholders
        for original, placeholder in self.reverse_mapping.items():
            pattern = r'\b' + re.escape(original) + r'\b'
            anonymized_text = re.sub(pattern, placeholder, anonymized_text, flags=re.IGNORECASE)
        
        return anonymized_text
    
    def de_anonymize(self, translated_text: str) -> str:
        """Restore original values from placeholders"""
        if not self.forward_mapping:
            return translated_text
        
        restored_text = translated_text
        for placeholder, mapping in self.forward_mapping.items():
            restored_text = restored_text.replace(placeholder, mapping.original)
        
        return restored_text
    
    def save_mapping(self, map_path: str):
        """Save the mapping to disk"""
        try:
            serializable_mappings = {}
            for placeholder, mapping in self.forward_mapping.items():
                serializable_mappings[placeholder] = asdict(mapping)
            
            with open(map_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_mappings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise RuntimeError(f"Failed to save mapping to {map_path}: {e}")
    
    def load_mapping(self, map_path: str):
        """Load a previously saved mapping"""
        try:
            with open(map_path, 'r', encoding='utf-8') as f:
                serializable_mappings = json.load(f)
            
            self.forward_mapping.clear()
            self.reverse_mapping.clear()
            
            for placeholder, mapping_dict in serializable_mappings.items():
                mapping = AnonymizationMapping(**mapping_dict)
                self.forward_mapping[placeholder] = mapping
                self.reverse_mapping[mapping.original] = placeholder
            
            # Update counter to avoid conflicts
            if self.forward_mapping:
                max_counter = max(
                    int(mapping.placeholder.split('_')[-1].rstrip('_'))
                    for mapping in self.forward_mapping.values()
                )
                self.placeholder_counter = max_counter
                
        except Exception as e:
            raise RuntimeError(f"Failed to load mapping from {map_path}: {e}")
    
    def clear_mappings(self):
        """Clear all current mappings"""
        self.forward_mapping.clear()
        self.reverse_mapping.clear()
        self.placeholder_counter = 0
