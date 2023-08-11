from fastapi import HTTPException


credentials_exception = HTTPException(status_code=401, detail="not authenticated")
not_found_exception = HTTPException(status_code=404, detail="not found")
conflict_exception = HTTPException(status_code=409, detail="conflict exists")
invalid_data_exception = HTTPException(status_code=400, detail="invalid data")
permission_exception = HTTPException(status_code=403, detail="permission denied")
