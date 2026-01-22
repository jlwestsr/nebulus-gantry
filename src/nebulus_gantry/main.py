import os
from dotenv import load_dotenv

from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from chainlit.utils import mount_chainlit
from sqlalchemy.orm import Session
from sqlalchemy import func
from openai import AsyncOpenAI

from .database import init_db, migrate_db, UsageLog, get_db
# New import
from .backend.routes import chat_router
# Legacy imports
from .routers import auth_routes, notes_routes, workspace_routes, ltm_routes, debug_routes
# from .routers import chat_routes # Legacy

from .middleware import AuthMiddleware
from .ops.ollama import create_model, generate_modelfile
from .ui.pages import get_notes_page, get_workspace_page

# Load environment variables
load_dotenv()


# Import CHAINLIT_AUTH_SECRET if needed, or assume env
SECRET_KEY = os.environ.get("CHAINLIT_AUTH_SECRET", "supersecret-dev-key-change-me-in-prod")


class ThemeFlickerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Force identity encoding (no gzip) for all requests to ensure we can
        # intercept and modify the HTML body safely without dealing with decompression.
        # This is a bit of a hack, but safe for a local app.
        if "headers" in request.scope:
            new_headers = []
            for k, v in request.scope["headers"]:
                if k.decode("latin-1").lower() == "accept-encoding":
                    continue
                new_headers.append((k, v))
            request.scope["headers"] = new_headers

        response = await call_next(request)

        # Only intercept root HTML requests (Chainlit index)
        if request.url.path == "/" and response.headers.get("content-type", "").startswith("text/html"):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Blocking script to inject
            script = b"""
            <script>
                (function() {
                    try {
                        const localTheme = localStorage.getItem('vite-ui-theme');
                        const supportDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
                        if (localTheme === 'dark' || (!localTheme && supportDarkMode)) {
                            document.documentElement.classList.add('dark');
                        } else {
                            document.documentElement.classList.remove('dark');
                        }
                    } catch (e) {}
                })();
            </script>
            """

            # Inject before closing head
            if b"</head>" in body:
                body = body.replace(b"</head>", script + b"</head>", 1)

            # Remove content-length so it defaults to the new length
            headers = dict(response.headers)
            if "content-length" in headers:
                del headers["content-length"]

            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Database on startup
    init_db()
    migrate_db()
    yield

app = FastAPI(middleware=[
    Middleware(SessionMiddleware, secret_key=SECRET_KEY, https_only=False, session_cookie="gantry_session"),
    Middleware(ThemeFlickerMiddleware),
    Middleware(AuthMiddleware)
], lifespan=lifespan)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount(
    "/public", StaticFiles(directory=os.path.join(BASE_DIR, "public")), name="public"
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon_ico():
    return FileResponse(os.path.join(BASE_DIR, "public", "sidebar_logo.png"))


@app.get("/favicon", include_in_schema=False)
async def favicon_standard():
    return FileResponse(os.path.join(BASE_DIR, "public", "sidebar_logo.png"))


# Configure Ollama client for API
client = AsyncOpenAI(
    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11435") + "/v1",
    api_key="ollama",
)

MODEL_MAPPING = {
    "llama3.2-vision:latest": "Llama 3.2 Vision",
    "llama3.1:latest": "Llama 3.1",
    "qwen2.5-coder:latest": "Qwen 2.5 Coder",
}


@app.get("/models")
async def get_models():
    try:
        models = await client.models.list()
        raw_model_ids = [m.id for m in models.data]

        friendly_models = []
        for raw_id in raw_model_ids:
            if "embed" in raw_id:
                continue
            friendly_models.append(MODEL_MAPPING.get(raw_id, raw_id))

        return JSONResponse(content={"models": friendly_models, "raw": raw_model_ids})
    except Exception as e:
        return JSONResponse(
            content={"models": ["Llama 3.1"], "error": str(e)}, status_code=500
        )


@app.post("/api/models/create")
async def api_create_model(data: dict):
    try:
        name = data.get("name")
        base = data.get("base")
        system = data.get("system", "")
        params = data.get("parameters", {})

        if not name or not base:
            return JSONResponse(
                content={"error": "Name and Base Model are required"}, status_code=400
            )

        modelfile = generate_modelfile(base, system, params)
        result = await create_model(name, modelfile, base=base)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/metrics/usage")
async def get_usage_metrics(db: Session = Depends(get_db)):
    """
    Returns aggregated token usage metrics.
    """
    # Total tokens per model
    stats = (
        db.query(
            UsageLog.model,
            func.sum(UsageLog.prompt_tokens).label("prompt"),
            func.sum(UsageLog.completion_tokens).label("completion"),
            func.sum(UsageLog.total_tokens).label("total"),
            func.sum(UsageLog.cost).label("cost"),
        )
        .group_by(UsageLog.model)
        .all()
    )

    result = []
    for s in stats:
        result.append(
            {
                "model": s.model,
                "prompt_tokens": int(s.prompt or 0),
                "completion_tokens": int(s.completion or 0),
                "total_tokens": int(s.total or 0),
                "cost_micro": int(s.cost or 0),
            }
        )

    # Recent history
    recent = db.query(UsageLog).order_by(UsageLog.created_at.desc()).limit(10).all()

    recent_list = []
    for r in recent:
        recent_list.append(
            {
                "id": r.id,
                "model": r.model,
                "total_tokens": r.total_tokens,
                "timestamp": r.created_at.isoformat(),
            }
        )

    return {"summary": result, "recent": recent_list}


@app.get("/notes", response_class=HTMLResponse)
async def notes_page():
    return get_notes_page()


@app.get("/workspace", response_class=HTMLResponse)
async def workspace_page():
    return get_workspace_page()


# Include routers
app.include_router(auth_routes.router)
# app.include_router(chat_routes.router) # Legacy
app.include_router(chat_router.router)   # New Backend Router
app.include_router(notes_routes.router)
app.include_router(workspace_routes.router)
app.include_router(ltm_routes.router)
app.include_router(debug_routes.router)

# Mount Chainlit app on root
mount_chainlit(app=app, target=os.path.join(BASE_DIR, "chat.py"), path="/")
