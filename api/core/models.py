from sqlmodel import SQLModel, Field, Relationship, Session
from pydantic import EmailStr
from typing import Optional, List
from .types import RoleEnum, PlanEnum
from datetime import datetime, timedelta
import string
import secrets


class UserBase(SQLModel):
    email: EmailStr = Field(unique=True)


class UserLogin(UserBase):
    password: str


class UserCreate(UserLogin):
    role: RoleEnum


class UserTechnology(SQLModel, table=True):
    technology_id: Optional[int] = Field(
        default=None, foreign_key="technology.id", primary_key=True
    )
    # technology: Technology = Relationship()
    user_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    # user: User = Relationship()


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: Optional[int] = Field(default=None, foreign_key="plan.id")
    plan: Optional["Plan"] = Relationship()
    hashed_password: str = Field(default=None, max_length=32)
    role_id: Optional[int] = Field(foreign_key="role.id")
    role: Optional["Role"] = Relationship()
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    offers: List["Offer"] = Relationship(back_populates="offerer")
    is_verified: bool = False
    technologies: List["Technology"] = Relationship(link_model=UserTechnology)


class UserOut(UserBase):
    id: int


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    users: List[User] = Relationship()


class Role(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    users: List[User] = Relationship()


class ProjectIn(SQLModel):
    title: str
    description: Optional[str] = None
    price_from: int
    price_to: int
    technologies_id: List[int] = None


class OfferOut(SQLModel):
    offer_price: int
    duration_day: int
    # offerer: UserOut


class ProjectBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    price_from: int
    price_to: int
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: "User" = Relationship()
    doer_id: Optional[int] = Field(foreign_key="user.id")
    doer: Optional["User"] = Relationship()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expire_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=15)
    )
    finished_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    deadline_until: Optional[datetime] = None


class ProjectOut(SQLModel):
    offers: List[OfferOut] = None


class Model(SQLModel):
    a: str


class Model2(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    b: List[Model]


class Project(ProjectBase, table=True):
    offers: List["Offer"] = Relationship(back_populates="project")
    # technologies: List['Technology'] = Relationship(link_model='ProjectTechnology')


class Technology(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str


class ProjectTechnology(SQLModel, table=True):
    technology_id: Optional[int] = Field(
        default=None, foreign_key="technology.id", primary_key=True
    )
    technology: Technology = Relationship()
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    project: Project = Relationship()


class UserVerificationCode(SQLModel, table=True):
    code: str = Field(
        default_factory=lambda: "".join(secrets.choice(string.digits) for _ in range(6)),
        primary_key=True,
    )
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship()
    expire_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=5), nullable=False
    )


class ResetPasswordToken(SQLModel, table=True):
    token: str = Field(default=lambda: secrets.token_hex, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship()
    expire_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=5)
    )


class Offer(SQLModel, table=True):
    offerer_id: Optional[int] = Field(
        default=None, foreign_key="user.id", primary_key=True
    )
    offerer: User = Relationship()
    project_id: Optional[int] = Field(
        default=None, foreign_key="project.id", primary_key=True
    )
    project: Project = Relationship(back_populates="offers")
    offer_price: int
    duration_day: int
