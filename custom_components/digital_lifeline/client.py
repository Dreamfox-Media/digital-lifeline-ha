"""HTTP client for the Digital Lifeline portal."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import parse_qs, urlparse

import aiohttp

from .const import REQUEST_TIMEOUT_S

_LOGGER = logging.getLogger(__name__)

# Not found (e.g. during a portal deploy), request timeout and rate limiting are
# temporary: keep the events queued instead of dropping them as invalid.
_RETRYABLE_STATUSES = (404, 408, 429)


class LifelineError(Exception):
    """Base error."""


class LifelineAuthError(LifelineError):
    """Token or household was rejected."""


class LifelineDisabledError(LifelineError):
    """The integration switch is off in the portal."""


class LifelineConnectionError(LifelineError):
    """Portal unreachable or returned a server error (retryable)."""


class LifelineRequestError(LifelineError):
    """Portal rejected the request as invalid (not retryable)."""


def parse_webhook_url(url: str) -> tuple[str, str]:
    """Split the pasted webhook URL into (base_url, household_id).

    Accepts ``https://host/api/public/webhooks/ha-integration?household=<uuid>``.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("invalid url")
    household = (parse_qs(parsed.query).get("household") or [None])[0]
    if not household:
        raise ValueError("missing household")
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    return base, household


class LifelineClient:
    """Thin async client; one instance per config entry."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        household: str,
        token: str,
    ) -> None:
        self._session = session
        self._base = base_url
        self._household = household
        self._token = token

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "X-DL-Token": self._token,
            "X-DL-Household": self._household,
            "Content-Type": "application/json",
        }
        try:
            async with self._session.post(
                f"{self._base}/{path}",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_S),
            ) as resp:
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    body = {}
                if resp.status == 401:
                    raise LifelineAuthError("unauthorized")
                if resp.status == 403:
                    if isinstance(body, dict) and body.get("error") == "integration_disabled":
                        raise LifelineDisabledError("integration disabled in portal")
                    raise LifelineAuthError("forbidden")
                if resp.status >= 500 or resp.status in _RETRYABLE_STATUSES:
                    raise LifelineConnectionError(f"portal error {resp.status}")
                if resp.status >= 400:
                    raise LifelineRequestError(f"request rejected ({resp.status})")
                return body if isinstance(body, dict) else {}
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise LifelineConnectionError(str(err) or type(err).__name__) from err

    async def handshake(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("handshake", payload)

    async def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post("heartbeat", payload)

    async def send_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        return await self._post("event", {"events": events})
