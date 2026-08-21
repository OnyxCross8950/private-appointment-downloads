from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol


class AppointmentState(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DownloadDecisionError(ValueError):
    pass


class StorageSigner(Protocol):
    async def presign_download(
        self,
        bucket: str,
        key: str,
        expires_seconds: int,
        response_disposition: str,
    ) -> dict[str, Any]:
        raise AssertionError("protocol methods are not called directly")


@dataclass(frozen=True)
class AppointmentDownload:
    bucket: str
    signer: StorageSigner
    link_lifetime_seconds: int = 300

    async def issue(
        self,
        appointment_id: str,
        state: AppointmentState,
        document_ready: bool,
    ) -> dict[str, str | int]:
        if state is not AppointmentState.COMPLETED or not document_ready:
            raise DownloadDecisionError("The appointment document is not ready for release")

        object_key = f"appointments/{appointment_id}/visit-summary.pdf"
        signed = await self.signer.presign_download(
            bucket=self.bucket,
            key=object_key,
            expires_seconds=self.link_lifetime_seconds,
            response_disposition='attachment; filename="visit-summary.pdf"',
        )
        return {
            "appointment_id": appointment_id,
            "download_url": str(signed["url"]),
            "expires_seconds": self.link_lifetime_seconds,
            "notification": "Your visit summary is ready in the patient portal.",
        }
