import os
import time
import json
import numpy as np
from typing import List, Tuple, Dict, Optional
from dotenv import load_dotenv

# RateLimiter is now imported from llm_cache to ensure singleton usage
from llm_cache import cached_embed_content, RateLimiter
from app_config import config

load_dotenv()

REGISTRY_FILE = config.get("paths", "registry_file", "data/library_registry.json")
DATA_DIR = config.get("paths", "data_dir", "data")
EMBEDDING_MODEL = "models/text-embedding-004"

# Derived paths for vector storage
VECTOR_INDEX_FILE = os.path.join(DATA_DIR, "vector_index.npy")
VECTOR_IDS_FILE = os.path.join(DATA_DIR, "vector_ids.json")

class LibrarianAgent:
    """
    A lightweight Knowledge Base that performs semantic search over 
    a JSON registry using in-memory vector math.
    Persists the vector index to disk to avoid rebuilding on every run.
    """
    def __init__(self, api_key: str = None):
        # NOTE: cached_embed_content now handles rate limiting internally
        self.registry: Dict[str, Dict] = {}
        self.ids: List[str] = []
        self.vector_matrix: Optional[np.ndarray] = None
        self.api_key = api_key
        
        self._load_registry()
        self._build_vector_index()

    def _load_registry(self):
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE, 'r') as f:
                    self.registry = json.load(f)
                print(f"   [Librarian] Loaded registry with {len(self.registry)} components.")
            except Exception as e:
                print(f"   [Librarian] Error loading registry: {e}")
                self.registry = {}
        else:
            print(f"   [Librarian] Warning: {REGISTRY_FILE} not found. Library is empty.")

    def _build_vector_index(self):
        """
        Loads vectors from disk if they match the registry, otherwise rebuilds them.
        """
        if not self.registry:
            return

        # 1. Try Loading from Disk
        if self._try_load_vectors():
            return

        # 2. Rebuild if missing or stale
        vectors = []
        self.ids = []

        print("   [Librarian] Building Vector Index (Registry changed or index missing)...")
        
        for protein_id, data in self.registry.items():
            # Construct semantic text
            text = f"{protein_id} {data.get('description', '')} Keywords: {', '.join(data.get('keywords', []))}"
            
            # Rate limiting is handled inside cached_embed_content
            try:
                result = cached_embed_content(
                    model=EMBEDDING_MODEL,
                    content=text,
                    task_type="retrieval_document",
                    api_key=self.api_key
                )
                embedding = result['embedding']
                
                vectors.append(embedding)
                self.ids.append(protein_id)
            except Exception as e:
                print(f"      [Warning] Failed to embed {protein_id}: {e}")

        if vectors:
            self.vector_matrix = np.array(vectors)
            self._save_vectors()
            print(f"   [Librarian] Index built and saved. Shape: {self.vector_matrix.shape}")

    def _try_load_vectors(self) -> bool:
        """
        Attempts to load existing vector index. 
        Returns True only if files exist AND match the current registry keys.
        """
        if os.path.exists(VECTOR_INDEX_FILE) and os.path.exists(VECTOR_IDS_FILE):
            try:
                # Load IDs first to check consistency
                with open(VECTOR_IDS_FILE, 'r') as f:
                    saved_ids = json.load(f)
                
                # Check if Registry matches Saved IDs (Set comparison for robustness)
                current_keys = set(self.registry.keys())
                saved_keys = set(saved_ids)
                
                if current_keys == saved_keys:
                    self.vector_matrix = np.load(VECTOR_INDEX_FILE)
                    self.ids = saved_ids
                    print(f"   [Librarian] Loaded cached vector index ({len(self.ids)} items).")
                    return True
                else:
                    print("   [Librarian] Registry changed. Rebuilding index.")
                    return False
            except Exception as e:
                print(f"   [Librarian] Error loading cached index: {e}")
                return False
        return False

    def _save_vectors(self):
        """Saves the current vector matrix and IDs to disk."""
        try:
            if self.vector_matrix is not None:
                np.save(VECTOR_INDEX_FILE, self.vector_matrix)
                with open(VECTOR_IDS_FILE, 'w') as f:
                    json.dump(self.ids, f)
        except Exception as e:
            print(f"   [Librarian] Warning: Failed to save vector index: {e}")

    def search(self, query: str, k=3) -> List[Tuple[str, str, float]]:
        if self.vector_matrix is None or len(self.ids) == 0:
            return []

        # Rate limiting is handled inside cached_embed_content
        try:
            result = cached_embed_content(
                model=EMBEDDING_MODEL,
                content=query,
                task_type="retrieval_query",
                api_key=self.api_key
            )
            query_vec = np.array(result['embedding'])
        except Exception as e:
            print(f"   [Librarian] Search error: {e}")
            return []

        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0: query_vec = query_vec / q_norm
        
        db_norms = np.linalg.norm(self.vector_matrix, axis=1)
        
        with np.errstate(divide='ignore', invalid='ignore'):
            scores = np.dot(self.vector_matrix, query_vec) / db_norms
            scores = np.nan_to_num(scores)

        top_indices = np.argsort(-scores)[:k]
        
        results = []
        for idx in top_indices:
            score = scores[idx]
            if score < 0.3: continue
            
            comp_id = self.ids[idx]
            desc = self.registry[comp_id].get('description', 'No description')
            
            distance = 1.0 - score
            results.append((comp_id, desc, distance))
            
        return results

    def close(self):
        pass