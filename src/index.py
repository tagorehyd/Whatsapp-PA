import asyncio
import json
import os
import re

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse

from .db import ensure_contact, get_recent_messages, insert_incoming_message, insert_outgoing_message
from .llm import generate_reply
from .logger import logger
from .wa_client import send_reply

app = FastAPI()
BANNED_REPLY_TEXT = re.compile(r"let me think|the user is asking|i need to reply|i should reply|analysis:|reasoning:|chain of thought|let me analyze", re.IGNORECASE)


def normalize_event(payload: dict) -> dict | None:
    data = payload.get("data") or {}
    key = data.get("key") or {}
    event = payload.get("event")
    jid = data.get("from") or key.get("remoteJid")
    if (event != "message.received" or key.get("fromMe") is True or data.get("sender") == "ME" or data.get("type") != "TEXT" or data.get("chatType") == "STATUS" or data.get("chatType") not in {"PERSONAL", "GROUP"} or not jid or jid == "status@broadcast" or jid.endswith("@broadcast") or jid.endswith("@newsletter")):
        return None
    return {"jid": jid, "text": data.get("content") or "", "push_name": data.get("pushName") or "", "message_id": key.get("id"), "from_me": key.get("fromMe", False), "event": event}


def sanitize_reply(value: str) -> str | None:
    reply = re.sub(r"^(?:me|ravi|assistant|you):\s*", "", str(value or "").strip(), flags=re.IGNORECASE).strip()
    if len(reply) >= 2 and reply[0] == reply[-1] and reply[0] in {"\"", "'"}:
        reply = reply[1:-1].strip()
    if not reply or BANNED_REPLY_TEXT.search(reply):
        return None
    return reply[:600]


async def process_webhook(raw_body: bytes) -> None:
    try:
        payload = json.loads(raw_body)
        message = normalize_event(payload)
        if not message:
            logger.info("Ignored WA-AKG webhook event=%s", payload.get("event"))
            return
        logger.info("Processing incoming WA-AKG message jid=%s message_id=%s", message["jid"], message["message_id"])
        # Contact creation always precedes either messages-table insert.
        await asyncio.to_thread(ensure_contact, message["jid"], message["push_name"])
        inserted_id = await asyncio.to_thread(insert_incoming_message, message["jid"], message["text"], message["message_id"])
        if not inserted_id:
            logger.info("Duplicate WA-AKG webhook ignored; message_id=%s", message["message_id"])
            return
        limit = int(os.getenv("CONTEXT_MESSAGES", "30"))
        transcript = await asyncio.to_thread(get_recent_messages, message["jid"], limit)
        logger.info("Requesting LLM reply jid=%s transcript_messages=%s", message["jid"], len(transcript))
        raw_reply = await asyncio.to_thread(generate_reply, message["jid"], message["push_name"], transcript)
        reply = sanitize_reply(raw_reply)
        if not reply:
            logger.error("LLM reply was empty or unsafe; not sending; jid=%s", message["jid"])
            return
        await asyncio.to_thread(send_reply, message["jid"], reply, message["message_id"])
        await asyncio.to_thread(insert_outgoing_message, message["jid"], reply)
        logger.info("Sent WA-AKG reply jid=%s message_id=%s", message["jid"], message["message_id"])
    except Exception:
        logger.exception("Webhook processing failed")


async def webhook_handler(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    raw_body = await request.body()
    response = JSONResponse(status_code=200, content={"ok": True})
    logger.info("Received WA-AKG webhook path=%s bytes=%s", request.url.path, len(raw_body))
    background_tasks.add_task(process_webhook, raw_body)
    response.background = background_tasks
    return response


app.post("/webhook")(webhook_handler)
app.post("/")(webhook_handler)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "ts": int(__import__("time").time() * 1000)}


@app.get("/webhook")
async def webhook_verification() -> dict:
    return {"ok": True}
