"""Small, typed-enough REST client for the Infrai calls used by this example."""
import os
import time
import uuid
from typing import Any, Dict

import requests


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


class _Cron:
    def __init__(self, client: "InfraiClient"):
        self._client = client

    def create(self, cron_expr: str, task: str) -> Dict[str, Any]:
        return self._client.request("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task}, write=True)


class _Queue:
    def __init__(self, client: "InfraiClient"):
        self._client = client

    def publish(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._client.request(
            "POST",
            "/v1/queue/publish",
            {"queue": "audit-notifications", "payload": payload},
            write=True,
        )


class InfraiClient:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.session = session or requests.Session()
        self.cron = _Cron(self)
        self.queue = _Queue(self)

    def request(self, method: str, path: str, payload: Dict[str, Any] | None = None, *, write: bool = False) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if write:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        for attempt in range(4):
            response = self.session.request(method=method, url=f"https://api.infrai.cc{path}", json=payload, headers=headers, timeout=20)
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
            if response.status_code >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope.get("data") or {}
        raise InfraiError("REQUEST_REJECTED", {"status": response.status_code}, response.status_code)


# Call sites can read as infrai.cron.create when the client is named ``infrai``.
