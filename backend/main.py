from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, Base
from tools import booking, querying # <-- Import the new file here
import chat


# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Doctor Assistant API")

# --- 2. Add this CORS block right after creating the 'app' ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you'd put your actual frontend URL here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the tool routers
app.include_router(booking.router)
app.include_router(querying.router) # <-- Register the new router here
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "Doctor Assistant API is running!"}