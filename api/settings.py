from functools import lru_cache
from pydantic import BaseSettings
from dotenv import load_dotenv
import os
from pathlib import Path, PosixPath

# if .env file exists, get the environment variables from there,
# else from actual environment variables
load_dotenv(override=True)


class Settings(BaseSettings):
    SESSION_KEY: str = os.environ["SESSION_KEY"]
    URL_PREFIX: str = os.environ["URL_PREFIX"]
    POSTGRES_USERNAME: str = os.environ["POSTGRES_USERNAME"]
    POSTGRES_PASSWORD: str = os.environ["POSTGRES_PASSWORD"]
    DATABASE_NAME: str = os.environ["DATABASE_NAME"]
    BASE_DIR: PosixPath =  Path(__file__).resolve().parent.parent
    DATA_PATH: str = 'data'
    

@lru_cache()
def get_setting():
    settings = Settings()
    return settings


settings = get_setting()
