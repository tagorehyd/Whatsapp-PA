import os
from urllib.parse import quote

import httpx

from .logger import logger


def _post(path: str, payload: dict) -> None:
    base_url = os.environ["WA_BASE_URL"].rstrip("/")
    response = httpx.post(
        f"{base_url}{path}",
        headers={"Content-Type": "application/json", "X-API-Key": os.environ["WA_API_KEY"]},
        json=payload,
        timeout=20,
    )
    response.raise_for_status()


def send_reply(jid: str, text: str, message_id: str | None) -> None:
    path_base = f"/api/messages/{quote(os.environ['WA_SESSION_ID'], safe='')}/{quote(jid, safe='')}"
    if message_id:
        try:
            _post(f"{path_base}/reply", {"messageId": message_id, "message": {"text": text}, "fromMe": False})
            return
        except httpx.HTTPError as error:
            logger.error("Quoted WA-AKG reply failed; falling back to send: %s", error)
    _post(f"{path_base}/send", {"message": {"text": text}})
