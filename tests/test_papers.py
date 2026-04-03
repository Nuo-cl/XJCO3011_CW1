def test_paper_model_creation(app, db, sample_paper):
    """Paper model can be created and queried."""
    from app.models.paper import Paper
    paper = Paper.query.filter_by(arxiv_id='2401.12345').first()
    assert paper is not None
    assert paper.title == 'Attention Is All You Need Revisited'
    assert 'cs.CL' in paper.categories
