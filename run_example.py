import asyncio

from health_download.appointment_download import AppointmentDownload, AppointmentState


class PreviewSigner:
    async def presign_download(self, **_: object) -> dict[str, str]:
        return {"url": "https://signed.example/visit-summary"}


async def main() -> None:
    workflow = AppointmentDownload(bucket="private-docs", signer=PreviewSigner())
    print(await workflow.issue("appt_2048", AppointmentState.COMPLETED, True))


if __name__ == "__main__":
    asyncio.run(main())
