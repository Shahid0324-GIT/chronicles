"""Official LangChain adapters. SDK exception bodies never leave this module."""

import json
import re
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
        strict: bool = False,
        lease: ModelLease | None = None,
    ) -> None:
        self.client, self.name, self.model, self.credential = client, name, model, credential
        self.health_url, self.api_key, self.method = health_url, api_key, method
        self.strict = strict
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
                (
                    item
                    for item in models
                    if item.get("name" if self.name == "ollama" else "id") == self.model
                ),
                None,
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
            for unit in ("requests", "tokens"):
                if str(headers.get("x-ratelimit-remaining-" + unit, "")) == "0":
                    value = str(headers.get("x-ratelimit-reset-" + unit, ""))
                    duration = sum(
                        float(n) * {"h": 3600, "m": 60, "s": 1}[suffix]
                        for n, suffix in re.findall(r"([\d.]+)([hms])", value)
                    )
                    delay = max(delay, duration)
            raise InferenceFailure("rate_limited", delay)
        if code in (401, 403):
            raise InferenceFailure("authentication")
        if code in (400, 413, 422):
            # Identical malformed/oversized requests are not transient outages.
            # Keep response bodies private while exposing a useful diagnostic.
            raise InferenceFailure("provider_invalid_request", issues=(f"http_status:{code}",))
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
                    "presentation": 4000,
                    "presentation_verification": 2500,
                }
                client = self.client.model_copy(update={"num_predict": budgets[task]})
            if self.strict and self.method != "json_schema":
                raise InferenceFailure(
                    "provider_invalid_request", issues=("strict_requires_json_schema",)
                )
            if self.method == "json_mode":
                system += "\nReturn one JSON object conforming to this schema:\n"
                system += json.dumps(schema.model_json_schema(), separators=(",", ":"))
            runnable = client.with_structured_output(
                schema,
                method=self.method,
                include_raw=True,
                **({"strict": True} if self.strict else {}),
            )
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
            body = getattr(error, "body", {})
            detail = body.get("error", body) if isinstance(body, dict) else {}
            if self.name == "groq" and code == 400 and isinstance(detail, dict):
                if isinstance(detail.get("error"), dict):
                    detail = detail["error"]
            if (
                self.name == "groq"
                and code == 400
                and isinstance(detail, dict)
                and detail.get("code") in {"tool_use_failed", "json_validate_failed"}
            ):
                # Provider-side tool validation is invalid output, not network failure.
                # Recover only redacted schema locations; never expose failed generations.
                issues: tuple[str, ...] = ("provider:tool_schema_validation",)
                generation = detail.get("failed_generation", "")
                if isinstance(generation, str):
                    try:
                        start = generation.index("{")
                        candidate, _ = json.JSONDecoder().raw_decode(generation[start:])
                        schema.model_validate(candidate)
                    except ValidationError as invalid:
                        issues = validation_issues(invalid, schema)
                    except (ValueError, TypeError):
                        pass
                raise InferenceFailure("invalid_output", issues=issues) from None
            if code == 400 and isinstance(detail, dict):
                provider_code = str(detail.get("code", "unknown"))
                safe_code = (
                    provider_code if re.fullmatch(r"[a-z_]{1,60}", provider_code) else "unknown"
                )
                message = str(detail.get("message", "")).lower()
                categories = tuple(
                    "provider:" + word
                    for word in (
                        "tool_choice",
                        "too large",
                        "token",
                        "unsupported",
                        "schema",
                        "function",
                        "model",
                        "json",
                    )
                    if word in message
                )
                raise InferenceFailure(
                    "provider_invalid_request",
                    issues=("http_status:400", "provider_code:" + safe_code, *categories),
                ) from None
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
                            max_tokens=4000,
                            reasoning_effort=(
                                "low"
                                if settings.groq_structured_output_method == "json_mode"
                                and "gpt-oss" in settings.groq_model
                                else None
                            ),
                            timeout=settings.ai_timeout_seconds,
                        ),
                        "groq",
                        settings.groq_model,
                        label,
                        health_url="https://api.groq.com/openai/v1/models",
                        api_key=key,
                        method=settings.groq_structured_output_method,
                        strict=settings.groq_structured_output_strict,
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
        cloud_rate_limit_wait_seconds=settings.ai_cloud_rate_limit_wait_seconds,
        key_failover=settings.ai_cloud_key_failover,
    )
