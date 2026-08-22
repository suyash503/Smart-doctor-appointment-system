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

## A note on access control

There is no authentication yet. Any caller can read or book against any
`patient_id`, which needs solving before this handles real patient data.
