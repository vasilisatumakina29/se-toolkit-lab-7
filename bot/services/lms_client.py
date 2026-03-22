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
        if not self._base_url:
            return "LMS API base URL is not configured yet."

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self._build_url("/openapi.json"))
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return f"LMS API is unreachable: {exc}"

        return f"LMS API is reachable at {self._base_url}."

    async def list_labs(self) -> str:
        """Return a placeholder or a best-effort lab list."""
        if not self._base_url or not self._api_key:
            return "Labs are not available yet: LMS API credentials are not configured."

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    self._build_url("/items"),
                    headers=self._auth_headers,
                )
                response.raise_for_status()
                items = response.json()
        except httpx.HTTPError:
            return "Labs command is scaffolded, but backend data is not available right now."
        except ValueError:
            return "Labs command is scaffolded, but backend returned unreadable data."

        labs = [
            item.get("title", "Untitled lab")
            for item in items
            if isinstance(item, dict) and item.get("type") == "lab"
        ]
        if not labs:
            return "No labs were found in the LMS yet."
        return "Available labs:\n" + "\n".join(f"- {lab}" for lab in labs[:10])

    async def get_scores(self, lab: str) -> str:
        """Return a text summary for the scores endpoint."""
        if not lab:
            return "Usage: /scores <lab-id>"
        if not self._base_url or not self._api_key:
            return f"Scores for {lab}: backend credentials are not configured yet."

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    self._build_url("/analytics/scores"),
                    params={"lab": lab},
                    headers=self._auth_headers,
                )
                response.raise_for_status()
                buckets = response.json()
        except httpx.HTTPError:
            return f"Scores for {lab}: command scaffold is ready, but backend data is unavailable."
        except ValueError:
            return f"Scores for {lab}: backend returned unreadable data."

        if not isinstance(buckets, list) or not buckets:
            return f"Scores for {lab}: no score data found."

        lines = [f"Score distribution for {lab}:"]
        for bucket in buckets:
            if not isinstance(bucket, dict):
                continue
            lines.append(f"- {bucket.get('bucket', '?')}: {bucket.get('count', 0)}")
        return "\n".join(lines)

    def _build_url(self, path: str) -> str:
        return urljoin(f"{self._base_url}/", path.lstrip("/"))

    @property
    def _auth_headers(self) -> dict[str, str]:
        if not self._api_key:
            return {}
        return {"Authorization": f"Bearer {self._api_key}"}
