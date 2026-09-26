from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router
from app.api.bob import router as bob_router
from app.mcp.server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"⚡ {settings.APP_NAME} API starting...")
    print(f"Environment: {settings.APP_ENV}")

    async with mcp.session_manager.run():
        yield

    print("Ripple API shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.RIPPLE_VERSION,
    description=(
        "Ripple is an AI-powered developer workflow for understanding "
        "the impact of code changes before they are made."
    ),
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(
    router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    bob_router,
    prefix=settings.API_PREFIX,
)


app.mount(
    "/mcp",
    mcp.streamable_http_app(
        streamable_http_path="/",
    ),
)


@app.get("/")
async def root():
    return {
        "name": "Ripple",
        "version": settings.RIPPLE_VERSION,
        "status": "online",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ripple-api",
    }




