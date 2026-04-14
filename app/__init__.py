from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flasgger import Flasgger

from app.config import DevelopmentConfig, TestingConfig, ProductionConfig

db = SQLAlchemy()
jwt = JWTManager()

config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def create_app(config_name='development'):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    jwt.init_app(app)
    CORS(app)
    Flasgger(app)

    from app.routes.auth import auth_bp
    from app.routes.papers import papers_bp
    from app.routes.notes import notes_bp
    from app.routes.search import search_bp
    from app.routes.recommendations import recommendations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(papers_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(recommendations_bp)

    from app.utils.errors import register_error_handlers
    register_error_handlers(app)

    # Initialise ChromaDB service
    from app.services.chromadb_service import ChromaDBService
    chromadb_service = ChromaDBService(
        persist_directory=app.config.get('CHROMADB_DIR', 'chroma_data'),
        use_persistent=app.config.get('CHROMADB_PERSIST', True),
    )
    app.extensions['chromadb'] = chromadb_service

    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'ok',
            'message': 'ScholarTrack API is running'
        })

    with app.app_context():
        from app import models  # noqa: F401 — ensure all models are registered
        db.create_all()

    return app
