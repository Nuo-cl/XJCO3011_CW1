import chromadb


class ChromaDBService:
    """Manages ChromaDB collections for semantic search over papers and notes."""

    def __init__(self, persist_directory='chroma_data', use_persistent=True):
        """Initialise ChromaDB client and collections.

        Args:
            persist_directory: Path for persistent storage.
            use_persistent: If False, use EphemeralClient (for tests).
        """
        if use_persistent:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.EphemeralClient()

        self.paper_collection = self.client.get_or_create_collection(
            name='paper_abstracts',
            metadata={'hnsw:space': 'cosine'},
        )
        self.notes_collection = self.client.get_or_create_collection(
            name='user_notes',
            metadata={'hnsw:space': 'cosine'},
        )

    def get_paper_collection(self):
        """Return the paper_abstracts collection."""
        return self.paper_collection

    def get_notes_collection(self):
        """Return the user_notes collection."""
        return self.notes_collection

    def add_paper(self, paper_id, abstract, metadata):
        """Add or update a paper abstract in the vector store."""
        self.paper_collection.upsert(
            ids=[f'paper_{paper_id}'],
            documents=[abstract],
            metadatas=[metadata],
        )

    def search_papers(self, query, n_results=10):
        """Semantic search over paper abstracts."""
        results = self.paper_collection.query(
            query_texts=[query],
            n_results=n_results,
        )
        return results

    def add_note(self, note_id, content, metadata):
        """Add or update a note in the vector store."""
        self.notes_collection.upsert(
            ids=[f'note_{note_id}'],
            documents=[content],
            metadatas=[metadata],
        )

    def update_note(self, note_id, content, metadata):
        """Update an existing note in the vector store."""
        self.add_note(note_id, content, metadata)

    def delete_note(self, note_id):
        """Remove a note from the vector store."""
        try:
            self.notes_collection.delete(ids=[f'note_{note_id}'])
        except Exception:
            pass

    def search_notes(self, query, user_id, n_results=10):
        """Semantic search over user notes, filtered by user_id."""
        results = self.notes_collection.query(
            query_texts=[query],
            n_results=n_results,
            where={'user_id': user_id},
        )
        return results

    def search_all(self, query, user_id=None, n_results=10):
        """Search across both papers and notes."""
        paper_results = self.search_papers(query, n_results=n_results)
        note_results = self.search_notes(query, user_id, n_results=n_results) if user_id else None
        return {
            'papers': paper_results,
            'notes': note_results,
        }
