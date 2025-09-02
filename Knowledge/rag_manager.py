"""
Simplified RAG Manager for VB6 to C# Translation using ChromaDB

This module provides a streamlined RAG system using ChromaDB with nomic-embed-text
embeddings for VB6-to-C# code translation pattern retrieval.

Schema:
- id: SERIAL PRIMARY KEY
- vb6_code: TEXT NOT NULL
- csharp_translation: TEXT NOT NULL  
- embedding: VECTOR(768) -- for nomic-embed-text
- category: VARCHAR(50) -- 'form', 'class', 'method', 'data_access'
- complexity: VARCHAR(20) -- 'simple', 'medium', 'complex'
- created_at: TIMESTAMP DEFAULT NOW()
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None

try:
    from Utils.model_interface import NomicEmbeddingsClient
    NOMIC_AVAILABLE = True
except ImportError:
    NOMIC_AVAILABLE = False
    NomicEmbeddingsClient = None


@dataclass
class CodePattern:
    """Represents a VB6 to C# translation pattern"""
    id: Optional[int]
    vb6_code: str
    csharp_translation: str
    category: str  # 'form', 'class', 'method', 'data_access'
    complexity: str  # 'simple', 'medium', 'complex'
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass 
class PatternMatch:
    """Represents a pattern match with similarity score"""
    pattern: CodePattern
    similarity_score: float
    match_reason: str


