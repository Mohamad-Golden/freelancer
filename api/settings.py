from functools import lru_cache
from pydantic import BaseSettings
from dotenv import load_dotenv
import os

# if .env file exists, get the environment variables from there,
# else from actual environment variabls
load_dotenv(override=True)


class Settings(BaseSettings):
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    SESSION_KEY: str = os.environ["SESSION_KEY"]
    URL_PREFIX: str = os.environ["URL_PREFIX"]

    class Config:
        env_file = ".env"


@lru_cache()
def get_setting():
    settings = Settings()
    return settings


settings = get_setting()
