"""Router from plain text input to handler functions."""

from __future__ import annotations

import json
import sys

import httpx

from handlers.basic import handle_help, handle_start
from handlers.common import HandlerContext
from handlers.lms import handle_health, handle_labs, handle_scores
from services import ServiceContainer

_SYSTEM_PROMPT = """
You are an LMS Telegram bot assistant.

Use the available tools whenever the user asks about LMS data, analytics, labs, learners, scores,
groups, timelines, completion, or sync. Prefer tool calls over guessing. You may call multiple tools
in sequence when the question requires comparison or reasoning across labs or groups.

Rules:
- Never invent LMS data.
- If the user greets you, respond warmly and briefly explain what you can do.
- If the request is ambiguous, ask a short clarifying question.
- If the request is nonsense or unrelated, explain what kinds of LMS questions you can answer.
- After receiving tool results, summarize them clearly for a human user.
""".strip()

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_items",
            "description": "List labs and tasks available in the LMS catalog.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_learners",
            "description": "Get enrolled learners and their groups.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scores",
            "description": "Get the 4-bucket score distribution for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pass_rates",
            "description": "Get per-task average scores and attempt counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeline",
            "description": "Get submissions per day for a lab timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_groups",
            "description": "Get group performance, average scores, and student counts for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_learners",
            "description": "Get the top learners by score, optionally for one lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Optional lab identifier such as 'lab-04'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of learners to return.",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_completion_rate",
            "description": "Get completion rate percentage for a lab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab": {
                        "type": "string",
                        "description": "Lab identifier such as 'lab-04'.",
                    }
                },
                "required": ["lab"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_sync",
            "description": "Refresh LMS data from the autochecker pipeline.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


async def handle_text(text: str, services: ServiceContainer) -> str:
    """Handle a command or free-form text and return a text response."""
    normalized = text.strip()
    context = HandlerContext(services=services)

    if not normalized:
        return "Please enter a command. Try /help."

    command, _, rest = normalized.partition(" ")
    argument = rest.strip() or None

    match command.lower():
        case "/start":
            return await handle_start(context)
        case "/help":
            return await handle_help(context)
        case "/health":
            return await handle_health(context)
        case "/labs":
            return await handle_labs(context)
        case "/scores":
            return await handle_scores(context, argument)
        case _:
            return await _route_free_form_text(normalized, services)


async def _route_free_form_text(text: str, services: ServiceContainer) -> str:
    if not services.llm._api_key or not services.llm._base_url or not services.llm._model:
        return (
            "Free-form routing is not configured yet. Set LLM_API_KEY, "
            "LLM_API_BASE_URL, and LLM_API_MODEL, then try again. "
            "For now, use /help for slash commands."
        )

    messages: list[dict[str, object]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    tool_results_count = 0

    for _ in range(6):
        message = await _request_chat_completion(messages, services)
        tool_calls = message.get("tool_calls")
        assistant_message: dict[str, object] = {
            "role": "assistant",
            "content": message.get("content") or "",
        }
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        messages.append(assistant_message)

        if not tool_calls:
            content = str(message.get("content") or "").strip()
            if content:
                return content
            return (
                "I could not build an answer from the model response. "
                "Try asking about labs, scores, pass rates, groups, or learners."
            )

        for tool_call in tool_calls:
            function_payload = tool_call.get("function")
            if not isinstance(function_payload, dict):
                continue

            tool_name = str(function_payload.get("name") or "")
            raw_arguments = str(function_payload.get("arguments") or "{}")
            arguments = _parse_tool_arguments(raw_arguments)
            print(
                f"[tool] LLM called: {tool_name}({json.dumps(arguments, ensure_ascii=True)})",
                file=sys.stderr,
            )

            result = await _execute_tool(tool_name, arguments, services)
            print(f"[tool] Result: {_summarize_tool_result(result)}", file=sys.stderr)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=True),
                }
            )
            tool_results_count += 1

        print(
            f"[summary] Feeding {tool_results_count} tool results back to LLM",
            file=sys.stderr,
        )

    return (
        "I reached the tool-calling limit before finishing the answer. "
        "Please try a more specific question."
    )


