from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from gmail_agent import agent_1
import os

app = FastAPI()

class QueryRequest(BaseModel):
    query: str

@app.post("/query")
def handle_query(request: QueryRequest, x_api_key: str = Header(None)):
    if x_api_key != os.getenv("API_SECRET"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return agent_1(request.query)