# Smart Doctor

A hospital scheduling assistant. Patients chat with an LLM that looks up doctors,
reads appointment history and books visits through an MCP server.

## Layout

```
backend/
  mcp_server.py     MCP server, exposes the scheduling tools and the history resource
  mcp_client.py     stdio client the API uses to reach the server
  services.py       booking, lookup and cancellation logic
  chat.py           chat endpoint, discovers its tools from the MCP server
  main.py           FastAPI app the frontend talks to
frontend/           React chat UI
```

The scheduling logic lives in `services.py` and has exactly two callers: the MCP
tools and the HTTP routes. Neither keeps its own copy.

## Running the backend

```
cd backend
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
python seed.py
uvicorn main:app --reload
```

The API starts the MCP server itself as a subprocess, so nothing else is needed.
`GET /` reports whether that connection came up.

`backend/.env` holds the configuration:

```
GROQ_API_KEY=your-key
DATABASE_URL=sqlite:///./health_assistant.db
ALLOWED_ORIGINS=http://localhost:5173
```

## Running the frontend

```
cd frontend
npm install
npm run dev
```

## Using the MCP server from another host

The server also runs standalone over stdio, so any MCP host can use it:

```
python backend/mcp_server.py
```

To register it with Claude Desktop, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "smart-doctor": {
      "command": "python",
      "args": ["C:/Projects/smart-doctor/backend/mcp_server.py"]
    }
  }
}
```

Tools:

| Tool | Does |
| --- | --- |
| `list_doctors` | every doctor and their specialty |
| `list_patient_appointments` | a patient's appointments |
| `book_appointment` | book a slot, rejecting clashes |
| `cancel_appointment` | cancel by id |
| `add_medical_record` | record a condition, allergy, surgery or note |
| `list_medical_records` | read history, optionally by category |
| `delete_medical_record` | remove an entry |
| `add_prescription` | record a medication with dosage and frequency |
| `list_prescriptions` | medications, optionally active only |
| `stop_prescription` | mark a medication as no longer taken |
| `list_photo_drafts` | photos waiting for the patient to confirm |
| `get_photo_draft` | read what was extracted from one photo |
| `confirm_photo_draft` | save a draft the patient has approved |
| `discard_photo_draft` | throw a draft away unsaved |

Resource: `appointment://patient/{patient_id}/history`, which returns allergies,
conditions, medications and appointments as one summary an LLM can read in a
single call.

## Medical history and prescriptions

Patients build their own record, either by talking to the assistant or through
the API directly:

```
POST   /records/history                        add a condition, allergy, surgery or note
GET    /records/history/{patient_id}           read it back, filter with ?category=allergy
DELETE /records/history/{record_id}            remove an entry
POST   /records/prescriptions                  add a medication
GET    /records/prescriptions/{patient_id}     list them, filter with ?active_only=true
POST   /records/prescriptions/{id}/stop        mark a medication as stopped
GET    /records/summary/{patient_id}           the whole record as readable text
```

History entries are one of four categories: `condition`, `allergy`, `surgery` or
`note`. Prescriptions carry a dosage, a frequency and an optional prescribing
doctor, and are never deleted, only stopped, so the record stays honest about
what someone used to take.

The assistant reads all of this before it answers, which is what makes the
allergy list worth having.

## Photos

A patient can photograph a prescription or discharge note and have the details
read out of it:

```
POST /records/photos                     multipart upload: patient_id + file
GET  /records/photos/pending/{patient}   drafts still waiting on confirmation
GET  /records/photos/draft/{photo_id}    one draft
GET  /records/photos/image/{photo_id}    the original image
POST /records/photos/{photo_id}/confirm  save the approved items
POST /records/photos/{photo_id}/discard  throw the draft away
```

Uploading extracts, it does not save. The response is a draft of the medications
and history entries found in the image, and the record is only written when the
patient confirms. The confirm body may contain edited items, so a patient can fix
a misread dosage or drop a line before anything is stored. Items that match
something already on file come back flagged `already_on_file` so nobody confirms
the same prescription twice.

This matters because vision models misread handwriting, and a dosage that reads
`5mg` as `50mg` is not a bug you want to find later. The assistant is instructed
to read the draft back item by item and never confirm on the patient's behalf.
Text inside an image is treated as data to report, never as instructions to
follow.

Images accept PNG, JPEG and WebP up to 8MB, and are written to `backend/uploads`.
That directory is local disk, so on a platform with an ephemeral filesystem the
images do not survive a redeploy even though the extracted records do.

## A note on access control

There is no authentication yet. Any caller can read or book against any
`patient_id`, which needs solving before this handles real patient data.
