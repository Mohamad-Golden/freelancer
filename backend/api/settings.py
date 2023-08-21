import os
from functools import lru_cache
from pathlib import Path, PosixPath

from dotenv import load_dotenv
from pydantic import BaseSettings

_base_dir = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_base_dir / ".env", override=True)

class Settings(BaseSettings):
    SESSION_KEY: str = os.environ["SESSION_KEY"]
    URL_PREFIX: str = os.environ["URL_PREFIX"]
    POSTGRES_USERNAME: str = os.environ["POSTGRES_USERNAME"]
    POSTGRES_PASSWORD: str = os.environ["POSTGRES_PASSWORD"]
    DATABASE_NAME: str = os.environ["DATABASE_NAME"]
    MAIL_SERVER: str = os.environ["MAIL_SERVER"]
    MAIL_USERNAME: str = os.environ["MAIL_USERNAME"]
    MAIL_PASSWORD: str = os.environ["MAIL_PASSWORD"]
    MAIL_PORT: str = int(os.environ["MAIL_PORT"])
    BASE_DIR: PosixPath = _base_dir
    DATA_PATH: str = "data"


@lru_cache()
def get_setting():
    settings = Settings()
    return settings


settings = get_setting()
settings = get_setting()
