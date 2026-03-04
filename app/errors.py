# Description: Utility function to create standardized HTTP error responses in FastAPI. Coded by LF using copilot inline additions, Copilot added comments afterwards.
from fastapi import HTTPException

def http_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    """Return an HTTPException with a standardized error payload shape."""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": {
                "code": code,
                "message": message,
                "details": details or {}
            }
        }
    )
    