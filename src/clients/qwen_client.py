from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from openai import APIConnectionError, APITimeoutError, BadRequestError, OpenAI, RateLimitError
from openai.types.chat import ChatCompletion
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.clients.config import settings
from src.telemetry import track_call

logger = logging.getLogger(__name__)

_FAILURE_WINDOW_SECONDS = 30
_OPEN_SECONDS = 15
_FAILURE_THRESHOLD = 3


class QwenUnavailableError(RuntimeError):
	pass


@dataclass(frozen=True)
class CallTelemetry:
	model: str
	latency_ms: int
	prompt_tokens: int | None
	completion_tokens: int | None
	had_tool_call: bool


class CircuitBreaker:
	CLOSED = "closed"
	OPEN = "open"
	HALF_OPEN = "half_open"

	def __init__(self) -> None:
		self._state = self.CLOSED
		self._failure_times: list[float] = []
		self._opened_at = 0.0
		self._half_open_probe_in_flight = False
		self._lock = threading.Lock()

	def allow_call(self) -> str:
		now = time.monotonic()
		with self._lock:
			if self._state == self.OPEN:
				if now < self._opened_at + _OPEN_SECONDS:
					raise QwenUnavailableError(
						"Qwen circuit breaker is OPEN after repeated failures; requests are temporarily blocked."
					)
				self._state = self.HALF_OPEN
				self._half_open_probe_in_flight = False

			if self._state == self.HALF_OPEN:
				if self._half_open_probe_in_flight:
					raise QwenUnavailableError(
						"Qwen circuit breaker is HALF_OPEN and a probe request is already in flight."
					)
				self._half_open_probe_in_flight = True

			return self._state

	def record_success(self) -> None:
		with self._lock:
			self._state = self.CLOSED
			self._failure_times.clear()
			self._opened_at = 0.0
			self._half_open_probe_in_flight = False

	def record_failure(self) -> None:
		now = time.monotonic()
		with self._lock:
			if self._state == self.HALF_OPEN:
				self._state = self.OPEN
				self._opened_at = now
				self._half_open_probe_in_flight = False
				self._failure_times.clear()
				return

			self._failure_times = [timestamp for timestamp in self._failure_times if now - timestamp <= _FAILURE_WINDOW_SECONDS]
			self._failure_times.append(now)

			if len(self._failure_times) >= _FAILURE_THRESHOLD:
				self._state = self.OPEN
				self._opened_at = now
				self._failure_times.clear()

	@property
	def state(self) -> str:
		with self._lock:
			if self._state == self.OPEN and time.monotonic() >= self._opened_at + _OPEN_SECONDS:
				self._state = self.HALF_OPEN
				self._half_open_probe_in_flight = False
			return self._state


