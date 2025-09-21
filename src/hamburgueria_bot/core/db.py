
"""Factory de sessão do SQLAlchemy 2."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def create_session_factory(database_url: str):
    """Cria SessionFactory síncrona para SQLAlchemy 2.

    :param database_url: URL completa do banco (psycopg3).
    :return: sessionmaker configurado.
    """
    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
