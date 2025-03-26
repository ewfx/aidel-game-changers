from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
from app import *

app = FastAPI()


@app.post("/process")
async def process_request(request: Request):
    try:
        # Try to parse the incoming JSON body
        body = await request.json()

        # If it's a JSON, extract the relevant text field (assuming 'text' key is present)
        text_input = body.get("text", None)

        if not text_input:
            raise ValueError("No text provided in the JSON body")

    except json.JSONDecodeError:
        text_input = await request.body()

        text_input = text_input.decode("utf-8")

    response = get_info(text_input)

    return JSONResponse(content=response)
