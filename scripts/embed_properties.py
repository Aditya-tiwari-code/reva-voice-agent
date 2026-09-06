import os
import sys
from pathlib import Path

# Add project root directory to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.rag.embedder import PropertyEmbedder

def main():
    csv_path = os.path.join(ROOT_DIR, "data", "properties.csv")
    db_path = os.path.join(ROOT_DIR, "chroma_db")

    print(f"Loading properties from: {csv_path}")
    print(f"Initializing ChromaDB vector store at: {db_path}")

    embedder = PropertyEmbedder(db_path=db_path)
    count = embedder.load_and_embed_csv(csv_path)

    print(f"[SUCCESS] Embedded {count} properties into ChromaDB")

if __name__ == "__main__":
    main()
