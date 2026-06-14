import hashlib
import hmac
import json
import logging

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


def notify_crm(event: str, data: dict) -> bool:
    """Push a webhook notification to the CRM when new data is available."""
    if not settings.crm_webhook_url:
        return False

    payload = {"event": event, "data": data}
    headers = {"Content-Type": "application/json"}

    if settings.crm_webhook_secret:
        signature = hmac.new(
            settings.crm_webhook_secret.encode(),
            json.dumps(payload, default=str).encode(),
            hashlib.sha256,
        ).hexdigest()
        headers["X-Intel-Signature"] = signature

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(settings.crm_webhook_url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info("CRM webhook sent: %s", event)
            return True
    except Exception as e:
        logger.error("CRM webhook failed: %s", e)
        return False