async def _request_chat_completion(
    messages: list[dict[str, object]],
    services: ServiceContainer,
) -> dict[str, object]:
    url = f"{_normalize_base_url(services.llm._base_url)}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {services.llm._api_key}",
    }
    payload = {
        "model": services.llm._model,
        "messages": messages,
        "tools": _TOOLS,
        "tool_choice": "auto",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"LLM error: unreadable JSON response ({exc}).") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        phrase = exc.response.reason_phrase or "HTTP error"
        raise RuntimeError(f"LLM error: HTTP {status} {phrase}.") from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError("LLM error: request timed out.") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"LLM error: {exc}.") from exc

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("LLM error: response did not include choices.")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeError("LLM error: response did not include a message.")
    return message


def _normalize_base_url(base_url: str | None) -> str:
    value = (base_url or "").strip()
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"
    if not value.endswith("/v1"):
        value = f"{value.rstrip('/')}/v1"
    return value.rstrip("/")


def _parse_tool_arguments(raw_arguments: str) -> dict[str, object]:
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


async def _execute_tool(
    tool_name: str,
    arguments: dict[str, object],
    services: ServiceContainer,
) -> object:
    lms = services.lms

    match tool_name:
        case "get_items":
            return await lms._get_json("/items/")
        case "get_learners":
            return await lms._get_json("/learners/")
        case "get_scores":
            return await lms._get_json(
                "/analytics/scores",
                params=_string_params(arguments, ("lab",)),
            )
        case "get_pass_rates":
            return await lms._get_json(
                "/analytics/pass-rates",
                params=_string_params(arguments, ("lab",)),
            )
        case "get_timeline":
            return await lms._get_json(
                "/analytics/timeline",
                params=_string_params(arguments, ("lab",)),
            )
        case "get_groups":
            return await lms._get_json(
                "/analytics/groups",
                params=_string_params(arguments, ("lab",)),
            )
        case "get_top_learners":
            return await lms._get_json(
                "/analytics/top-learners",
                params=_string_params(arguments, ("lab", "limit")),
            )
        case "get_completion_rate":
            return await lms._get_json(
                "/analytics/completion-rate",
                params=_string_params(arguments, ("lab",)),
            )
        case "trigger_sync":
            return await _trigger_sync(services)
        case _:
            return {"error": f"Unknown tool: {tool_name}"}


def _string_params(
    arguments: dict[str, object],
    allowed_keys: tuple[str, ...],
) -> dict[str, str]:
    params: dict[str, str] = {}
    for key in allowed_keys:
        value = arguments.get(key)
        if value is None:
            continue
        params[key] = str(value)
    return params


async def _trigger_sync(services: ServiceContainer) -> object:
    lms = services.lms

    if not lms._base_url:
        return "Backend error: LMS_API_BASE_URL is not configured."
    if not lms._api_key:
        return "Backend error: LMS_API_KEY is not configured."

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                lms._build_url("/pipeline/sync"),
                headers=lms._auth_headers,
            )
            response.raise_for_status()
            return response.json()
    except ValueError:
        return "Backend error: /pipeline/sync returned unreadable JSON."
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        phrase = exc.response.reason_phrase or "HTTP error"
        return f"Backend error: HTTP {status} {phrase}."
    except httpx.ConnectError as exc:
        return (
            f"Backend error: {lms._describe_request_error(exc)}. "
            "Check that the services are running."
        )
    except httpx.TimeoutException:
        return "Backend error: request timed out after 30 seconds."
    except httpx.RequestError as exc:
        return f"Backend error: {lms._describe_request_error(exc)}."


def _summarize_tool_result(result: object) -> str:
    if isinstance(result, list):
        return f"{len(result)} records"
    if isinstance(result, dict):
        if "error" in result:
            return str(result["error"])
        return f"object with keys: {', '.join(sorted(str(key) for key in result.keys())[:5])}"
    return str(result)
