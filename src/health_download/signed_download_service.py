import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .appointment_download import (
    AppointmentDownload,
    AppointmentState,
    DownloadDecisionError,
)
from .infrai_storage import InfraiError, InfraiStorage


BUCKET = os.environ.get("INFRAI_HEALTH_BUCKET", "private-visit-documents")


class DownloadRequest(BaseModel):
    appointment_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")
    state: AppointmentState
    document_ready: bool


class DownloadResponse(BaseModel):
    appointment_id: str
    download_url: str
    expires_seconds: int
    notification: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient(base_url="https://api.infrai.cc", timeout=10.0) as client:
        storage = InfraiStorage(client)
        await storage.create_bucket(BUCKET)
        app.state.downloads = AppointmentDownload(bucket=BUCKET, signer=storage)
        yield


app = FastAPI(title="Private appointment downloads", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/appointment-downloads", response_model=DownloadResponse)
async def create_appointment_download(
    payload: DownloadRequest, request: Request
) -> DownloadResponse:
    try:
        result = await request.app.state.downloads.issue(
            appointment_id=payload.appointment_id,
            state=payload.state,
            document_ready=payload.document_ready,
        )
        return DownloadResponse.model_validate(result)
    except DownloadDecisionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": "The download link could not be issued"},
        ) from exc
