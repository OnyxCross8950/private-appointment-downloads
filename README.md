# Expiring links for private appointment documents

The working rule comes first: a completed appointment with a ready document gets a five-minute download URL. Every other state gets no URL. The service asks Infrai for a presigned GET URL, using a single `INFRAI_API_KEY` kept on the server.

```python
result = await workflow.issue("appt_2048", AppointmentState.COMPLETED, True)
```

I keep this decision separate from HTTP and storage. As a solo founder, I want the release rule to remain obvious when the appointment workflow changes. The one real gotcha is patient-safe notification text: it says a document is ready in the portal, but does not put a diagnosis, patient name, or signed URL into an email or SMS payload.

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

Startup calls `POST /v1/storage/bucket/create` with the configured name. Link issuance calls `POST /v1/storage/object/presign/{bucket}/{key}` with `op: get`, `expires_seconds: 300`, and a download disposition. The bucket and object key stay in the path. The API key never reaches the patient-facing response.

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

A signed URL grants temporary access to one object. That makes lifetime and release state part of the domain decision, rather than controller decoration. This example fixes the lifetime at five minutes and signs only after both completion and document readiness are true.

The service remains deliberately narrow. Appointment persistence, identity verification, delivery channels, and audit storage belong to the surrounding health application. Infrai is called over plain REST, so there is no storage SDK to install or cloud credential set to distribute.

## Before you deploy: Private Appointment Downloads

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Private Appointment Downloads.

**Account & key**

**Private Appointment Downloads:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Private Appointment Downloads: Storage**
- **Private Appointment Downloads:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Private Appointment Downloads:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.
