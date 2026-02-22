import os
import chromadb
from deepface import DeepFace
import argparse
from tqdm import tqdm

def register_faces(image_folder, db_path="data/vector_db", collection_name="faces"):
    """
    Reads images from image_folder (filenames should be person names) 
    and adds their embeddings to ChromaDB.
    """
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(name=collection_name)
    
    print(f"Registering faces from {image_folder}...")
    
    for filename in tqdm(os.listdir(image_folder)):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            person_name = os.path.splitext(filename)[0]
            img_path = os.path.join(image_folder, filename)
            
            try:
                # Generate embedding
                embedding_objs = DeepFace.represent(
                    img_path=img_path, 
                    model_name="VGG-Face",
                    enforce_detection=True
                )
                
                if embedding_objs:
                    embedding = embedding_objs[0]["embedding"]
                    
                    # Add to ChromaDB
                    collection.add(
                        embeddings=[embedding],
                        ids=[person_name],
                        metadatas=[{"name": person_name, "source": img_path}]
                    )
                    # print(f"Registered: {person_name}")
                else:
                    print(f"No face detected in {filename}, skipping.")
                    
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register faces in Vector Store")
    parser.add_argument("--folder", type=str, required=True, help="Folder containing images of people")
    args = parser.parse_args()
    
    register_faces(args.folder)
