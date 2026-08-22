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

Tools: `list_doctors`, `list_patient_appointments`, `book_appointment`,
`cancel_appointment`. Resource: `appointment://patient/{patient_id}/history`.

## A note on access control

There is no authentication yet. Any caller can read or book against any
`patient_id`, which needs solving before this handles real patient data.
