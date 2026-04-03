def test_flashcard_model_creation(app, db, sample_user, sample_paper):
    """Flashcard model can be created with SM-2 defaults."""
    from app.models.note import Note
    from app.models.flashcard import Flashcard

    note = Note(
        user_id=sample_user.id,
        paper_id=sample_paper.id,
        title='Test Note',
        content='Content for flashcard test.',
    )
    db.session.add(note)
    db.session.commit()

    card = Flashcard(
        user_id=sample_user.id,
        note_id=note.id,
        question='What is self-attention?',
        answer='A mechanism that relates different positions of a sequence.',
    )
    db.session.add(card)
    db.session.commit()

    assert card.id is not None
    assert card.ease_factor == 2.5
    assert card.interval == 1
    assert card.repetitions == 0
