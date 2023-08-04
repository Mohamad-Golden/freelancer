from sqlmodel import create_engine

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        sqlite_file_name = "database.db"
        sqlite_url = f"sqlite:///{sqlite_file_name}"
        connect_args = {"check_same_thread": False}
        _engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)
    return _engine
