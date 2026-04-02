"""
FastAPI wrapper for the Memory Agent.

Provides REST endpoints for multi-tenant conversational agent with semantic memory.
Imports and uses the Agent class from agent.py.
"""

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent import Agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s,p%(process)s,{%(filename)s:%(lineno)d},%(levelname)s,%(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Memory Agent API",
    description="Multi-tenant conversational agent with semantic memory",
    version="1.0.0",
)

_session_cache: Dict[str, Agent] = {}

class InvocationRequest(BaseModel):
    user_id: str = Field(..., description="User identifier for memory isolation")
    run_id: Optional[str] = Field(
        None, description="Session ID (auto-generated if not provided)"
    )
    query: str = Field(..., description="User's message")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional context/tags"
    )


class InvocationResponse(BaseModel):
    response: str = Field(..., description="Agent's response text")
    user_id: str
    run_id: str


class PingResponse(BaseModel):
    status: str
    message: str

def _get_or_create_agent(user_id: str, run_id: str) -> Agent:
    """Get existing Agent for session or create a new one."""
    if run_id in _session_cache:
        return _session_cache[run_id]

    logger.info(f"Creating new Agent for user_id={user_id}, run_id={run_id}")
    agent = Agent(user_id=user_id, run_id=run_id)
    _session_cache[run_id] = agent
    return agent


@app.get("/ping", response_model=PingResponse)
def ping():
    """Health check endpoint."""
    return PingResponse(status="ok", message="Memory Agent API is running")


@app.post("/invocation", response_model=InvocationResponse)
def invocation(request: InvocationRequest):
    """Main conversation endpoint.

    Takes user query and returns agent response. Maintains session state
    via run_id so that multiple turns in the same session reuse the same
    Agent instance (and therefore the same Strands conversation context).
    """
    run_id = request.run_id or str(uuid.uuid4())[:8]

    try:
        agent = _get_or_create_agent(request.user_id, run_id)
        response_text = agent.chat(request.query)

        return InvocationResponse(
            response=response_text,
            user_id=request.user_id,
            run_id=run_id,
        )

    except Exception as e:
        logger.error(f"Error in /invocation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))