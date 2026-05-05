# 🏥 Smart Doctor Appointment & Reporting Assistant

An intelligent, full-stack medical scheduling assistant powered by Agentic AI and the Model Context Protocol (MCP). This application allows patients to book appointments and query doctor availability using natural language, seamlessly translating conversational intent into strict database operations.

## 🚀 Live Demo
**Access the live application here:** [Smart Doctor AI](https://smart-doctor-ai.vercel.app/)

*Note: The backend is hosted on a free Render instance. If the application has not been used in the last 15 minutes, the server will go to sleep. **The first message you send may take 30–50 seconds to process** while the server wakes up. Subsequent messages will be instant.*

## 🧠 Core Architecture
This project implements a true Agentic Loop, where an LLM is granted autonomous access to backend tools to fulfill user requests.

* **Frontend:** React, Vite, and custom CSS for a ChatGPT-style conversational interface. Hosted on Vercel.
* **Backend:** FastAPI (Python) implementing modular routing and MCP tool exposure. Hosted on Render.
* **Database:** SQLite with SQLAlchemy ORM.
* **Data Validation:** Pydantic schemas ensure the LLM cannot hallucinate or inject malformed data into the database.
* **AI Agent:** Groq API utilizing Meta's Llama 3 models for high-speed, low-latency reasoning and tool calling.
* **Memory:** Multi-turn conversational memory persisted via session IDs.

## ⚡ Features
* **Natural Language Processing:** Users can type complex requests (e.g., "I need to see Dr. House tomorrow at 10 AM for a severe headache").
* **Autonomous Tool Execution:** The AI parses the prompt, decides which Python tool to use, and executes the SQL queries.
* **Multi-Turn Memory:** The agent remembers previous context within the same session.
* **Strict Schema Enforcement:** Backend refuses any AI requests that do not match the strict Pydantic database models.

## ⚠️ Architecture Notes: Google Calendar Integration
The Agentic workflow is fully wired to trigger the Google Calendar API via OAuth 2.0. However, because this production deployment utilizes a free-tier headless cloud server (Render), the browser-based authentication flow cannot be completed in the live environment. For security purposes, the `credentials.json` and `token.json` files are strictly excluded via `.gitignore`. 

**Graceful Degradation:** The `book_appointment` MCP tool is engineered with a `try/except` fallback. If the external Google Calendar API fails or is missing credentials on the cloud server, the system catches the error, successfully persists the appointment directly to the PostgreSQL/SQLite database, and allows the AI agent to continue the conversation without disrupting the user experience.

## 🛠️ Local Setup & Installation

To run this project locally with full Google Calendar integration:

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/suyash503/Smart-Doctor-Appointment-System.git](https://github.com/suyash503/Smart-Doctor-Appointment-System.git)
