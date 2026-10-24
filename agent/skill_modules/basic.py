from __future__ import annotations

import ast
import datetime as dt
import json
import operator
import os
import sys
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from .core import _validate_text, _workspace_root

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}

def get_weather(city: str) -> str:
    city = _validate_text(city, "city")
    api_key = os.getenv("WEATHER_API_KEY") or os.getenv("weather_api_key")
    if not api_key:
        raise ValueError("Weather API key is not configured")

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "appid": api_key,
                "units": "metric",
                "lang": "zh_cn",
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise RuntimeError("Weather service request failed") from error
    except (ValueError, json.JSONDecodeError) as error:
        raise RuntimeError("Weather service returned invalid data") from error

    return json.dumps(
        {
            "city": data.get("name", city),
            "country": data.get("sys", {}).get("country"),
            "temperature_c": data.get("main", {}).get("temp"),
            "feels_like_c": data.get("main", {}).get("feels_like"),
            "humidity_percent": data.get("main", {}).get("humidity"),
            "description": (data.get("weather") or [{}])[0].get("description"),
        },
        ensure_ascii=False,
    )

def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        if isinstance(node.value, bool):
            raise ValueError("Boolean values are not supported")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("Exponent is too large")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if abs(result) > 1e100:
            raise ValueError("Result is too large")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))
    raise ValueError("Only numeric arithmetic is supported")

def calculate(expression: str) -> str:
    expression = _validate_text(expression, "expression", max_length=200)
    try:
        tree = ast.parse(expression, mode="eval")
        result = _evaluate(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as error:
        raise ValueError("Invalid arithmetic expression") from error
    return str(result)

def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    timezone = _validate_text(timezone, "timezone", max_length=64)
    try:
        current = dt.datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError as error:
        raise ValueError("Unknown timezone") from error
    return current.isoformat(timespec="seconds")

def get_workspace_info() -> str:
    root = _workspace_root()
    return json.dumps(
        {
            "workspace": str(root),
            "exists": root.exists(),
            "is_directory": root.is_dir(),
            "note": "All relative file paths are resolved under this directory.",
        },
        ensure_ascii=False,
    )

def get_runtime_info() -> str:
    root = _workspace_root()
    return json.dumps(
        {
            "workspace": str(root),
            "provider": os.getenv("MODEL_PROVIDER", "openai-compatible"),
            "model": (
                os.getenv("MODEL_NAME")
                or "gpt-4o-mini"
            ),
            "base_url": (
                os.getenv("MODEL_BASE_URL")
                or "https://api.openai.com/v1"
            ),
            "api_key_configured": bool(os.getenv("MODEL_API_KEY")),
            "weather_key_configured": bool(
                os.getenv("WEATHER_API_KEY") or os.getenv("weather_api_key")
            ),
            "python": sys.version.split()[0],
        },
        ensure_ascii=False,
    )
