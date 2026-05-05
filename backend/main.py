from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.database import engine, Base
from tools import booking, querying
import chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Doctor Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      
    allow_credentials=False,  
    allow_methods=["*"],      
    allow_headers=["*"],      
)

app.include_router(booking.router)
app.include_router(querying.router)
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "Doctor Assistant API is running and CORS is fully open!"}