class RAGManager:
    """
    Simplified RAG Manager using ChromaDB with nomic-embed-text embeddings.
    
    Provides pattern storage, retrieval, and similarity matching for VB6 to C# translation.
    """
    
    def __init__(self, 
                 chroma_db_path: str = "./chroma_db",
                 collection_name: str = "code_patterns"):
        
        self.logger = logging.getLogger(__name__)
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        
        # Initialize ChromaDB
        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB not available. Install with: pip install chromadb")
        
        try:
            self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "VB6 to C# code translation patterns"}
            )
            self.logger.info(f"Initialized ChromaDB at {chroma_db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
        
        # Initialize embeddings client
        if not NOMIC_AVAILABLE:
            self.logger.warning("NomicEmbeddingsClient not available. Some features may not work.")
            self.embeddings_client = None
        else:
            try:
                self.embeddings_client = NomicEmbeddingsClient()
                self.logger.info("Initialized Nomic embeddings client")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Nomic embeddings: {e}")
                self.embeddings_client = None
        
        # Pattern statistics
        self.pattern_count = 0
        self._update_stats()
    
    def _update_stats(self):
        """Update pattern statistics"""
        try:
            self.pattern_count = self.collection.count()
        except Exception as e:
            self.logger.warning(f"Failed to get collection count: {e}")
            self.pattern_count = 0
    
    def store_pattern(self, pattern: CodePattern) -> bool:
        """
        Store a code pattern in ChromaDB
        
        Args:
            pattern: CodePattern to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Generate embedding if client is available
            embedding = None
            if self.embeddings_client and pattern.vb6_code.strip():
                try:
                    # Combine VB6 code with category for better context
                    text_for_embedding = f"Category: {pattern.category}\nVB6 Code: {pattern.vb6_code}"
                    embedding = self.embeddings_client.embed_text(text_for_embedding)
                    pattern.embedding = embedding
                    self.logger.debug(f"Generated embedding with {len(embedding)} dimensions")
                except Exception as e:
                    self.logger.warning(f"Failed to generate embedding: {e}")
            
            # Prepare document for ChromaDB
            document = f"VB6: {pattern.vb6_code}\nC#: {pattern.csharp_translation}"
            
            # Generate ID if not provided
            pattern_id = pattern.id if pattern.id else int(time.time() * 1000)
            
            # Store in ChromaDB - let ChromaDB handle embedding dimensions automatically
            if embedding:
                self.collection.add(
                    documents=[document],
                    embeddings=[embedding],
                    metadatas=[{
                        "category": pattern.category,
                        "complexity": pattern.complexity,
                        "created_at": pattern.created_at.isoformat() if pattern.created_at else datetime.now().isoformat(),
                        "vb6_code": pattern.vb6_code,
                        "csharp_translation": pattern.csharp_translation
                    }],
                    ids=[str(pattern_id)]
                )
            else:
                # Store without embedding if generation failed
                self.collection.add(
                    documents=[document],
                    metadatas=[{
                        "category": pattern.category,
                        "complexity": pattern.complexity,
                        "created_at": pattern.created_at.isoformat() if pattern.created_at else datetime.now().isoformat(),
                        "vb6_code": pattern.vb6_code,
                        "csharp_translation": pattern.csharp_translation
                    }],
                    ids=[str(pattern_id)]
                )
            
            pattern.id = pattern_id
            self.pattern_count += 1
            self.logger.debug(f"Stored pattern {pattern_id} in category {pattern.category}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            if "Collection expecting embedding with dimension" in error_msg:
                self.logger.error(f"Embedding dimension mismatch when storing pattern: {e}")
                self.logger.info("Attempting to reset collection for correct embedding dimensions...")
                try:
                    # Try to reset the collection
                    if self.reset_collection_for_new_embeddings():
                        self.logger.info("Collection reset successful, retrying pattern storage...")
                        # Retry storing the pattern
                        return self.store_pattern(pattern)
                    else:
                        self.logger.error("Failed to reset collection, cannot store pattern")
                        return False
                except Exception as reset_error:
                    self.logger.error(f"Failed to reset collection: {reset_error}")
                    return False
            else:
                self.logger.error(f"Failed to store pattern: {e}")
                return False
    
    def retrieve_similar_patterns(self, 
                                 vb6_code: str, 
                                 top_k: int = 5,
                                 category: str = None,
                                 complexity: str = None) -> List[PatternMatch]:
        """
        Retrieve patterns similar to the given VB6 code
        
        Args:
            vb6_code: VB6 code to find patterns for
            top_k: Maximum number of patterns to return
            category: Optional category filter ('form', 'class', 'method', 'data_access')
            complexity: Optional complexity filter ('simple', 'medium', 'complex')
            
        Returns:
            List of PatternMatch objects sorted by similarity
        """
        
        if not vb6_code.strip():
            return []
        
        try:
            # Build query filters
            where_filter = {}
        if category:
                where_filter["category"] = category
            if complexity:
                where_filter["complexity"] = complexity
            
            # Prepare query text
            query_text = f"VB6 Code: {vb6_code}"
            
            # Search ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=min(top_k, self.pattern_count) if self.pattern_count > 0 else top_k,
                where=where_filter if where_filter else None
            )
            
            # Convert results to PatternMatch objects
            matches = []
            if results and results['ids'] and results['ids'][0]:
                for i, pattern_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results.get('distances', [[0.5]])[0][i] if 'distances' in results else 0.5
                    
                    # Convert distance to similarity (ChromaDB returns cosine distance)
                    similarity = max(0, 1 - distance)
                    
                    # Create pattern object
                    pattern = CodePattern(
                        id=int(pattern_id),
                        vb6_code=metadata.get('vb6_code', ''),
                        csharp_translation=metadata.get('csharp_translation', ''),
                        category=metadata.get('category', 'unknown'),
                        complexity=metadata.get('complexity', 'medium'),
                        created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
                    )
                    
                    # Determine match reason
                    match_reason = "semantic_similarity"
                    if category and metadata.get('category') == category:
                        match_reason = "category_and_semantic_match"
                    
                            match = PatternMatch(
                                pattern=pattern,
                                similarity_score=similarity,
                        match_reason=match_reason
                            )
                            matches.append(match)
                            
            return matches
            
            except Exception as e:
            error_msg = str(e)
            if "Collection expecting embedding with dimension" in error_msg:
                self.logger.error(f"Embedding dimension mismatch: {e}")
                self.logger.info("Attempting to reset collection for correct embedding dimensions...")
                try:
                    # Try to reset the collection
                    if self.reset_collection_for_new_embeddings():
                        self.logger.info("Collection reset successful, retrying query...")
                        # Retry the query
                        results = self.collection.query(
                            query_texts=[query_text],
                            n_results=min(top_k, self.pattern_count) if self.pattern_count > 0 else top_k,
                            where=where_filter if where_filter else None
                        )
                        # Process results as normal
                        matches = []
                        if results and results['ids'] and results['ids'][0]:
                            for i, pattern_id in enumerate(results['ids'][0]):
                                metadata = results['metadatas'][0][i]
                                distance = results.get('distances', [[0.5]])[0][i] if 'distances' in results else 0.5
                                
                                # Convert distance to similarity (ChromaDB returns cosine distance)
                                similarity = max(0, 1 - distance)
                                
                                # Create pattern object
                                pattern = CodePattern(
                                    id=int(pattern_id),
                                    vb6_code=metadata.get('vb6_code', ''),
                                    csharp_translation=metadata.get('csharp_translation', ''),
                                    category=metadata.get('category', 'unknown'),
                                    complexity=metadata.get('complexity', 'medium'),
                                    created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
                                )
                                
                                # Determine match reason
                                match_reason = "semantic_similarity"
                                if similarity > 0.8:
                                    match_reason = "high_similarity"
                                elif similarity > 0.6:
                                    match_reason = "medium_similarity"
                                else:
                                    match_reason = "low_similarity"
                                
                                matches.append(PatternMatch(
                                    pattern=pattern,
                                    similarity_score=similarity,
                                    match_reason=match_reason
                                ))
                        
                        # Sort by similarity score
        matches.sort(key=lambda x: x.similarity_score, reverse=True)
                        return matches
                    else:
                        self.logger.error("Failed to reset collection, returning empty results")
                        return []
                except Exception as reset_error:
                    self.logger.error(f"Failed to reset collection: {reset_error}")
                    return []
            else:
                self.logger.error(f"Failed to retrieve similar patterns: {e}")
                return []
    
    def search_by_category(self, category: str, limit: int = 10) -> List[CodePattern]:
        """
        Search patterns by category
        
        Args:
            category: Category to search ('form', 'class', 'method', 'data_access')
            limit: Maximum number of results
            
        Returns:
            List of CodePattern objects
        """
        
        try:
            results = self.collection.query(
                query_texts=[""],  # Empty query to get all
                n_results=limit,
                where={"category": category}
            )
            
            patterns = []
            if results and results['ids'] and results['ids'][0]:
                for i, pattern_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    
                    pattern = CodePattern(
                        id=int(pattern_id),
                        vb6_code=metadata.get('vb6_code', ''),
                        csharp_translation=metadata.get('csharp_translation', ''),
                        category=metadata.get('category', 'unknown'),
                        complexity=metadata.get('complexity', 'medium'),
                        created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
                    )
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to search by category {category}: {e}")
            return []
    
    def get_categories(self) -> List[str]:
        """Get all available categories"""
        try:
            # Get all patterns to extract unique categories
            results = self.collection.query(
                query_texts=[""],
                n_results=self.pattern_count if self.pattern_count > 0 else 1000
            )
            
            categories = set()
            if results and results['metadatas'] and results['metadatas'][0]:
                for metadata in results['metadatas'][0]:
                    categories.add(metadata.get('category', 'unknown'))
            
            return sorted(list(categories))
            
        except Exception as e:
            self.logger.error(f"Failed to get categories: {e}")
            return ['form', 'class', 'method', 'data_access']  # Default categories
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG manager statistics"""
        
        self._update_stats()
        
        stats = {
            'total_patterns': self.pattern_count,
            'chroma_db_path': self.chroma_db_path,
            'collection_name': self.collection_name,
            'embeddings_available': self.embeddings_client is not None
        }
        
        # Get category breakdown
        try:
            categories = self.get_categories()
            category_counts = {}
            
            for category in categories:
                patterns = self.search_by_category(category, limit=1000)
                category_counts[category] = len(patterns)
            
            stats['categories'] = category_counts
            
        except Exception as e:
            self.logger.warning(f"Failed to get category stats: {e}")
            stats['categories'] = {}
        
        return stats
    
    def load_patterns_from_json(self, patterns_dir: str = "Knowledge/VB6_to_CSharp_Equivalents") -> int:
        """
        Load patterns from JSON files and store in ChromaDB
        
        Args:
            patterns_dir: Directory containing pattern JSON files
            
        Returns:
            int: Number of patterns loaded
        """
        
        patterns_path = Path(patterns_dir)
        if not patterns_path.exists():
            self.logger.error(f"Patterns directory not found: {patterns_path}")
            return 0
        
        loaded_count = 0
        
        # Category mapping for JSON files
        category_mapping = {
            'forms_patterns': 'form',
            'business_logic_patterns': 'class',
            'data_access_patterns': 'data_access',
            'com_patterns': 'method',
            'error_handling_patterns': 'method'
        }
        
        for json_file in patterns_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Determine category from filename
                file_stem = json_file.stem
                category = category_mapping.get(file_stem, 'method')
                
                self.logger.info(f"Loading patterns from {json_file.name} as category '{category}'")
                
                for pattern_name, pattern_data in data.items():
                    try:
                        # Extract pattern information
                        vb6_code = pattern_data.get('pattern', '')
                        csharp_code = pattern_data.get('csharp_equivalent', '')
                        complexity = pattern_data.get('complexity', 'medium')
                        
                        if not vb6_code or not csharp_code:
                            self.logger.warning(f"Skipping incomplete pattern: {pattern_name}")
                            continue
                        
                        # Create pattern object
                        pattern = CodePattern(
                            id=None,  # Will be auto-generated
                            vb6_code=vb6_code,
                            csharp_translation=csharp_code,
                            category=category,
                            complexity=complexity
                        )
                        
                        # Store pattern
                        if self.store_pattern(pattern):
                                loaded_count += 1
                            
                    except Exception as e:
                        self.logger.error(f"Failed to load pattern {pattern_name}: {e}")
                
            except Exception as e:
                self.logger.error(f"Failed to load patterns from {json_file}: {e}")
        
        self.logger.info(f"Loaded {loaded_count} patterns from {len(list(patterns_path.glob('*.json')))} files")
        return loaded_count
    
    def clear_patterns(self) -> bool:
        """Clear all patterns from ChromaDB"""
        try:
            # Delete the collection and recreate it
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "VB6 to C# code translation patterns"}
            )
            self.pattern_count = 0
            self.logger.info("Cleared all patterns from ChromaDB")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear patterns: {e}")
            return False
    
    def reset_collection_for_new_embeddings(self) -> bool:
        """
        Reset the ChromaDB collection to handle embedding dimension changes.
        This is useful when switching embedding models or if there's a dimension mismatch.
        """
        try:
            self.logger.info("Resetting ChromaDB collection for new embedding dimensions")
            
            # Get current patterns before clearing
            current_patterns = []
            try:
                results = self.collection.query(
                    query_texts=[""],
                    n_results=self.pattern_count if self.pattern_count > 0 else 1000
                )
                
                if results and results['ids'] and results['ids'][0]:
                    for i, pattern_id in enumerate(results['ids'][0]):
                        metadata = results['metadatas'][0][i]
                        pattern = CodePattern(
                            id=int(pattern_id),
                            vb6_code=metadata.get('vb6_code', ''),
                            csharp_translation=metadata.get('csharp_translation', ''),
                            category=metadata.get('category', 'unknown'),
                            complexity=metadata.get('complexity', 'medium'),
                            created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
                        )
                        current_patterns.append(pattern)
                        
                self.logger.info(f"Backing up {len(current_patterns)} patterns")
            except Exception as e:
                self.logger.warning(f"Could not backup existing patterns: {e}")
            
            # Clear and recreate collection
            if self.clear_patterns():
                # Restore patterns with new embeddings
                restored_count = 0
                for pattern in current_patterns:
                    if self.store_pattern(pattern):
                        restored_count += 1
                
                self.logger.info(f"Restored {restored_count}/{len(current_patterns)} patterns with new embeddings")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to reset collection: {e}")
            return False


