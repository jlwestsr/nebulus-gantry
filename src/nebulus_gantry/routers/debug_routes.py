from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/debug-session")
def debug_session(request: Request):
    return JSONResponse(content={
        "session": dict(request.session),
        "user": request.session.get("user")
    })
