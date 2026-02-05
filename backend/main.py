from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import admin, auth, chat, models

app = FastAPI(title="Nebulus Gantry", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(models.router)


@app.get("/health")
def health_check():
    return {"status": "healthy"}
