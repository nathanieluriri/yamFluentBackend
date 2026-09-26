import asyncio
import json

import httpx
from openai import APIConnectionError, OpenAIError
from starlette.requests import Request

import main


def test_openai_failure_returns_the_json_error_shape():
    assert main.app.exception_handlers[OpenAIError] is main.openai_exception_handler
    request = Request(
        {"type": "http", "method": "POST", "path": "/v1/users/sessions/", "headers": [], "query_string": b""}
    )
    error = APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    )
    response = asyncio.run(main.openai_exception_handler(request, error))
    assert response.status_code == 503
    body = json.loads(response.body)
    assert body["status_code"] == 503
    assert body["data"] is None
    assert "AI service" in body["detail"]
