import os
import json
from urllib.parse import quote

import httpx

from .logger import logger


def _post(path: str, payload: dict) -> None:
    base_url = os.environ["WA_BASE_URL"].rstrip("/")
    url = f"{base_url}{path}"
    logger.debug("WA-AKG request method=POST url=%s json=%s", url, json.dumps(payload, ensure_ascii=False))
    try:
        response = httpx.post(
            url,
            headers={"Content-Type": "application/json", "X-API-Key": os.environ["WA_API_KEY"]},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        logger.debug(
            "WA-AKG response method=POST url=%s status=%s body=%s",
            url,
            response.status_code,
            response.text,
        )
    except httpx.HTTPError as error:
        # Include the destination, but never credentials or message content.
        response = error.response if isinstance(error, httpx.HTTPStatusError) else None
        if response is not None:
            logger.debug(
                "WA-AKG error response method=POST url=%s status=%s body=%s",
                url,
                response.status_code,
                response.text,
            )
        raise RuntimeError(f"WA-AKG request failed at {url}: {error}") from error


def send_reply(jid: str, text: str, message_id: str | None) -> None:
    path_base = f"/api/messages/{quote(os.environ['WA_SESSION_ID'], safe='')}/{quote(jid, safe='')}"
    if message_id:
        try:
            _post(f"{path_base}/reply", {"messageId": message_id, "message": {"text": text}, "fromMe": False})
            return
        except RuntimeError as error:
            logger.error("Quoted WA-AKG reply failed; falling back to send: %s", error)
    _post(f"{path_base}/send", {"message": {"text": text}})
