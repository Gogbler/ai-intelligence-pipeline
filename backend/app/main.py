"""Main FastAPI Application Entrypoint.

FrontierAtlas AI Intelligence Graph Platform.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.database.session import init_db
from app.api.routes import router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Scalable, fault-tolerant ingestion pipeline for AI startups, products, research papers, news, and jobs.",
)

# Enable CORS for React frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

# Mount frontend dist static files if built
frontend_dist = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
)

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/")
    def serve_frontend_root():
        return FileResponse(os.path.join(frontend_dist, "index.html"))

    @app.get("/dashboard")
    def serve_dashboard():
        return FileResponse(os.path.join(frontend_dist, "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "platform": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs_url": "/docs",
            "api_stats": "/api/stats",
            "status": "OPERATIONAL",
        }


@app.on_event("startup")
def on_startup():
    init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
