import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
LOC_THRESHOLD = 500  # Maximum lines of code for treating whole file
BLOCK_THRESHOLD = 10  # Maximum number of blocks for treating whole file
MIN_LOC = 5  # Minimum lines of code for a block to be considered standalone
MAX_LOC = 200  # Maximum lines of code for a single chunk


@dataclass
class CodeBlock:
    """Represents a code block (function, subroutine, handler, etc.)"""
    name: str
    type: str  # 'function', 'subroutine', 'handler', 'procedure', etc.
    start_line: int
    end_line: int
    loc: int = 0
    text: str = ""


@dataclass
class TranslationTask:
    """Represents a translation task for a code chunk"""
    source_file: str
    code_text: str
    metadata: Dict = field(default_factory=dict)
    blocks_metadata: List[CodeBlock] = field(default_factory=list)


class DecompositionAgent:
    """Agent responsible for decomposing source files into manageable translation tasks."""
    
    def __init__(self):
        self.vb6_patterns = {
            'function': r'^\s*(Public|Private)?\s*Function\s+(\w+)\s*\([^)]*\)\s*(?:As\s+\w+)?',
            'subroutine': r'^\s*(Public|Private)?\s*Sub\s+(\w+)\s*\([^)]*\)',
            'property': r'^\s*(Public|Private)?\s*Property\s+(Get|Let|Set)\s+(\w+)',
            'event': r'^\s*Private\s+Sub\s+(\w+)_\w+\s*\([^)]*\)',
            'class': r'^\s*Class\s+(\w+)',
            'module': r'^\s*Module\s+(\w+)'
        }
        
        self.fortran_patterns = {
            'function': r'^\s*(?:RECURSIVE\s+)?(?:PURE\s+)?(?:ELEMENTAL\s+)?FUNCTION\s+(\w+)\s*\([^)]*\)',
            'subroutine': r'^\s*(?:RECURSIVE\s+)?(?:PURE\s+)?(?:ELEMENTAL\s+)?SUBROUTINE\s+(\w+)\s*\([^)]*\)',
            'program': r'^\s*PROGRAM\s+(\w+)',
            'module': r'^\s*MODULE\s+(\w+)'
        }
    
    def decompose_files(self, source_files: List[str]) -> List[TranslationTask]:
        """Main decomposition method that processes a list of source files."""
        tasks = []
        
        for file_path in source_files:
            try:
                logger.info(f"Decomposing file: {file_path}")
                file_tasks = self._decompose_single_file(file_path)
                tasks.extend(file_tasks)
            except Exception as e:
                logger.error(f"Error decomposing file {file_path}: {e}")
                continue
        
        return tasks
    
    def _decompose_single_file(self, file_path: str) -> List[TranslationTask]:
        """Decompose a single source file into translation tasks."""
        content = self._read_file(file_path)
        file_extension = Path(file_path).suffix.lower()
        
        # Parse source code to extract blocks
        blocks = self._parse_source(content, file_extension)
        
        # Compute metrics for each block
        self._compute_block_metrics(blocks, content)
        
        # Decide chunking strategy
        if self._should_treat_whole_file(blocks):
            # Emit one task for entire file
            task = self._make_task(file_path, content, blocks)
            return [task]
        else:
            # Group blocks into chunks
            groups = self._group_blocks_into_chunks(blocks)
            tasks = []
            for group in groups:
                chunk_text = self._extract_text(content, group)
                task = self._make_task(file_path, chunk_text, group)
                tasks.append(task)
            return tasks
    
    def _read_file(self, file_path: str) -> str:
        """Read file content with proper encoding handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            raise RuntimeError(f"Could not read file {file_path} with any supported encoding")
    
    def _parse_source(self, content: str, file_extension: str) -> List[CodeBlock]:
        """Parse source code to identify all blocks (functions, subs, handlers)."""
        blocks = []
        lines = content.split('\n')
        
        if file_extension in ['.vba', '.bas', '.cls', '.frm']:
            # VB6/VBA parsing
            blocks = self._parse_vb6_blocks(lines)
        elif file_extension in ['.f90', '.f95', '.f77', '.f']:
            # Fortran parsing
            blocks = self._parse_fortran_blocks(lines)
        else:
            # Generic parsing for other languages
            blocks = self._parse_generic_blocks(lines)
        
        return blocks
    
    def _parse_vb6_blocks(self, lines: List[str]) -> List[CodeBlock]:
        """Parse VB6/VBA code blocks."""
        blocks = []
        current_block = None
        block_stack = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for block starts
            for block_type, pattern in self.vb6_patterns.items():
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    if block_type == 'property':
                        name = match.group(3)  # Property name is in group 3
                    else:
                        name = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    
                    current_block = CodeBlock(
                        name=name,
                        type=block_type,
                        start_line=line_num,
                        end_line=line_num,
                        text=line
                    )
                    block_stack.append(current_block)
                    break
            
            # Check for block ends
            if current_block and self._is_vb6_block_end(line, current_block.type):
                current_block.end_line = line_num
                current_block.text = '\n'.join(lines[current_block.start_line-1:line_num])
                blocks.append(current_block)
                block_stack.pop()
                current_block = block_stack[-1] if block_stack else None
        
        return blocks
    
    def _parse_fortran_blocks(self, lines: List[str]) -> List[CodeBlock]:
        """Parse Fortran code blocks."""
        blocks = []
        current_block = None
        block_stack = []
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for block starts
            for block_type, pattern in self.fortran_patterns.items():
                if block_type.startswith('end_'):
                    continue
                    
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1)
                    current_block = CodeBlock(
                        name=name,
                        type=block_type,
                        start_line=line_num,
                        end_line=line_num,
                        text=line
                    )
                    block_stack.append(current_block)
                    break
            
            # Check for block ends
            if current_block and self._is_fortran_block_end(line, current_block.type):
                current_block.end_line = line_num
                current_block.text = '\n'.join(lines[current_block.start_line-1:line_num])
                blocks.append(current_block)
                block_stack.pop()
                current_block = block_stack[-1] if block_stack else None
        
        return blocks
    
    def _parse_generic_blocks(self, lines: List[str]) -> List[CodeBlock]:
        """Generic parsing for other languages."""
        blocks = []
        function_pattern = r'^\s*(?:def|function|sub|procedure|method)\s+(\w+)'
        
        for line_num, line in enumerate(lines, 1):
            match = re.match(function_pattern, line, re.IGNORECASE)
            if match:
                name = match.group(1)
                block = CodeBlock(
                    name=name,
                    type='function',
                    start_line=line_num,
                    end_line=line_num,
                    text=line
                )
                blocks.append(block)
        
        return blocks
    
    def _is_vb6_block_end(self, line: str, block_type: str) -> bool:
        """Check if line marks the end of a VB6 block."""
        if block_type == 'function':
            return re.match(r'^\s*End\s+Function', line, re.IGNORECASE)
        elif block_type == 'subroutine':
            return re.match(r'^\s*End\s+Sub', line, re.IGNORECASE)
        elif block_type == 'property':
            return re.match(r'^\s*End\s+Property', line, re.IGNORECASE)
        elif block_type == 'class':
            return re.match(r'^\s*End\s+Class', line, re.IGNORECASE)
        elif block_type == 'module':
            return re.match(r'^\s*End\s+Module', line, re.IGNORECASE)
        return False
    
    def _is_fortran_block_end(self, line: str, block_type: str) -> bool:
        """Check if line marks the end of a Fortran block."""
        end_patterns = {
            'function': r'^\s*END\s+FUNCTION',
            'subroutine': r'^\s*END\s+SUBROUTINE',
            'program': r'^\s*END\s+PROGRAM',
            'module': r'^\s*END\s+MODULE'
        }
        
        if block_type in end_patterns:
            return re.match(end_patterns[block_type], line, re.IGNORECASE)
        return False
    
    def _compute_block_metrics(self, blocks: List[CodeBlock], content: str):
        """Compute metrics for each block."""
        for block in blocks:
            # Calculate lines of code
            block.loc = block.end_line - block.start_line + 1
    
    def _should_treat_whole_file(self, blocks: List[CodeBlock]) -> bool:
        """Decide whether to treat the entire file as one task."""
        total_loc = sum(block.loc for block in blocks)
        
        if total_loc <= LOC_THRESHOLD and len(blocks) <= BLOCK_THRESHOLD:
            return True
        
        return False
    
    def _group_blocks_into_chunks(self, blocks: List[CodeBlock]) -> List[List[CodeBlock]]:
        """Group blocks into manageable chunks for translation."""
        # Start by placing each block in its own chunk
        initial_chunks = [[block] for block in blocks]
        
        # Merge very small blocks (<MIN_LOC) with their neighbor
        for i, chunk in enumerate(initial_chunks):
            if sum(block.loc for block in chunk) < MIN_LOC:
                target_chunk = self._find_most_linked_chunk(chunk, initial_chunks)
                if target_chunk and target_chunk != chunk:
                    # Merge chunk into target
                    target_chunk.extend(chunk)
                    initial_chunks[i] = []  # Mark for removal
        
        # Remove empty chunks
        initial_chunks = [chunk for chunk in initial_chunks if chunk]
        
        # Split overly large chunks
        final_chunks = []
        for chunk in initial_chunks:
            total_loc = sum(block.loc for block in chunk)
            if total_loc > MAX_LOC:
                # Split by retaining procedure boundaries
                split_groups = self._split_by_procedure(chunk)
                final_chunks.extend(split_groups)
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _find_most_linked_chunk(self, chunk: List[CodeBlock], all_chunks: List[List[CodeBlock]]) -> Optional[List[CodeBlock]]:
        """Find the chunk that has the most calls to/from the given chunk."""
        max_links = 0
        most_linked = None
        
        for other_chunk in all_chunks:
            if other_chunk == chunk:
                continue
            
            links = 0
            for block in chunk:
                for other_block in other_chunk:
                    if other_block.name in block.text or block.name in other_block.text:
                        links += 1
            
            if links > max_links:
                max_links = links
                most_linked = other_chunk
        
        return most_linked
    
    def _split_by_procedure(self, chunk: List[CodeBlock]) -> List[List[CodeBlock]]:
        """Split a large chunk by procedure boundaries."""
        # Simple strategy: split into groups of procedures
        max_procedures_per_chunk = 3
        split_chunks = []
        
        for i in range(0, len(chunk), max_procedures_per_chunk):
            split_chunks.append(chunk[i:i + max_procedures_per_chunk])
        
        return split_chunks
    
    def _extract_text(self, content: str, blocks: List[CodeBlock]) -> str:
        """Extract text for a group of blocks."""
        if not blocks:
            return ""
        
        lines = content.split('\n')
        start_line = min(block.start_line for block in blocks)
        end_line = max(block.end_line for block in blocks)
        
        return '\n'.join(lines[start_line-1:end_line])
    
    def _make_task(self, file_path: str, text: str, blocks: List[CodeBlock]) -> TranslationTask:
        """Create a TranslationTask from file content and blocks."""
        if not blocks:
            start_line, end_line = 1, len(text.split('\n'))
        else:
            start_line = min(block.start_line for block in blocks)
            end_line = max(block.end_line for block in blocks)
        
        metadata = {
            'line_range': (start_line, end_line),
            'loc': sum(block.loc for block in blocks),
            'block_names': [block.name for block in blocks],
            'block_types': [block.type for block in blocks],
            'file_extension': Path(file_path).suffix.lower()
        }
        
        return TranslationTask(
            source_file=file_path,
            code_text=text,
            metadata=metadata,
            blocks_metadata=blocks
        )


def decompose_file(file_path: str) -> List[TranslationTask]:
    """Convenience function to decompose a single file."""
    agent = DecompositionAgent()
    return agent.decompose_files([file_path])


def decompose_files(file_paths: List[str]) -> List[TranslationTask]:
    """Convenience function to decompose multiple files."""
    agent = DecompositionAgent()
    return agent.decompose_files(file_paths)
