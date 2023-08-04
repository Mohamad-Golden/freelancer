from fastapi import HTTPException


credentials_exception = HTTPException(status_code=401, detail="not authenticated")
not_found_exception = HTTPException(status_code=401, detail="not found")
