from fastapi import FastAPI 
from pydantic import BaseModel
from gmail_agent import agent_1

app = FastAPI()

class QueryRequest(BaseModel): 
    query: str

@app.post("/query")
def handle_query(request: QueryRequest):
    return agent_1(request.query) 