class QwenClient:
	def __init__(self, *, api_key: str | None = None, base_url: str | None = None) -> None:
		self.settings = settings
		self._client = OpenAI(
			api_key=api_key or self.settings.DASHSCOPE_API_KEY,
			base_url=base_url or self.settings.QWEN_BASE_URL,
		)
		self._breaker = CircuitBreaker()
		self.last_telemetry: CallTelemetry | None = None

	@retry(
		reraise=True,
		stop=stop_after_attempt(3),
		wait=wait_exponential(multiplier=0.5, min=1, max=8),
		retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
	)
	def _create_completion(self, **kwargs: Any) -> ChatCompletion:
		return self._client.chat.completions.create(**kwargs)

	def call_qwen_cheap(
		self,
		messages: Sequence[Any],
		tools: list[dict[str, Any]] | None = None,
		tool_choice: Any = "auto",
		temperature: float = 0.3,
		max_tokens: int = 1024,
	) -> ChatCompletion:
		return self._call(
			messages=messages,
			model=self.settings.QWEN_MODEL_CHEAP,
			tools=tools,
			tool_choice=tool_choice,
			temperature=temperature,
			max_tokens=max_tokens,
		)

	@track_call("qwen.call_qwen")
	def call_qwen(
		self,
		messages: Sequence[Any],
		tools: list[dict[str, Any]] | None = None,
		tool_choice: Any = "auto",
		temperature: float = 0.3,
		max_tokens: int = 1024,
	) -> ChatCompletion:
		return self._call(
			messages=messages,
			model=self.settings.QWEN_MODEL,
			tools=tools,
			tool_choice=tool_choice,
			temperature=temperature,
			max_tokens=max_tokens,
		)

	@track_call("qwen.call_qwen_structured")
	def call_qwen_structured(self, messages: Sequence[Any], tool_schema: dict[str, Any]) -> dict[str, Any]:
		function_schema = tool_schema.get("function") or {}
		function_name = function_schema.get("name")
		if not function_name:
			raise ValueError("tool_schema must include function.name for structured Qwen calls.")

		forced_tool_choice = {"type": "function", "function": {"name": function_name}}

		try:
			response = self._call(
				messages=messages,
				tools=[tool_schema],
				tool_choice=forced_tool_choice,
				model=self.settings.QWEN_MODEL,
				temperature=0.3,
				max_tokens=1024,
			)
			return self._parse_forced_tool_response(response, function_name)
		except BadRequestError:
			return self._call_structured_json_fallback(messages=messages, tool_schema=tool_schema)

	def _call(
		self,
		*,
		messages: Sequence[Any],
		model: str,
		tools: list[dict[str, Any]] | None,
		tool_choice: Any,
		temperature: float,
		max_tokens: int,
	) -> ChatCompletion:
		self._breaker.allow_call()
		normalized_messages = self._normalize_messages(messages)
		start_time = time.perf_counter()
		try:
			response = self._create_completion(
				model=model,
				messages=normalized_messages,
				tools=tools,
				tool_choice=tool_choice,
				temperature=temperature,
				max_tokens=max_tokens,
			)
		except (RateLimitError, APIConnectionError, APITimeoutError):
			self._breaker.record_failure()
			raise
		except Exception:
			raise

		self._breaker.record_success()

		self._record_telemetry(response=response, model=model, start_time=start_time)
		return response

	def _call_structured_json_fallback(self, messages: Sequence[Any], tool_schema: dict[str, Any]) -> dict[str, Any]:
		schema_text = json.dumps(tool_schema, ensure_ascii=False, separators=(",", ":"))
		fallback_messages = [
			{
				"role": "system",
				"content": (
					"Return only a valid JSON object for the following tool schema. "
					"Do not wrap the result in markdown or extra text. Schema: " + schema_text
				),
			},
			*self._normalize_messages(messages),
		]

		first_response = self._call(
			messages=fallback_messages,
			model=self.settings.QWEN_MODEL,
			tools=None,
			tool_choice="auto",
			temperature=0.3,
			max_tokens=1024,
		)
		try:
			return self._json_from_response(first_response)
		except (ValueError, json.JSONDecodeError):
			retry_messages = [
				*fallback_messages,
				{
					"role": "user",
					"content": "your last output was invalid JSON, return ONLY valid JSON",
				},
			]
			second_response = self._call(
				messages=retry_messages,
				model=self.settings.QWEN_MODEL,
				tools=None,
				tool_choice="auto",
				temperature=0.3,
				max_tokens=1024,
			)
			return self._json_from_response(second_response)

	def _parse_forced_tool_response(self, response: ChatCompletion, expected_name: str) -> dict[str, Any]:
		choice = response.choices[0]
		tool_calls = getattr(choice.message, "tool_calls", None) or []
		if not tool_calls:
			raise ValueError("Qwen did not return a tool call for the forced structured request.")

		if len(tool_calls) != 1:
			raise ValueError("Qwen returned more than one tool call for the forced structured request.")

		tool_call = tool_calls[0]
		function = getattr(tool_call, "function", None)
		function_name = getattr(function, "name", None)
		if function_name != expected_name:
			raise ValueError(
				f"Qwen returned tool call '{function_name}' instead of the forced function '{expected_name}'."
			)

		arguments = getattr(function, "arguments", "")
		return json.loads(arguments)

	def _json_from_response(self, response: ChatCompletion) -> dict[str, Any]:
		content = response.choices[0].message.content
		if not content:
			raise ValueError("Qwen returned an empty response while JSON was required.")
		parsed = json.loads(content)
		if not isinstance(parsed, dict):
			raise ValueError("Qwen structured JSON response must be an object.")
		return parsed

	def _record_telemetry(self, *, response: ChatCompletion, model: str, start_time: float | None) -> None:
		usage = getattr(response, "usage", None)
		latency_ms = int((time.perf_counter() - start_time) * 1000) if start_time is not None else 0
		telemetry = CallTelemetry(
			model=model,
			latency_ms=latency_ms,
			prompt_tokens=getattr(usage, "prompt_tokens", None),
			completion_tokens=getattr(usage, "completion_tokens", None),
			had_tool_call=bool(getattr(response.choices[0].message, "tool_calls", None)),
		)
		self.last_telemetry = telemetry
		try:
			setattr(response, "qwen_telemetry", telemetry)
		except Exception:
			pass

		logger.info(
			json.dumps(
				{
					"model": telemetry.model,
					"latency_ms": telemetry.latency_ms,
					"prompt_tokens": telemetry.prompt_tokens,
					"completion_tokens": telemetry.completion_tokens,
					"had_tool_call": telemetry.had_tool_call,
				},
				separators=(",", ":"),
				ensure_ascii=False,
			)
		)

	def _normalize_messages(self, messages: Sequence[Any]) -> list[dict[str, Any]]:
		normalized: list[dict[str, Any]] = []
		for message in messages:
			normalized.append(self._normalize_message(message))
		return normalized

	def _normalize_message(self, message: Any) -> dict[str, Any]:
		if isinstance(message, Mapping):
			return dict(message)

		message_type = getattr(message, "type", None) or getattr(message, "role", None)
		content = getattr(message, "content", None)
		additional_kwargs = getattr(message, "additional_kwargs", {}) or {}

		role_map = {
			"human": "user",
			"user": "user",
			"ai": "assistant",
			"assistant": "assistant",
			"system": "system",
			"tool": "tool",
		}
		role = role_map.get(message_type, message_type)
		if role is None:
			raise TypeError(f"Unsupported message type: {type(message)!r}")

		normalized: dict[str, Any] = {"role": role, "content": content}
		for key in ("name", "tool_call_id", "tool_calls", "function_call"):
			if hasattr(message, key):
				value = getattr(message, key)
				if value is not None:
					normalized[key] = value

		for key in ("tool_calls", "function_call"):
			if key in additional_kwargs and additional_kwargs[key] is not None:
				normalized[key] = additional_kwargs[key]

		if role == "tool" and "tool_call_id" not in normalized:
			tool_call_id = getattr(message, "tool_call_id", None) or additional_kwargs.get("tool_call_id")
			if tool_call_id:
				normalized["tool_call_id"] = tool_call_id

		return normalized


qwen_client = QwenClient()
