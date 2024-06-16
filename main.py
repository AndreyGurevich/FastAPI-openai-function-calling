import asyncio
import logging
import os
import traceback
from typing import Any

import uvicorn
from fastapi import Body, FastAPI
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from utils.custom_logger import logger
from utils.gpt_helper import get_openai_response_stream, openai_client

app = FastAPI()


class ChatMessage(BaseModel):
    message: str = Field(..., example="What weather is it now in San Francisco?")
    just_one_more_field: str = Field(..., example="test")


@app.post("/v1/threads")
async def create_conversation():
    thread = openai_client.beta.threads.create()
    logger.info("New thread created: " + thread.id)
    return {"id": thread.id, "messages": [], "topic": None}


@app.post("/v1/threads/{threads_id}/chat")
async def receive_message(
        threads_id: str,
        incoming_message: ChatMessage = Body(...),
) -> Any:
    logger.info(f"New request to /v1/conversations/{threads_id}/chat")
    try:
        openai_client.beta.threads.messages.create(
            thread_id=threads_id,
            role="user",
            content=incoming_message.message
        )

        loop = asyncio.get_running_loop()
        return EventSourceResponse(get_openai_response_stream(threads_id, loop), media_type="text/event-stream")

    except Exception as e:
        tb_str = traceback.format_exc()
        logging.error(f"Error in receive_message: {e}\nTraceback:\n{tb_str}")
        return {"error": "An error occurred"}


@app.get("/", summary="Test", tags=["Test"])
async def status():
    return "OK"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0",
                port=int(os.getenv("PORT", 8000)),
                log_level="info"
                )
