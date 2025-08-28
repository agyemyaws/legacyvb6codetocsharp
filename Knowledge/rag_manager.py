"""
RAG Manager - Retrieval-Augmented Generation for VB6 to C# Translation

This module manages a knowledge base of VB6 to C# translation patterns and provides
intelligent retrieval capabilities to enhance translation quality through examples.

Features:
- Pattern storage and categorization
- Similarity-based pattern retrieval
- Category-specific searches
- Embedding-based similarity matching
- Integration with translation agents
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import hashlib

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Optional imports for advanced embedding functionality
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None


@dataclass
class CodePattern:
    """Represents a VB6 to C# translation pattern"""
    id: str
    name: str
    description: str
    category: str
    vb6_code: str
    csharp_code: str
    tags: List[str] = field(default_factory=list)
    complexity: str = "medium"  # low, medium, high
    confidence: float = 1.0  # 0.0 to 1.0
    usage_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate ID if not provided"""
        if not self.id:
            # Generate hash-based ID from content
            content = f"{self.name}_{self.vb6_code}_{self.csharp_code}"
            self.id = hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass 
class PatternMatch:
    """Represents a pattern match with similarity score"""
    pattern: CodePattern
    similarity_score: float
    match_reason: str
    relevance_factors: List[str] = field(default_factory=list)


class RAGManager:
    """
    Manages retrieval-augmented generation for VB6 to C# translation.
    
    Provides intelligent pattern storage, retrieval, and similarity matching
    to enhance translation quality through relevant examples.
    """
    
    def __init__(self, knowledge_base_path: str = None):
        self.logger = logging.getLogger(__name__)
        
        # Initialize paths
        self.knowledge_base_path = Path(knowledge_base_path) if knowledge_base_path else Path(__file__).parent
        self.patterns_dir = self.knowledge_base_path / "VB6_to_CSharp_Equivalents"
        self.embeddings_cache_path = self.knowledge_base_path / "embeddings_cache.json"
        
        # Initialize storage
        self.patterns: Dict[str, CodePattern] = {}
        self.category_index: Dict[str, List[str]] = defaultdict(list)  # category -> pattern_ids
        self.tag_index: Dict[str, List[str]] = defaultdict(list)  # tag -> pattern_ids
        self.embeddings_cache: Dict[str, List[float]] = {}
        
        # Initialize embedding model if available
        self.embedding_model = None
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.info("Initialized sentence transformer for embeddings")
            except Exception as e:
                self.logger.warning(f"Failed to initialize embedding model: {e}")
        
        # Load existing patterns
        self._load_patterns()
        self._load_embeddings_cache()
    
    def store_pattern(self, pattern: CodePattern, category: str = None) -> None:
        """
        Store a code pattern in the knowledge base
        
        Args:
            pattern: CodePattern to store
            category: Optional category override
        """
        
        if category:
            pattern.category = category
        
        # Store pattern
        self.patterns[pattern.id] = pattern
        
        # Update indices
        self.category_index[pattern.category].append(pattern.id)
        for tag in pattern.tags:
            self.tag_index[tag].append(pattern.id)
        
        # Generate embedding if possible
        if self.embedding_model:
            try:
                # Combine VB6 and description for embedding
                text_for_embedding = f"{pattern.description} {pattern.vb6_code}"
                embedding = self.embedding_model.encode(text_for_embedding).tolist()
                self.embeddings_cache[pattern.id] = embedding
            except Exception as e:
                self.logger.warning(f"Failed to generate embedding for pattern {pattern.id}: {e}")
        
        self.logger.debug(f"Stored pattern: {pattern.name} ({pattern.id})")
    
    def retrieve_similar_patterns(self, query_code: str, top_k: int = 5, 
                                 category: str = None, min_similarity: float = 0.1) -> List[PatternMatch]:
        """
        Retrieve patterns similar to the query code
        
        Args:
            query_code: VB6 code to find patterns for
            top_k: Maximum number of patterns to return
            category: Optional category filter
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of PatternMatch objects sorted by similarity
        """
        
        matches = []
        
        # Filter patterns by category if specified
        candidate_patterns = []
        if category:
            pattern_ids = self.category_index.get(category, [])
            candidate_patterns = [self.patterns[pid] for pid in pattern_ids if pid in self.patterns]
        else:
            candidate_patterns = list(self.patterns.values())
        
        # Try embedding-based similarity first
        if self.embedding_model and self.embeddings_cache:
            try:
                query_embedding = self.embedding_model.encode(query_code)
                
                for pattern in candidate_patterns:
                    if pattern.id in self.embeddings_cache:
                        pattern_embedding = np.array(self.embeddings_cache[pattern.id])
                        similarity = self._cosine_similarity(query_embedding, pattern_embedding)
                        
                        if similarity >= min_similarity:
                            match = PatternMatch(
                                pattern=pattern,
                                similarity_score=similarity,
                                match_reason="embedding_similarity",
                                relevance_factors=["semantic_similarity"]
                            )
                            matches.append(match)
                            
            except Exception as e:
                self.logger.warning(f"Embedding-based similarity failed: {e}")
        
        # Fallback to text-based similarity
        if not matches:
            matches = self._text_based_similarity(query_code, candidate_patterns, min_similarity)
        
        # Sort by similarity score and return top_k
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
        return matches[:top_k]
    
    def search_by_category(self, category: str, query: str = None, limit: int = 10) -> List[CodePattern]:
        """
        Search patterns by category with optional query filtering
        
        Args:
            category: Pattern category to search
            query: Optional text query for filtering
            limit: Maximum number of results
            
        Returns:
            List of matching CodePattern objects
        """
        
        pattern_ids = self.category_index.get(category, [])
        patterns = [self.patterns[pid] for pid in pattern_ids if pid in self.patterns]
        
        if query:
            # Filter patterns by query text
            query_lower = query.lower()
            filtered_patterns = []
            
            for pattern in patterns:
                # Search in name, description, VB6 code, and tags
                searchable_text = f"{pattern.name} {pattern.description} {pattern.vb6_code} {' '.join(pattern.tags)}".lower()
                if query_lower in searchable_text:
                    filtered_patterns.append(pattern)
            
            patterns = filtered_patterns
        
        # Sort by usage count and confidence
        patterns.sort(key=lambda p: (p.usage_count, p.confidence), reverse=True)
        
        return patterns[:limit]
    
    def search_by_tags(self, tags: List[str], match_all: bool = False, limit: int = 10) -> List[CodePattern]:
        """
        Search patterns by tags
        
        Args:
            tags: List of tags to search for
            match_all: If True, pattern must have all tags; if False, any tag matches
            limit: Maximum number of results
            
        Returns:
            List of matching CodePattern objects
        """
        
        if match_all:
            # Pattern must have all tags
            pattern_ids = None
            for tag in tags:
                tag_pattern_ids = set(self.tag_index.get(tag, []))
                if pattern_ids is None:
                    pattern_ids = tag_pattern_ids
                else:
                    pattern_ids = pattern_ids.intersection(tag_pattern_ids)
            
            pattern_ids = list(pattern_ids) if pattern_ids else []
        else:
            # Pattern must have any tag
            pattern_ids = set()
            for tag in tags:
                pattern_ids.update(self.tag_index.get(tag, []))
            pattern_ids = list(pattern_ids)
        
        patterns = [self.patterns[pid] for pid in pattern_ids if pid in self.patterns]
        patterns.sort(key=lambda p: (p.usage_count, p.confidence), reverse=True)
        
        return patterns[:limit]
    
    def get_pattern_by_id(self, pattern_id: str) -> Optional[CodePattern]:
        """Get a specific pattern by ID"""
        return self.patterns.get(pattern_id)
    
    def update_pattern_usage(self, pattern_id: str) -> None:
        """Increment usage count for a pattern"""
        if pattern_id in self.patterns:
            self.patterns[pattern_id].usage_count += 1
    
    def get_categories(self) -> List[str]:
        """Get all available pattern categories"""
        return list(self.category_index.keys())
    
    def get_category_stats(self) -> Dict[str, int]:
        """Get statistics for each category"""
        return {category: len(pattern_ids) for category, pattern_ids in self.category_index.items()}
    
    def update_embeddings(self) -> None:
        """
        Update embeddings for all patterns
        
        This can be called when the embedding model is updated or
        when new patterns are added in bulk.
        """
        
        if not self.embedding_model:
            self.logger.warning("No embedding model available for updating embeddings")
            return
        
        updated_count = 0
        
        for pattern_id, pattern in self.patterns.items():
            try:
                text_for_embedding = f"{pattern.description} {pattern.vb6_code}"
                embedding = self.embedding_model.encode(text_for_embedding).tolist()
                self.embeddings_cache[pattern_id] = embedding
                updated_count += 1
                
            except Exception as e:
                self.logger.warning(f"Failed to update embedding for pattern {pattern_id}: {e}")
        
        # Save updated embeddings
        self._save_embeddings_cache()
        self.logger.info(f"Updated embeddings for {updated_count} patterns")
    
    def _cosine_similarity(self, a: "np.ndarray", b: "np.ndarray") -> float:
        """Calculate cosine similarity between two vectors"""
        if not NUMPY_AVAILABLE:
            return 0.0
        
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return dot_product / (norm_a * norm_b)
        except:
            return 0.0
    
    def _text_based_similarity(self, query_code: str, patterns: List[CodePattern], 
                              min_similarity: float) -> List[PatternMatch]:
        """Fallback text-based similarity matching"""
        
        matches = []
        query_lower = query_code.lower()
        query_tokens = set(re.findall(r'\w+', query_lower))
        
        for pattern in patterns:
            # Calculate similarity based on keyword overlap
            pattern_text = f"{pattern.vb6_code} {pattern.description}".lower()
            pattern_tokens = set(re.findall(r'\w+', pattern_text))
            
            if not query_tokens or not pattern_tokens:
                continue
            
            # Jaccard similarity
            intersection = query_tokens.intersection(pattern_tokens)
            union = query_tokens.union(pattern_tokens)
            similarity = len(intersection) / len(union) if union else 0.0
            
            # Boost similarity for exact substring matches
            if any(token in pattern_text for token in query_tokens if len(token) > 3):
                similarity += 0.2
            
            # Boost similarity for VB6 keywords
            vb6_keywords = {'dim', 'set', 'sub', 'function', 'if', 'then', 'else', 'for', 'next', 'while', 'wend'}
            keyword_matches = query_tokens.intersection(vb6_keywords).intersection(pattern_tokens)
            if keyword_matches:
                similarity += len(keyword_matches) * 0.1
            
            if similarity >= min_similarity:
                relevance_factors = []
                if intersection:
                    relevance_factors.append("keyword_overlap")
                if keyword_matches:
                    relevance_factors.append("vb6_syntax_match")
                
                match = PatternMatch(
                    pattern=pattern,
                    similarity_score=similarity,
                    match_reason="text_similarity",
                    relevance_factors=relevance_factors
                )
                matches.append(match)
        
        return matches
    
    def _load_patterns(self) -> None:
        """Load patterns from JSON files in the knowledge base directory"""
        
        if not self.patterns_dir.exists():
            self.patterns_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created patterns directory: {self.patterns_dir}")
            return
        
        loaded_count = 0
        
        for json_file in self.patterns_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                category = json_file.stem  # Use filename as category
                
                # Handle different JSON structures
                if isinstance(data, dict):
                    for pattern_key, pattern_data in data.items():
                        if isinstance(pattern_data, dict):
                            pattern = self._create_pattern_from_dict(pattern_key, pattern_data, category)
                            if pattern:
                                self.store_pattern(pattern)
                                loaded_count += 1
                elif isinstance(data, list):
                    for i, pattern_data in enumerate(data):
                        if isinstance(pattern_data, dict):
                            pattern = self._create_pattern_from_dict(f"{category}_{i}", pattern_data, category)
                            if pattern:
                                self.store_pattern(pattern)
                                loaded_count += 1
                
            except Exception as e:
                self.logger.error(f"Failed to load patterns from {json_file}: {e}")
        
        self.logger.info(f"Loaded {loaded_count} patterns from {len(list(self.patterns_dir.glob('*.json')))} files")
    
    def _create_pattern_from_dict(self, pattern_key: str, pattern_data: dict, category: str) -> Optional[CodePattern]:
        """Create a CodePattern from dictionary data"""
        
        try:
            # Handle different JSON structures
            if 'pattern' in pattern_data and 'csharp_equivalent' in pattern_data:
                # Structure: {"pattern": "vb6_code", "csharp_equivalent": "cs_code", "description": "..."}
                return CodePattern(
                    id="",  # Will be auto-generated
                    name=pattern_key,
                    description=pattern_data.get('description', pattern_key),
                    category=category,
                    vb6_code=pattern_data['pattern'],
                    csharp_code=pattern_data['csharp_equivalent'],
                    tags=pattern_data.get('tags', []),
                    complexity=pattern_data.get('complexity', 'medium'),
                    confidence=pattern_data.get('confidence', 1.0),
                    metadata=pattern_data.get('metadata', {})
                )
            elif 'vb6_code' in pattern_data and 'csharp_code' in pattern_data:
                # Direct structure
                return CodePattern(
                    id=pattern_data.get('id', ""),
                    name=pattern_data.get('name', pattern_key),
                    description=pattern_data.get('description', pattern_key),
                    category=pattern_data.get('category', category),
                    vb6_code=pattern_data['vb6_code'],
                    csharp_code=pattern_data['csharp_code'],
                    tags=pattern_data.get('tags', []),
                    complexity=pattern_data.get('complexity', 'medium'),
                    confidence=pattern_data.get('confidence', 1.0),
                    metadata=pattern_data.get('metadata', {})
                )
            else:
                self.logger.warning(f"Invalid pattern structure for {pattern_key}: {pattern_data}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create pattern from {pattern_key}: {e}")
            return None
    
    def _load_embeddings_cache(self) -> None:
        """Load cached embeddings from disk"""
        
        if self.embeddings_cache_path.exists():
            try:
                with open(self.embeddings_cache_path, 'r', encoding='utf-8') as f:
                    self.embeddings_cache = json.load(f)
                self.logger.debug(f"Loaded {len(self.embeddings_cache)} cached embeddings")
            except Exception as e:
                self.logger.warning(f"Failed to load embeddings cache: {e}")
    
    def _save_embeddings_cache(self) -> None:
        """Save embeddings cache to disk"""
        
        try:
            with open(self.embeddings_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.embeddings_cache, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save embeddings cache: {e}")
    
    def save_patterns_to_file(self, category: str, file_path: str = None) -> None:
        """
        Save patterns from a category to a JSON file
        
        Args:
            category: Category to save
            file_path: Optional custom file path
        """
        
        if file_path is None:
            file_path = self.patterns_dir / f"{category}.json"
        else:
            file_path = Path(file_path)
        
        pattern_ids = self.category_index.get(category, [])
        patterns_data = {}
        
        for pattern_id in pattern_ids:
            if pattern_id in self.patterns:
                pattern = self.patterns[pattern_id]
                patterns_data[pattern.name] = {
                    "pattern": pattern.vb6_code,
                    "csharp_equivalent": pattern.csharp_code,
                    "description": pattern.description,
                    "tags": pattern.tags,
                    "complexity": pattern.complexity,
                    "confidence": pattern.confidence,
                    "metadata": pattern.metadata
                }
        
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(patterns_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved {len(patterns_data)} patterns to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save patterns to {file_path}: {e}")
    
    def get_pattern_suggestions(self, vb6_code: str, context: Dict[str, Any] = None) -> List[PatternMatch]:
        """
        Get intelligent pattern suggestions for VB6 code
        
        Args:
            vb6_code: VB6 code snippet to analyze
            context: Optional context information (file_type, component_type, etc.)
            
        Returns:
            List of relevant PatternMatch objects
        """
        
        suggestions = []
        
        # Determine likely categories based on code content
        categories = self._infer_categories_from_code(vb6_code, context)
        
        # Search each relevant category
        for category in categories:
            category_matches = self.retrieve_similar_patterns(
                vb6_code, 
                top_k=3, 
                category=category, 
                min_similarity=0.2
            )
            suggestions.extend(category_matches)
        
        # Remove duplicates and sort by similarity
        seen_ids = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion.pattern.id not in seen_ids:
                seen_ids.add(suggestion.pattern.id)
                unique_suggestions.append(suggestion)
        
        unique_suggestions.sort(key=lambda x: x.similarity_score, reverse=True)
        return unique_suggestions[:5]  # Top 5 suggestions
    
    def _infer_categories_from_code(self, vb6_code: str, context: Dict[str, Any] = None) -> List[str]:
        """Infer likely pattern categories from VB6 code content"""
        
        categories = []
        code_lower = vb6_code.lower()
        
        # Form-related patterns
        if any(keyword in code_lower for keyword in ['form_load', 'command1_click', 'text1_change', 'private sub']):
            categories.append('forms_patterns')
        
        # Business logic patterns  
        if any(keyword in code_lower for keyword in ['function', 'sub', 'dim', 'if then', 'select case']):
            categories.append('business_logic_patterns')
        
        # Data access patterns
        if any(keyword in code_lower for keyword in ['adodb', 'recordset', 'connection', 'sql', 'database']):
            categories.append('data_access_patterns')
        
        # COM patterns
        if any(keyword in code_lower for keyword in ['createobject', 'set obj', 'com', 'activex']):
            categories.append('com_patterns')
        
        # Error handling patterns
        if any(keyword in code_lower for keyword in ['on error', 'err.raise', 'resume next']):
            categories.append('error_handling_patterns')
        
        # If no specific patterns detected, include general patterns
        if not categories:
            categories = ['general_patterns', 'business_logic_patterns']
        
        return categories


def main():
    """Test the RAGManager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Manager for VB6 to C# Translation")
    parser.add_argument("--action", choices=['load', 'search', 'categories', 'stats'], 
                       default='stats', help="Action to perform")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--category", help="Category filter")
    parser.add_argument("--knowledge-base", help="Knowledge base directory path")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Initialize RAG manager
    rag_manager = RAGManager(args.knowledge_base)
    
    if args.action == 'stats':
        print("\n=== RAG Manager Statistics ===")
        print(f"Total patterns: {len(rag_manager.patterns)}")
        print(f"Categories: {len(rag_manager.get_categories())}")
        print(f"Embeddings cached: {len(rag_manager.embeddings_cache)}")
        
        print("\nCategory breakdown:")
        for category, count in rag_manager.get_category_stats().items():
            print(f"  {category}: {count} patterns")
    
    elif args.action == 'categories':
        print("\n=== Available Categories ===")
        for category in sorted(rag_manager.get_categories()):
            print(f"  {category}")
    
    elif args.action == 'search' and args.query:
        print(f"\n=== Search Results for: {args.query} ===")
        matches = rag_manager.retrieve_similar_patterns(args.query, category=args.category)
        
        for i, match in enumerate(matches, 1):
            print(f"\n{i}. {match.pattern.name} (similarity: {match.similarity_score:.3f})")
            print(f"   Category: {match.pattern.category}")
            print(f"   Description: {match.pattern.description}")
            print(f"   VB6: {match.pattern.vb6_code[:100]}...")
            print(f"   C#: {match.pattern.csharp_code[:100]}...")
    
    elif args.action == 'load':
        print("\n=== Reloading Patterns ===")
        rag_manager._load_patterns()
        print(f"Loaded {len(rag_manager.patterns)} patterns")


if __name__ == "__main__":
    main()