def main():
    """Test the RAG Manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Manager for VB6 to C# Translation")
    parser.add_argument("--action", choices=['load', 'search', 'categories', 'stats', 'clear', 'reset'], 
                       default='stats', help="Action to perform")
    parser.add_argument("--query", help="Search query (VB6 code)")
    parser.add_argument("--category", help="Category filter")
    parser.add_argument("--patterns-dir", help="Patterns directory path", 
                       default="Knowledge/VB6_to_CSharp_Equivalents")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize RAG manager
    rag_manager = RAGManager()
    
    if args.action == 'stats':
        print("\n=== RAG Manager Statistics ===")
        stats = rag_manager.get_stats()
        
        print(f"Total patterns: {stats['total_patterns']}")
        print(f"ChromaDB path: {stats['chroma_db_path']}")
        print(f"Collection: {stats['collection_name']}")
        print(f"Embeddings available: {stats['embeddings_available']}")
        
        print(f"\nCategory breakdown:")
        for category, count in stats.get('categories', {}).items():
            print(f"  {category}: {count} patterns")
    
    elif args.action == 'categories':
        print("\n=== Available Categories ===")
        categories = rag_manager.get_categories()
        for category in categories:
            print(f"  {category}")
    
    elif args.action == 'search' and args.query:
        print(f"\n=== Search Results for: {args.query} ===")
        matches = rag_manager.retrieve_similar_patterns(
            args.query, 
            top_k=3, 
            category=args.category
        )
        
        for i, match in enumerate(matches, 1):
            print(f"\n{i}. Pattern ID: {match.pattern.id}")
            print(f"   Similarity: {match.similarity_score:.3f}")
            print(f"   Category: {match.pattern.category}")
            print(f"   Complexity: {match.pattern.complexity}")
            print(f"   Match Reason: {match.match_reason}")
            print(f"   VB6: {match.pattern.vb6_code[:100]}...")
            print(f"   C#: {match.pattern.csharp_translation[:100]}...")
    
    elif args.action == 'load':
        print(f"\n=== Loading Patterns from {args.patterns_dir} ===")
        count = rag_manager.load_patterns_from_json(args.patterns_dir)
        print(f"Loaded {count} patterns")
    
    elif args.action == 'clear':
        print("\n=== Clearing All Patterns ===")
        if rag_manager.clear_patterns():
            print("Successfully cleared all patterns")
        else:
            print("Failed to clear patterns")
    
    elif args.action == 'reset':
        print("\n=== Resetting Collection for New Embeddings ===")
        if rag_manager.reset_collection_for_new_embeddings():
            print("Successfully reset collection with new embeddings")
        else:
            print("Failed to reset collection")


if __name__ == "__main__":
    main()