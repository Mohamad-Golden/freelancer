from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi

# for landing page
from fastapi import Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from pathlib import Path
from .settings import settings
from .core.router import admin_router
from .core.router import router
from .core.router import authenticated_router
from .core import models
from .db import get_engine


BASE_DIR = Path(__file__).resolve().parent


def create_db_and_tables():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_application():
    create_db_and_tables()
    _app = FastAPI()
    apiRouter = APIRouter()
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # templates = Jinja2Templates(directory="templates/")
    # _app.mount("/static", StaticFiles(directory="templates/static"), name="static")

    try:
        _app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    except:
        pass
    apiRouter.include_router(router)
    apiRouter.include_router(authenticated_router, tags=["Auth Required"])
    apiRouter.include_router(admin_router, tags=["Admin"])
    _app.include_router(apiRouter)

    return _app


app = get_application()
