import json
import os
from pathlib import Path

from openai import OpenAI

from .logger import logger

BEHAVIOR = """You are replying as the user, not as an assistant. Match the contact's language and script: English to English, Telugu script to Telugu script, and Romanized Telugu (Tenglish) to Tenglish mixed with English. Use short casual messages. Do not use markdown, bullet lists, or formal sign-offs. Never reveal that you are an AI. Never output reasoning, analysis, or self-description. Output only the reply text, nothing else."""


def _data_dir() -> Path:
    return Path(os.getenv("DATA_DIR", "/app/data"))


def _contact_block(jid: str, push_name: str) -> str:
    contacts = json.loads((_data_dir() / "contacts.json").read_text(encoding="utf-8"))
    contact = contacts.get(jid)
    if contact:
        return f"About this contact (the person you are chatting with):\nName: {contact.get('name', '')}\nRelation: {contact.get('relation', '')}\nNotes: {contact.get('notes', '')}"
    return f"You are chatting with {push_name or 'this contact'}."


def generate_reply(jid: str, push_name: str, transcript: list[dict[str, str]]) -> str:
    # Both files are deliberately read for every call so mounted edits are live.
    context = (_data_dir() / "context.md").read_text(encoding="utf-8")
    contact_block = _contact_block(jid, push_name)
    transcript_text = "\n".join(
        f"{'Them' if message['role'] == 'user' else 'Me'}: {message['content']}" for message in transcript
    ) + '\nWrite ONLY the next "Me:" reply. Do not explain your thinking.'
    client = OpenAI(base_url=os.environ["LLM_BASE_URL"].rstrip("/"), api_key=os.environ["LLM_API_KEY"])
    request = {
        "model": os.environ["LLM_MODEL"],
        "messages": [
            {"role": "system", "content": BEHAVIOR},
            {"role": "system", "content": context},
            {"role": "system", "content": contact_block},
            {"role": "user", "content": transcript_text},
            {"role": "assistant", "content": "Me:"},
        ],
        "temperature": 0.7,
        "max_tokens": 300,
        "tool_choice": "none",
    }
    logger.debug("LLM request json=%s", json.dumps(request, ensure_ascii=False))
    response = client.chat.completions.create(
        **request,
    )
    logger.debug("LLM response json=%s", json.dumps(response.model_dump(mode="json"), ensure_ascii=False))
    return response.choices[0].message.content or ""
