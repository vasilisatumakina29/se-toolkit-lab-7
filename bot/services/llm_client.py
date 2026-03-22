"""Placeholder LLM client for future intent routing."""

from __future__ import annotations


class LLMClient:
    """Minimal LLM service wrapper used by free-form text routing."""

    def __init__(
        self,
        api_key: str | None,
        base_url: str | None,
        model: str | None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    async def explain_unknown_request(self, text: str) -> str:
        """Return a safe placeholder response for non-command input."""
        if "lab" in text.lower() and "available" in text.lower():
            return "Try /labs to see available labs."
        if self._api_key and self._base_url and self._model:
            return (
                "LLM routing is planned but not implemented yet. "
                "For now, use /help to see supported commands."
            )
        return "Free-form routing is not implemented yet. Try /help."
