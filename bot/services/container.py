"""Dependency container for handlers and transports."""

from __future__ import annotations

from dataclasses import dataclass

from config import Settings
from services.llm_client import LLMClient
from services.lms_client import LMSClient


@dataclass(slots=True)
class ServiceContainer:
    """Runtime services shared by handlers."""

    settings: Settings
    lms: LMSClient
    llm: LLMClient

    @classmethod
    def from_settings(cls, settings: Settings) -> "ServiceContainer":
        return cls(
            settings=settings,
            lms=LMSClient(
                base_url=settings.lms_api_base_url,
                api_key=settings.lms_api_key,
            ),
            llm=LLMClient(
                api_key=settings.llm_api_key,
                base_url=settings.llm_api_base_url,
                model=settings.llm_api_model,
            ),
        )
