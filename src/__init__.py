from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import create_tables
from . import appointment_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("app is starting")
    create_tables()
    print("tables created")
    yield
    print("app is shutting down")


def create_app():
    app = FastAPI(
        title="idk",
        description="Healthcare Appointment Scheduling System",
        lifespan=lifespan
    )

    # ✅ CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # React
            "http://127.0.0.1:3000"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        appointment_service.router,
        prefix=""
    )

    return app

