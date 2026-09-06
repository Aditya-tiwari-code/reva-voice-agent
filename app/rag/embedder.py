# Embed property data into ChromaDB

class PropertyEmbedder:
    """
    Ingests property CSV datasets and indexes listings into ChromaDB vector store.
    """
    def __init__(self, db_path: str = "./chroma_db"):
        self.db_path = db_path

    def index_properties(self, csv_filepath: str):
        """
        Reads CSV and adds vector embeddings to ChromaDB collection.
        """
        pass
