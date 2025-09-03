import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

import chromadb
from Utils.model_interface import EmbeddingsClient


@dataclass
class CodePattern:
    id: Optional[int]
    vb6_code: str
    csharp_code: str
    category: str
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class PatternMatch:
    pattern: CodePattern
    similarity_score: float
    match_reason: str


class RAGManager:
    def __init__(self, 
                 chroma_db_path: str = "./chroma_db",
                 collection_name: str = "code_patterns"):
        
        self.logger = logging.getLogger(__name__)
        self.chroma_db_path = chroma_db_path
        self.collection_name = collection_name
        
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
        
        try:
            self.embeddings_client = EmbeddingsClient()
            self.logger.info("Initialized embeddings client")
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings client: {e}")
            self.embeddings_client = None
            self.logger.error("Cannot store patterns without embeddings client. Please fix embeddings configuration.")
            return
        
        self._ensure_patterns_loaded()
    
    def _ensure_patterns_loaded(self):
        try:
            if self.collection.count() == 0:
                self.logger.info("Collection is empty, loading patterns from JSON files")
                self.load_patterns_from_json()
        except Exception as e:
            self.logger.warning(f"Could not check collection count: {e}")
    
    def _generate_embedding(self, pattern: CodePattern) -> Optional[List[float]]:
        try:
            text = f"Category: {pattern.category}\nVB6 Code: {pattern.vb6_code}"
            return self.embeddings_client.embed_text(text)
        except Exception as e:
            self.logger.warning(f"Failed to generate embedding: {e}")
            return None
    
    def _create_metadata(self, pattern: CodePattern) -> Dict[str, str]:
        return {
            "category": pattern.category,
            "created_at": pattern.created_at.isoformat() if pattern.created_at else datetime.now().isoformat(),
            "vb6_code": pattern.vb6_code,
            "csharp_translation": pattern.csharp_code
        }
    
    def store_pattern(self, pattern: CodePattern) -> bool:
        if not self.embeddings_client:
            self.logger.error("Cannot store pattern: embeddings client not initialized")
            return False
            
        if not pattern.vb6_code.strip():
            return False
            
        try:
            embedding = self._generate_embedding(pattern)
            if not embedding:
                return False
            
            pattern.embedding = embedding
            pattern_id = pattern.id if pattern.id else int(time.time() * 1000)
            
            self.collection.add(
                documents=[f"VB6: {pattern.vb6_code}\nC#: {pattern.csharp_code}"],
                embeddings=[embedding],
                metadatas=[self._create_metadata(pattern)],
                ids=[str(pattern_id)]
            )
            
            pattern.id = pattern_id
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern: {e}")
            return False
    
    def retrieve_similar_patterns(self, vb6_code: str, top_k: int = 5, category: str = None) -> List[PatternMatch]:
        if not vb6_code.strip() or not self.embeddings_client:
            return []
        
        try:
            where_filter = {"category": category} if category else None
            query_embedding = self.embeddings_client.embed_text(f"VB6 Code: {vb6_code}")
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 100),
                where=where_filter,
                include=['metadatas', 'distances']
            )
            
            matches = []
            if results and results['ids'] and results['ids'][0]:
                for i, pattern_id in enumerate(results['ids'][0]):
                    metadata = results['metadatas'][0][i]
                    distance = results.get('distances', [[0.5]])[0][i] if 'distances' in results else 0.5
                    similarity = max(0, 1 - distance)
                    
                    pattern = CodePattern(
                        id=int(pattern_id),
                        vb6_code=metadata.get('vb6_code', ''),
                        csharp_code=metadata.get('csharp_translation', ''),
                        category=metadata.get('category', 'unknown'),
                        created_at=datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
                    )
                    
                    match_reason = "category_and_semantic_match" if category and metadata.get('category') == category else "semantic_similarity"
                    
                    matches.append(PatternMatch(
                        pattern=pattern,
                        similarity_score=similarity,
                        match_reason=match_reason
                    ))
            
            matches.sort(key=lambda x: x.similarity_score, reverse=True)
            return matches
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve similar patterns: {e}")
            return []
    
    def load_patterns_from_json(self, patterns_dir: str = None, batch_size: int = 50) -> int:
        if patterns_dir is None:
            patterns_dir = Path(__file__).parent / "VB6_to_CSharp_Equivalents"
        
        patterns_path = Path(patterns_dir)
        if not patterns_path.exists() or not self.embeddings_client:
            return 0
        
        category_mapping = {
            'forms_patterns': 'form',
            'business_logic_patterns': 'business_logic',
            'data_access_patterns': 'data_access',
            'com_patterns': 'method',
            'error_handling_patterns': 'method'
        }
        
        all_patterns = []
        for json_file in patterns_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                category = category_mapping.get(json_file.stem, 'method')
                self.logger.info(f"Collecting patterns from {json_file.name} as category '{category}'")
                
                for pattern_name, pattern_data in data.items():
                    vb6_code = pattern_data.get('pattern', '')
                    csharp_code = pattern_data.get('csharp_equivalent', '')
                    
                    if vb6_code and csharp_code:
                        all_patterns.append(CodePattern(
                            id=None,
                            vb6_code=vb6_code,
                            csharp_code=csharp_code,
                            category=category
                        ))
                    else:
                        self.logger.warning(f"Skipping incomplete pattern: {pattern_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to load patterns from {json_file}: {e}")
        
        self.logger.info(f"Processing {len(all_patterns)} patterns in batches of {batch_size}")
        loaded_count = 0
        
        for i in range(0, len(all_patterns), batch_size):
            batch = all_patterns[i:i + batch_size]
            batch_loaded = self._store_pattern_batch(batch)
            loaded_count += batch_loaded
        
        self.logger.info(f"Loaded {loaded_count} patterns from {len(list(patterns_path.glob('*.json')))} files")
        return loaded_count
    
    def _store_pattern_batch(self, patterns: List[CodePattern]) -> int:
        if not patterns:
            return 0
        
        try:
            documents, embeddings, metadatas, ids = [], [], [], []
            
            for pattern in patterns:
                if not pattern.vb6_code.strip():
                    continue
                
                # Simple duplicate check - skip if pattern already exists
                try:
                    existing = self.collection.get(
                        where={"category": pattern.category},
                        include=['metadatas']
                    )
                    if existing and existing['metadatas']:
                        for metadata in existing['metadatas']:
                            if metadata.get('vb6_code') == pattern.vb6_code:
                                continue  # Skip duplicate
                except:
                    pass  # If check fails, continue with storing
                
                embedding = self._generate_embedding(pattern)
                if not embedding:
                    continue
                
                pattern.embedding = embedding
                pattern_id = pattern.id if pattern.id else int(time.time() * 1000) + len(ids)
                
                documents.append(f"VB6: {pattern.vb6_code}\nC#: {pattern.csharp_code}")
                embeddings.append(embedding)
                metadatas.append(self._create_metadata(pattern))
                ids.append(str(pattern_id))
                pattern.id = pattern_id
            
            if documents:
                self.collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
                return len(documents)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern batch: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        try:
            pattern_count = self.collection.count()
        except Exception as e:
            self.logger.warning(f"Failed to get collection count: {e}")
            pattern_count = 0
        
        return {
            'total_patterns': pattern_count,
            'chroma_db_path': self.chroma_db_path,
            'collection_name': self.collection_name,
            'embeddings_available': self.embeddings_client is not None
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Manager for VB6 to C# Translation")
    parser.add_argument("--action", choices=['load', 'search', 'stats'], default='stats')
    parser.add_argument("--query", help="Search query (VB6 code)")
    parser.add_argument("--category", help="Category filter")
    parser.add_argument("--patterns-dir", help="Patterns directory path", 
                       default="Knowledge/VB6_to_CSharp_Equivalents")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rag_manager = RAGManager()
    
    if args.action == 'stats':
        stats = rag_manager.get_stats()
        print(f"Total patterns: {stats['total_patterns']}")
        print(f"ChromaDB path: {stats['chroma_db_path']}")
        print(f"Collection: {stats['collection_name']}")
        print(f"Embeddings available: {stats['embeddings_available']}")
    
    elif args.action == 'search' and args.query:
        matches = rag_manager.retrieve_similar_patterns(args.query, top_k=3, category=args.category)
        for i, match in enumerate(matches, 1):
            print(f"{i}. Pattern ID: {match.pattern.id}")
            print(f"   Similarity: {match.similarity_score:.3f}")
            print(f"   Category: {match.pattern.category}")
            print(f"   Match Reason: {match.match_reason}")
            print(f"   VB6: {match.pattern.vb6_code[:100]}...")
            print(f"   C#: {match.pattern.csharp_code[:100]}...")
    
    elif args.action == 'load':
        count = rag_manager.load_patterns_from_json(args.patterns_dir)
        print(f"Loaded {count} patterns")


if __name__ == "__main__":
    main()