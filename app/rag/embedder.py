import os
import csv
import chromadb
from sentence_transformers import SentenceTransformer

class PropertyEmbedder:
    """
    Handles CSV dataset loading, vector embedding generation using SentenceTransformers,
    and storage in ChromaDB vector store.
    """

    def __init__(self, db_path: str = "./chroma_db", collection_name: str = "properties", model_name: str = "all-MiniLM-L6-v2"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=db_path)
        self.model = SentenceTransformer(model_name)
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def load_and_embed_csv(self, csv_path: str) -> int:
        """
        Reads CSV property dataset, builds descriptive document strings,
        generates vector embeddings, and upserts into ChromaDB.
        Returns total number of embedded properties.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Property CSV file not found at: {csv_path}")

        documents = []
        metadatas = []
        ids = []

        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prop_id = str(row["id"])
                bhk = str(row.get("bhk", ""))
                prop_type = str(row.get("property_type", ""))
                location = str(row.get("location", ""))
                city = str(row.get("city", ""))
                price = str(row.get("price_lakh", ""))
                area = str(row.get("area_sqft", ""))
                trans_type = str(row.get("transaction_type", ""))
                amenities = str(row.get("amenities", ""))
                desc = str(row.get("description", ""))

                # Construct unified document text for vector search
                combined_text = (
                    f"{bhk} BHK {prop_type} in {location}, {city}. "
                    f"Price: {price} lakh. Area: {area} sqft. "
                    f"Type: {trans_type}. Amenities: {amenities}. {desc}"
                )

                metadata = {
                    "id": int(row["id"]),
                    "title": str(row.get("title", "")),
                    "location": location,
                    "city": city,
                    "price_lakh": float(row.get("price_lakh", 0.0)),
                    "property_type": prop_type,
                    "bhk": int(row.get("bhk", 0)),
                    "area_sqft": int(row.get("area_sqft", 0)),
                    "transaction_type": trans_type,
                    "amenities": amenities,
                    "availability": str(row.get("availability", "")),
                    "description": desc
                }

                documents.append(combined_text)
                metadatas.append(metadata)
                ids.append(prop_id)

        # Batch encode embeddings
        embeddings = self.model.encode(documents).tolist()

        # Upsert documents and embeddings into ChromaDB collection
        self.collection.upsert(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        return len(documents)

    def check_collection_size(self) -> int:
        """Returns total number of documents in ChromaDB collection."""
        return self.collection.count()
