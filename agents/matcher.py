import chromadb
from deepface import DeepFace
import numpy as np
from agents.base import BaseAgent
from typing import Optional, Dict, Any
import os

class IdentityMatchingAgent(BaseAgent):
    """
    Agent responsible for matching a detected face against a known database.
    Uses DeepFace for embeddings and ChromaDB for vector search.
    """
    def __init__(self, name: str = "IdentityMatchingAgent", config: dict = None):
        super().__init__(name, config)
        self.db_path = self.config.get("db_path", "data/vector_db")
        self.collection_name = self.config.get("collection_name", "faces")
        self.threshold = self.config.get("threshold", 0.4) # Distance threshold
        self.model_name = self.config.get("model_name", "VGG-Face")
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        self.collection = self.chroma_client.get_or_create_collection(name=self.collection_name)
        self.logger.info(f"Connected to ChromaDB at {self.db_path}, collection: {self.collection_name}")

    def run(self, face_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives face image, matches it, and returns identity results.
        Input: {"face_image": np.ndarray, "box": tuple}
        """
        try:
            face_img = face_data.get("face_image")
            if face_img is None:
                return {"identity": "Unknown", "confidence": 0, "status": "no_face"}

            # Generate embedding
            # Note: DeepFace.represent returns a list of objects
            # We enforce detection false because the FaceDetectionAgent already did it
            embedding_objs = DeepFace.represent(
                img_path=face_img, 
                model_name=self.model_name, 
                enforce_detection=False
            )
            
            if not embedding_objs:
                return {"identity": "Unknown", "confidence": 0}
                
            embedding = embedding_objs[0]["embedding"]
            
            # Search ChromaDB
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=1
            )
            
            if not results["ids"] or not results["ids"][0]:
                return {"identity": "Unknown", "confidence": 0, "box": face_data["box"]}
            
            best_match_id = results["ids"][0][0]
            distance = results["distances"][0][0]
            metadata = results["metadatas"][0][0]
            
            # Distance in ChromaDB (cosine/l2) - lower is better for some metrics
            # For VGG-Face with cosine, distance < 0.4 is usually a good match
            if distance < self.threshold:
                self.logger.info(f"Match found: {best_match_id} (dist: {distance:.4f})")
                return {
                    "identity": best_match_id,
                    "confidence": 1 - distance,
                    "metadata": metadata,
                    "box": face_data["box"]
                }
            else:
                self.logger.info(f"Unknown face detected (best dist: {distance:.4f})")
                return {"identity": "Unknown", "confidence": 1 - distance, "box": face_data["box"]}
                
        except Exception as e:
            return self.handle_error(e, "matching identity")
