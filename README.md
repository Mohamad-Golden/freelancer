# Freelancer
## Simple version of a freelancing website

### run
uvicorn api.main:app --reload

## Used technologies
* Fastapi
* Uvicorn
* Pydantic
* Sqlmodel
* Postgresql
* Alembic
* Web socket
* SMTP
* JWT


## Basic features
* User validation by email
* Resetting password by email
* Creating resume
* Posting a project by employer
* Finding projects easily based on freelancer's skills
* Premium plans
* Real time chat


_Project uses single folder structure for simplicity._
_Also it's not using async due to sqlmodel lack of good support at the time of writing the project._
