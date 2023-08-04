from enum import Enum


class PlanEnum(str, Enum):
    free = "free"
    bronze = "bronze"
    gold = "gold"
    diamond = "diamond"


class RoleEnum(str, Enum):
    freelancer = "freelancer"
    employer = "employer"


class GeneralRole(str, Enum):
    admin = "admin"
    freelancer = "freelancer"
    employer = "employer"
