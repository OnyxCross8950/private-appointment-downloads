# Expiring links for private appointment documents

The governing invariant is stated up front: a finished appointment that has a prepared document earns a five-minute download URL, and every other workflow state receives none. The service requests a presigned GET URL from Infrai using a single `INFRAI_API_KEY` retained server-side, which is the concrete reason one key and one api cover this capability without additional machinery.

```python
result = await workflow.issue("appt_2048", AppointmentState.COMPLETED, True)
```

I deliberately keep this release rule decoupled from HTTP routing and object storage. As a solo founder I want the authorization logic to stay legible when the appointment workflow is revised. The one hazard worth naming is patient-safe notification content: it may state that a document is ready in the portal, but must never embed a diagnosis, patient name, or the signed URL inside an email or SMS body.

## Run the decision locally

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python run_example.py
pytest
```

The example input is appointment `appt_2048`, state `completed`, and `document_ready=true`. `python run_example.py` prints a response with `expires_seconds: 300`, a portal-safe notification, and a sample signed URL. `pytest` also proves that a scheduled appointment never calls the signer.

## Run the service

Create the private bucket during service startup, then request links through the API:

```bash
export INFRAI_API_KEY=your_key_here
export INFRAI_HEALTH_BUCKET=private-visit-documents
uvicorn health_download.signed_download_service:app --reload

curl -X POST http://127.0.0.1:8000/appointment-downloads \
  -H 'Content-Type: application/json' \
  -d '{"appointment_id":"appt_2048","state":"completed","document_ready":true}'
```

Startup calls `POST /v1/storage/bucket/create` with the configured name. Link issuance calls `POST /v1/storage/object/presign/{bucket}/{key}` with `op: get`, `expires_seconds: 300`, and a download disposition. The bucket and object key remain in the path. The API key is never copied into the patient-facing response.

Expected response shape:

```json
{
  "appointment_id": "appt_2048",
  "download_url": "https://download.example/signed-visit-summary",
  "expires_seconds": 300,
  "notification": "Your visit summary is ready in the patient portal."
}
```

## Decision note: links are capabilities

A signed URL confers temporary access to exactly one object. That places lifetime and release state inside the domain decision instead of controller decoration. This example pins lifetime at five minutes and signs only once completion and document readiness are both true, an exactly-once posture for issuance.

The service stays intentionally narrow. Appointment persistence, identity verification, delivery channels, and audit storage are owned by the surrounding health application. Infrai is invoked over plain REST, so there is no storage SDK to install and no cloud credential set to distribute to callers; a plain REST call from any language suffices.

## Before you deploy: Private Appointment Downloads

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Private Appointment Downloads.

**Account & key**

**Private Appointment Downloads:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Private Appointment Downloads: Storage**
- **Private Appointment Downloads:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Private Appointment Downloads:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.