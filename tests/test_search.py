def test_chromadb_service_init():
    """ChromaDB service can be instantiated with ephemeral client."""
    from app.services.chromadb_service import ChromaDBService

    service = ChromaDBService(use_persistent=False)
    assert service.paper_collection is not None
    assert service.notes_collection is not None
