import json
import datetime
from typing import Dict, Any, List

import faiss
import numpy as np

from utils.config import MEMORY_INDEX_DIR
from utils.logging_utils import setup_logger

logger = setup_logger(__name__)


class ModelMemory:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.metadata: List[Dict] = []
        self.memory_path = MEMORY_INDEX_DIR
        self.memory_path.mkdir(parents=True, exist_ok=True)

    def add_model(self, vector: np.ndarray, model_name: str, metadata: Dict = None):
        if len(vector) != self.dim:
            raise ValueError(f"Vector dimension {len(vector)} != {self.dim}")
        vector = vector / np.linalg.norm(vector)
        vector = vector.astype("float32").reshape(1, -1)
        self.index.add(vector)
        self.metadata.append(
            {
                "model_name": model_name,
                "timestamp": datetime.datetime.now().isoformat(),
                "shap_vector": vector.flatten().tolist(),
                "metadata": metadata or {},
            }
        )

    def find_similar(self, query_vector: np.ndarray, k: int = 5) -> List[Dict]:
        if len(query_vector) != self.dim:
            raise ValueError(f"Query vector dimension {len(query_vector)} != {self.dim}")
        query_vector = query_vector / np.linalg.norm(query_vector)
        query_vector = query_vector.astype("float32").reshape(1, -1)
        distances, indices = self.index.search(query_vector, k)
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx >= 0:
                meta = self.metadata[idx].copy()
                meta["similarity"] = float(dist)
                meta["distance"] = 1 - float(dist)
                results.append(meta)
        return results

    def save(self):
        faiss.write_index(self.index, str(self.memory_path / "model_memory.index"))
        with open(self.memory_path / "model_memory.json", "w") as f:
            json.dump(self.metadata, f)
        logger.info("Memory index saved to %s (%d entries)", self.memory_path, len(self.metadata))

    @classmethod
    def load(cls, dim: int):
        memory = cls(dim)
        try:
            loaded_index = faiss.read_index(str(memory.memory_path / "model_memory.index"))
            if loaded_index.d != dim:
                # Stale index from a prior run with different feature count; start fresh.
                logger.warning(
                    "Stale FAISS index (dim=%d, expected %d) -- starting fresh",
                    loaded_index.d, dim,
                )
                return memory
            memory.index = loaded_index
            with open(memory.memory_path / "model_memory.json", "r") as f:
                memory.metadata = json.load(f)
            logger.info("Loaded memory index from %s (%d entries)", memory.memory_path, len(memory.metadata))
        except (FileNotFoundError, RuntimeError):
            logger.info("No existing memory index found -- starting fresh")
        return memory


def run_feedback_memory_agent(shap_data: Dict[str, Any], model_name: str) -> List[Dict]:
    try:
        if not isinstance(shap_data, dict) or "mean_vector" not in shap_data:
            raise ValueError("SHAP data must contain 'mean_vector'")
        vector = np.array(shap_data["mean_vector"], dtype="float32")
        dim = len(vector)
        memory = ModelMemory.load(dim)
        memory.add_model(
            vector,
            model_name,
            {
                "feature_names": shap_data.get("feature_names", []),
                "norm_factor": shap_data.get("norm_factor", 1.0),
            },
        )
        similar_models = memory.find_similar(vector)
        memory.save()
        logger.info("Feedback memory agent complete -- %d similar models returned", len(similar_models))
        return similar_models
    except Exception as e:
        raise RuntimeError(f"Model similarity search failed: {e}")
