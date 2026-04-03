def test_note_model_creation(app, db, sample_user, sample_paper):
    """Note model can be created and linked to user and paper."""
    from app.models.note import Note
    note = Note(
        user_id=sample_user.id,
        paper_id=sample_paper.id,
        title='Test Note',
        content='This is a test note about transformers.',
    )
    db.session.add(note)
    db.session.commit()

    assert note.id is not None
    assert note.user_id == sample_user.id
    assert note.paper_id == sample_paper.id
