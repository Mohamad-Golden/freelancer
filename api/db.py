from sqlmodel import create_engine
from .settings import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        connection_string = f"postgresql://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@localhost:5432/{settings.DATABASE_NAME}"
        # sqlite_file_name = "database.db"
        # sqlite_url = f"sqlite:///{sqlite_file_name}"
        # connect_args = {"check_same_thread": False}
        _engine = create_engine(connection_string)
    return _engine
