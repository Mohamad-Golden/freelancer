import hashlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from fastapi_utils.inferring_router import InferringRouter
from sqlmodel import Session, SQLModel

from .core.models import Plan, Role, Status, User
from .core.router import admin_router, authenticated_router, router
from .db import get_engine
from .settings import settings


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
        free = Plan(title="free", offer_number=5)
        bronze = Plan(title="bronze", duration_day=30, offer_number=50)
        gold = Plan(title="gold", duration_day=60, offer_number=150)
        diamond = Plan(title="diamond", duration_day=90, offer_number=350)
        user = User(
            email="user@example.com",
            hashed_password=hashlib.md5(b"string").hexdigest(),
            role=admin,
            plan=free,
            offer_left=free.offer_number,
            is_verified=True,
            is_email_verified=True,
        )
        unassigned = Status(title="unassigned")
        assigned = Status(title="assigned")
        done = Status(title="done")
        session.add(unassigned)
        session.add(done)
        session.add(assigned)
        session.add(user)
        session.add(free)
        session.add(bronze)
        session.add(gold)
        session.add(diamond)
        session.commit()


def get_application():
    # create_db_and_tables()
    # startup()
    _app = FastAPI(
        openapi_url=settings.URL_PREFIX + "/openapi.json",
    )

    def custom_openapi():
        if _app.openapi_schema:
            return _app.openapi_schema
        openapi_schema = get_openapi(
            title="Freelancer Api Documentation",
            version="1.0.0",
            description="Use login route to authorize",
            routes=_app.routes,
        )
        _app.openapi_schema = openapi_schema
        return _app.openapi_schema

    _app.openapi = custom_openapi
    apiRouter = InferringRouter(prefix=settings.URL_PREFIX)

    @apiRouter.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=_app.openapi_url,
            title=_app.title + " - Swagger UI Freelancer",
            oauth2_redirect_url=_app.swagger_ui_oauth2_redirect_url,
            swagger_ui_parameters={"docExpansion": None},
        )

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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
    apiRouter.include_router(router, tags=["Unauthenticated"])
    apiRouter.include_router(authenticated_router, tags=["Authenticated"])
    apiRouter.include_router(admin_router, tags=["Admin"])
    _app.include_router(apiRouter)

    return _app


app = get_application()
