# 🏥 Smart Doctor Appointment & Reporting Assistant

An intelligent, full-stack medical scheduling assistant powered by Agentic AI and the Model Context Protocol (MCP). This application allows patients to book appointments, keep their own medical history, and query doctor availability using natural language, seamlessly translating conversational intent into strict database operations.

## 🚀 Live Demo
**Access the live application here:** [Smart Doctor AI](https://smart-doctor-ai.vercel.app/)

*Note: The backend is hosted on a free Render instance. If the application has not been used in the last 15 minutes, the server will go to sleep. **The first message you send may take 30–50 seconds to process** while the server wakes up. Subsequent messages will be instant.*

## 🧠 Core Architecture
This project implements a true Agentic Loop, where an LLM is granted autonomous access to backend tools to fulfill user requests.

* **Frontend:** React, Vite, and custom CSS for a ChatGPT-style conversational interface. Hosted on Vercel.
* **Backend:** FastAPI (Python) implementing modular routing and MCP tool exposure. Hosted on Render.
* **MCP Server:** A standalone `FastMCP` server over stdio. The chat endpoint is an MCP *client* — it discovers the tools at runtime rather than hardcoding them.
* **Database:** SQLite with SQLAlchemy ORM.
* **Data Validation:** Pydantic schemas ensure the LLM cannot hallucinate or inject malformed data into the database.
* **AI Agent:** Groq API. `openai/gpt-oss-120b` for reasoning and tool calling, `qwen/qwen3.6-27b` for reading uploaded photos.
* **Memory:** Multi-turn conversational memory persisted via session IDs.

### How the pieces fit

```
backend/
  mcp_server.py     MCP server: the scheduling and record tools, plus a history resource
  mcp_client.py     stdio client the API uses to reach that server
  services.py       booking, records, prescriptions and photo-draft logic
  extraction.py     reads medicines and conditions out of an image
  chat.py           chat endpoint, discovers its tools from the MCP server
  main.py           FastAPI app the frontend talks to
frontend/           React chat UI
```

All domain logic lives in `services.py` and has exactly two callers: the MCP tools and the HTTP routes. Neither keeps its own copy, so the two can't drift apart.

## ⚡ Features
* **Natural Language Processing:** Users can type complex requests (e.g., "I need to see Dr. House tomorrow at 10 AM for a severe headache").
* **Autonomous Tool Execution:** The AI parses the prompt, decides which tool to use, and executes the SQL queries.
* **Runtime Tool Discovery:** Tools are listed over MCP and converted to the model's function-calling format on the fly — adding a tool to the MCP server is enough to make the agent aware of it.
* **Medical History & Prescriptions:** Patients record conditions, allergies, surgeries and medications. The agent checks allergies and current medicines before answering anything treatment-adjacent.
* **Photo Extraction:** Photograph a prescription and have the medicines, conditions and allergies read out of it — behind a confirmation step (see below).
* **Multi-Turn Memory:** The agent remembers previous context within the same session.
* **Strict Schema Enforcement:** Backend refuses any AI requests that do not match the strict Pydantic database models, and rejects double-booking a doctor.

## 🧰 MCP Tools

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

Resource: `appointment://patient/{patient_id}/history` — allergies, conditions, medications and appointments as one summary the model can read in a single call.

The server also runs standalone over stdio, so any MCP host can use it:

```bash
python backend/mcp_server.py
```

To register it with Claude Desktop, add this to `claude_desktop_config.json`:

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

## 📋 Medical History & Prescriptions

Patients build their own record, either by talking to the assistant or through the API:

```
POST   /records/history                        add a condition, allergy, surgery or note
GET    /records/history/{patient_id}           read it back, filter with ?category=allergy
DELETE /records/history/{record_id}            remove an entry
POST   /records/prescriptions                  add a medication
GET    /records/prescriptions/{patient_id}     list them, filter with ?active_only=true
POST   /records/prescriptions/{id}/stop        mark a medication as stopped
GET    /records/summary/{patient_id}           the whole record as readable text
```

History entries are one of `condition`, `allergy`, `surgery` or `note`. Prescriptions are never deleted, only stopped, so the record stays honest about what someone used to take.

## 📷 Photo Extraction

```
POST /records/photos                     multipart upload: patient_id + file
GET  /records/photos/pending/{patient}   drafts still waiting on confirmation
GET  /records/photos/draft/{photo_id}    one draft
GET  /records/photos/image/{photo_id}    the original image
POST /records/photos/{photo_id}/confirm  save the approved items
POST /records/photos/{photo_id}/discard  throw the draft away
```

**Uploading extracts, it does not save.** The response is a draft of the medications and history entries found in the image, and the record is only written when the patient confirms. The confirm body may carry edited items, so a misread dosage can be fixed or a line dropped before anything is stored. Items matching something already on file come back flagged `already_on_file`.

This matters because vision models misread handwriting, and a dosage that reads `5mg` as `50mg` is not a bug you want to find later. The assistant is instructed to read the draft back item by item and never confirm on the patient's behalf. Text inside an image is treated as data to report, never as instructions to follow.

PNG, JPEG and WebP up to 8MB, written to `backend/uploads`. That is local disk, so on an ephemeral filesystem the images do not survive a redeploy even though the extracted records do.

## ⚠️ Architecture Notes: Google Calendar Integration
The Agentic workflow is fully wired to trigger the Google Calendar API via OAuth 2.0. However, because this production deployment utilizes a free-tier headless cloud server (Render), the browser-based authentication flow cannot be completed in the live environment. For security purposes, the `credentials.json` and `token.json` files are strictly excluded via `.gitignore`.

**Graceful Degradation:** Calendar sync is engineered with a `try/except` fallback and is skipped entirely when no token has been authorised, so it can never block a booking on a headless server. The appointment persists to the database and the agent continues the conversation without disrupting the user experience. To authorise it locally, run `python backend/tools/google_cal.py` once.

## 🛠️ Local Setup & Installation

To run this project locally with full Google Calendar integration:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/suyash503/Smart-Doctor-Appointment-System.git
   ```

2. **Backend Setup:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   python seed.py
   uvicorn main:app --reload
   ```

   The API starts the MCP server itself as a subprocess, so nothing else is needed. `GET /` reports whether that connection came up.

   Add your Groq API key to a `.env` file in `backend/`:

   ```
   GROQ_API_KEY=your-key
   DATABASE_URL=sqlite:///./health_assistant.db
   ALLOWED_ORIGINS=http://localhost:5173
   ```

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## 🔒 A note on access control

There is no authentication yet. `patient_id` is supplied by the caller, so any caller can read or write against any patient. This needs solving before the project handles real patient data — the fix is to derive the patient from an authenticated session and drop the argument from the tool schemas entirely, so the model never chooses whose record it touches.

## 👤 Author
Suyash
