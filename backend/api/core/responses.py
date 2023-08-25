from fastapi import HTTPException, status

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated"
)
not_found_exception = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="not found"
)
conflict_exception = HTTPException(
    status_code=status.HTTP_409_CONFLICT, detail="conflict exists"
)
invalid_data_exception = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST, detail="invalid data"
)
permission_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN, detail="permission denied"
)
server_exception = HTTPException(
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="server error"
)
