from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.material.router import router as material_router
from app.script.router import router as script_router
from app.creation.router import router as creation_router
from app.user.router import router as user_router
from app.workers.router import router as workflow_router
from app.reference.router import router as reference_router
from app.template.router import router as template_router

# ── 初始化日志 ──────────────────────────
from app.core.logging import setup_logging
setup_logging()

app = FastAPI(title="Video-AI API", version="0.1.0", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(material_router)
app.include_router(script_router)
app.include_router(creation_router)
app.include_router(user_router)
app.include_router(workflow_router)
app.include_router(reference_router)
app.include_router(template_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
