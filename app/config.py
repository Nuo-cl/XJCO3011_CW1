import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    CHROMADB_DIR = 'chroma_data'
    CHROMADB_PERSIST = True
    SWAGGER = {
        'title': 'ScholarTrack API',
        'uiversion': 3,
        'description': 'A RESTful API for researchers to track arXiv papers, manage research notes, and use spaced repetition learning.',
        'version': '1.0.0',
        'termsOfService': '',
        'specs_route': '/apidocs/',
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'JWT Bearer token. Format: "Bearer {token}"',
            },
        },
    }


class DevelopmentConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///dev.db'
    DEBUG = True


class TestingConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    TESTING = True
    CHROMADB_PERSIST = False


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///prod.db'
