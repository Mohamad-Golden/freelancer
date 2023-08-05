from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi

# for landing page
from fastapi import Request, Depends, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi_utils.inferring_router import InferringRouter
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, Session
from pathlib import Path
from .settings import settings
from .core.router import admin_router
from .core.router import router
from .core.router import authenticated_router
from .core.models import User, Role, Plan
from .db import get_engine


BASE_DIR = Path(__file__).resolve().parent


def create_db_and_tables():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def startup():
    engine = get_engine()
    with Session(engine) as session:
        admin = Role(title="admin")
        freelancer = Role(title="freelancer")
        employer = Role(title="employer")
        session.add(admin)
        session.add(freelancer)
        session.add(employer)
        free = Plan(title="free")
        bronze = Plan(title="bronze")
        gold = Plan(title="gold")
        diamond = Plan(title="diamond")
        session.add(free)
        session.add(bronze)
        session.add(gold)
        session.add(diamond)
        session.commit()


def get_application():
    create_db_and_tables()
    # startup()
    _app = FastAPI(
        openapi_url=settings.URL_PREFIX + "/openapi.json",
        docs_url=settings.URL_PREFIX + "/docs",
    )
    apiRouter = InferringRouter(prefix=settings.URL_PREFIX)
    # _app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=[],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )
    # templates = Jinja2Templates(directory="templates/")
    # _app.mount("/static", StaticFiles(directory="templates/static"), name="static")

    try:
        _app.mount(
            settings.URL_PREFIX + "/uploads",
            StaticFiles(directory="uploads"),
            name="uploads",
        )
    except:
        pass
    apiRouter.include_router(router)
    apiRouter.include_router(authenticated_router, tags=["Auth Required"])
    apiRouter.include_router(admin_router, tags=["Admin"])
    _app.include_router(apiRouter)

    return _app


app = get_application()
