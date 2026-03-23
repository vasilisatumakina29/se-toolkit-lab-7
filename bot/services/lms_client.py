"""Small client for the LMS backend API."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx


class LMSClient:
    """Access LMS backend data with graceful fallback messages."""

    def __init__(self, base_url: str | None, api_key: str | None) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._api_key = api_key

    async def get_health(self) -> str:
        """Check whether the backend is reachable."""
        items = await self._get_items()
        if isinstance(items, str):
            return items
        return f"Backend is healthy. {len(items)} items available."

    async def list_labs(self) -> str:
        """Return the list of labs from the backend."""
        items = await self._get_items()
        if isinstance(items, str):
            return items

        labs = [
            item.get("title", "Untitled lab")
            for item in items
            if isinstance(item, dict) and item.get("type") == "lab"
        ]
        if not labs:
            return "No labs were found in the LMS yet."
        return "Available labs:\n" + "\n".join(f"- {lab}" for lab in labs[:10])

    async def get_scores(self, lab: str) -> str:
        """Return per-task average scores for a lab."""
        if not lab:
            return "Usage: /scores <lab-id>"

        payload = await self._get_json("/analytics/pass-rates", params={"lab": lab})
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, list) or not payload:
            return f"No pass-rate data found for {lab}. Check the lab id and backend data."

        lines = [f"Pass rates for {lab.upper().replace('-', ' ')}:"]
        for task in payload:
            if not isinstance(task, dict):
                continue
            name = str(task.get("task", "Untitled task"))
            avg_score = float(task.get("avg_score", 0.0))
            attempts = int(task.get("attempts", 0))
            lines.append(f"- {name}: {avg_score:.1f}% ({attempts} attempts)")
        if len(lines) == 1:
            return f"No pass-rate data found for {lab}. Check the lab id and backend data."
        return "\n".join(lines)

    def _build_url(self, path: str) -> str:
        return urljoin(f"{self._base_url}/", path.lstrip("/"))

    async def _get_items(self) -> list[dict[str, object]] | str:
        payload = await self._get_json("/items/")
        if isinstance(payload, str):
            return payload
        if not isinstance(payload, list):
            return "Backend error: /items returned an unexpected response. Check the backend service."
        items = [item for item in payload if isinstance(item, dict)]
        return items

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> object | str:
        if not self._base_url:
            return "Backend error: LMS_API_BASE_URL is not configured."
        if not self._api_key:
            return "Backend error: LMS_API_KEY is not configured."

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    self._build_url(path),
                    params=params,
                    headers=self._auth_headers,
                )
                response.raise_for_status()
                return response.json()
        except ValueError:
            return f"Backend error: {path} returned unreadable JSON."
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            phrase = exc.response.reason_phrase or "HTTP error"
            return f"Backend error: HTTP {status} {phrase}."
        except httpx.ConnectError as exc:
            return f"Backend error: {self._describe_request_error(exc)}. Check that the services are running."
        except httpx.TimeoutException:
            return "Backend error: request timed out after 5 seconds."
        except httpx.RequestError as exc:
            return f"Backend error: {self._describe_request_error(exc)}."

    def _describe_request_error(self, exc: httpx.RequestError) -> str:
        request = exc.request
        host = request.url.host or "unknown host"
        port = request.url.port
        location = f"{host}:{port}" if port else host
        message = str(exc).strip()
        if message:
            return f"{message} ({location})"
        return f"request failed ({location})"

    @property
    def _auth_headers(self) -> dict[str, str]:
        if not self._api_key:
            return {}
        return {"Authorization": f"Bearer {self._api_key}"}
