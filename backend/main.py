from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.routers import admin, auth, chat, documents, models, overlord, personas
from backend.services.chroma_pool import close_chroma_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_chroma_client()
    admin.shutdown_docker_service()


app = FastAPI(title="Nebulus Gantry", version="2.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Routers
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(models.router)
app.include_router(overlord.router)
app.include_router(personas.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
