import pytest

from health_download.appointment_download import (
    AppointmentDownload,
    AppointmentState,
    DownloadDecisionError,
)


class RecordingSigner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def presign_download(self, **kwargs: object) -> dict[str, str]:
        self.calls.append(kwargs)
        return {"url": "https://signed.example/visit-summary"}


@pytest.mark.asyncio
async def test_completed_ready_appointment_gets_short_lived_link() -> None:
    signer = RecordingSigner()
    workflow = AppointmentDownload(bucket="private-docs", signer=signer)

    result = await workflow.issue("appt_2048", AppointmentState.COMPLETED, True)

    assert result["expires_seconds"] == 300
    assert result["notification"] == "Your visit summary is ready in the patient portal."
    assert signer.calls == [
        {
            "bucket": "private-docs",
            "key": "appointments/appt_2048/visit-summary.pdf",
            "expires_seconds": 300,
            "response_disposition": 'attachment; filename="visit-summary.pdf"',
        }
    ]


@pytest.mark.asyncio
async def test_scheduled_appointment_never_reaches_signer() -> None:
    signer = RecordingSigner()
    workflow = AppointmentDownload(bucket="private-docs", signer=signer)

    with pytest.raises(DownloadDecisionError):
        await workflow.issue("appt_2048", AppointmentState.SCHEDULED, True)

    assert signer.calls == []
