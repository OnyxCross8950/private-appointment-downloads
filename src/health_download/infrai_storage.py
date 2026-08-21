import asyncio
import os
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return self.code


class InfraiStorage:
    def __init__(self, client: httpx.AsyncClient, api_key: str | None = None) -> None:
        self.client = client
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]

    async def _call(
        self, method: str, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        for attempt in range(4):
            response = await self.client.request(
                method=method,
                url=path,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt < 3:
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "request_rejected")),
                    detail=error,
                    status_code=response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {}

        raise RuntimeError("retry loop ended unexpectedly")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = parsedate_to_datetime(retry_after)
                return max(0.0, retry_at.timestamp() - __import__("time").time())
        return float(2**attempt)

    async def create_bucket(self, name: str) -> dict[str, Any]:
        return await self._call(
            method="POST",
            path="/v1/storage/bucket/create",
            body={"name": name},
        )

    async def presign_download(
        self,
        bucket: str,
        key: str,
        expires_seconds: int,
        response_disposition: str,
    ) -> dict[str, Any]:
        # infrai.storage.object.presign keeps credentials on the service side.
        safe_bucket = quote(bucket, safe="")
        safe_key = quote(key, safe="")
        return await self._call(
            method="POST",
            path=f"/v1/storage/object/presign/{safe_bucket}/{safe_key}",
            body={
                "op": "get",
                "expires_seconds": expires_seconds,
                "response_disposition": response_disposition,
            },
        )
