from enum import Enum


class PlanEnum(str, Enum):
    free = "free"
    bronze = "bronze"
    gold = "gold"
    diamond = "diamond"


class RoleEnum(str, Enum):
    freelancer = "freelancer"
    employer = "employer"
    admin = "admin"


class GeneralRole(str, Enum):
    admin = "admin"
    freelancer = "freelancer"
    employer = "employer"


class ProjectStatusEnum(str, Enum):
    done = "done"
    unassigned = "unassigned"
    assigned = "assigned"


class SortEnum(str, Enum):
    date = "created_at"
    price = "price_to"

class SortRequestEnum(str, Enum):
    date = 'created_at'
    response = 'responded_at'

class UserSortEnum(str, Enum):
    date = 'created_at'

class SortDirEnum(str, Enum):
    ascending = "asc"
    descending = "desc"

class RequestType(str, Enum):
    verification = 'verification'