"""Official LangChain adapters. SDK exception bodies never leave this module."""

import time
from contextlib import nullcontext
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langsmith import tracing_context
from pydantic import ValidationError

from src.application.inference import InferenceRouter
from src.application.ports.model_runtime import ModelLease
from src.application.research_contracts import (
    InferenceFailure,
    InferenceResult,
    InferenceUsage,
    T,
    Task,
    validation_issues,
)
from src.infrastructure.config.settings import Settings


class LangChainProvider:
    def __init__(
        self,
        client: BaseChatModel,
        name: str,
        model: str,
        credential: str,
        *,
        health_url: str,
        api_key: str | None = None,
        method: str = "json_schema",
        lease: ModelLease | None = None,
    ) -> None:
        self.client, self.name, self.model, self.credential = client, name, model, credential
        self.health_url, self.api_key, self.method = health_url, api_key, method
        self.lease = lease
        self.revision: str | None = None

    async def available(self) -> bool:
        try:
            headers = {"Authorization": "Bearer " + self.api_key} if self.api_key else {}
            async with httpx.AsyncClient(timeout=10, trust_env=False) as client:
                response = await client.get(self.health_url, headers=headers)
            self._check_status(response.status_code, response.headers)
            payload = response.json()
            models = payload.get("models", []) if self.name == "ollama" else payload.get("data", [])
            match = next(
                (item for item in models if item.get("name", item.get("id")) == self.model), None
            )
            self.revision = match.get("digest") if match and self.name == "ollama" else None
            return match is not None
        except InferenceFailure:
            raise
        except Exception:
            raise InferenceFailure("health_unavailable") from None

    @staticmethod
    def _check_status(code: int, headers: Any) -> None:
        if code == 429:
            try:
                delay = float(headers.get("retry-after", "60"))
            except (TypeError, ValueError):
                delay = 60
            raise InferenceFailure("rate_limited", delay)
        if code in (401, 403):
            raise InferenceFailure("authentication")
        if code >= 400:
            raise InferenceFailure("provider_http_error")

    async def generate(
        self, system: str, prompt: str, schema: type[T], task: Task
    ) -> InferenceResult:
        start = time.monotonic()
        try:
            client = self.client
            if self.name == "ollama":
                budgets = {
                    "planning": 600,
                    "identity_resolution": 1100,
                    "extraction": 3000,
                    "relationship_analysis": 2500,
                    "verification": 900,
                    "presentation": 1300,
                    "presentation_verification": 700,
                }
                client = self.client.model_copy(update={"num_predict": budgets[task]})
            runnable = client.with_structured_output(schema, method=self.method, include_raw=True)
            # Environment-enabled tracing must never bypass the local-content boundary.
            with tracing_context(enabled=False):
                async with self.lease() if self.lease and self.name == "ollama" else nullcontext():
                    result = await runnable.ainvoke(
                        [SystemMessage(content=system), HumanMessage(content=prompt)]
                    )
            if not isinstance(result, dict):
                raise InferenceFailure("invalid_output")
            parsed = result.get("parsed")
            if parsed is None or result.get("parsing_error"):
                error = result.get("parsing_error")
                while (
                    error is not None and not isinstance(error, ValidationError) and error.__cause__
                ):
                    error = error.__cause__
                raise InferenceFailure(
                    "invalid_output", issues=validation_issues(error or ValueError(), schema)
                )
            value = schema.model_validate(parsed)
            raw = result["raw"]
            tokens = raw.usage_metadata or {}
            return InferenceResult(
                value,
                InferenceUsage(
                    self.name,
                    self.model,
                    self.credential,
                    task,
                    "ok",
                    int((time.monotonic() - start) * 1000),
                    int(tokens.get("input_tokens", 0)),
                    int(tokens.get("output_tokens", 0)),
                    model_digest=self.revision,
                ),
            )
        except InferenceFailure:
            raise
        except ValidationError as error:
            raise InferenceFailure(
                "invalid_output", issues=validation_issues(error, schema)
            ) from None
        except Exception as error:
            response = getattr(error, "response", None)
            code = getattr(error, "status_code", 0)
            if response is not None:
                self._check_status(code or response.status_code, response.headers)
            raise InferenceFailure("inference_failed") from None


def create_inference(
    settings: Settings, lease: ModelLease | None = None, cache: Any = None
) -> InferenceRouter:
    local = LangChainProvider(
        ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            reasoning=False,
            num_ctx=8192,
            num_predict=4500,
            keep_alive=0,
            client_kwargs={"timeout": settings.ai_timeout_seconds, "trust_env": False},
        ),
        "ollama",
        settings.ollama_chat_model,
        "local",
        health_url=settings.ollama_base_url + "/api/tags",
        lease=lease,
    )
    cloud: list[LangChainProvider] = []
    if settings.groq_model:
        for label, secret in [
            ("primary", settings.groq_api_key_primary),
            ("secondary", settings.groq_api_key_secondary),
        ]:
            if secret and secret.get_secret_value().strip():
                key = secret.get_secret_value()
                cloud.append(
                    LangChainProvider(
                        ChatGroq(
                            model=settings.groq_model,
                            api_key=secret,
                            temperature=0,
                            max_retries=0,
                            timeout=settings.ai_timeout_seconds,
                        ),
                        "groq",
                        settings.groq_model,
                        label,
                        health_url="https://api.groq.com/openai/v1/models",
                        api_key=key,
                        method="function_calling",
                    )
                )
    return InferenceRouter(
        local,
        list(cloud),
        mode=settings.ai_provider_mode,
        cloud_content_allowed=settings.ai_cloud_content_allowed,
        attempts=settings.ai_max_attempts,
        timeout=settings.ai_timeout_seconds,
        concurrency=settings.ai_max_concurrent_inferences,
        cache=cache,
        max_calls=settings.agent_max_model_calls,
        stage_limits=settings.agent_stage_model_calls,
    )
