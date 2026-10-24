from __future__ import annotations

import ipaddress
import json
import socket
from urllib.parse import urlparse

import requests

from .core import _validate_text

def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as error:
        raise ValueError("URL host cannot be resolved") from error
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            return False
    return True

def fetch_webpage(url: str) -> str:
    url = _validate_text(url, "url", max_length=2_000)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP(S) URLs are supported")
    if not _is_public_host(parsed.hostname):
        raise ValueError("Private or local network addresses are not allowed")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "SafeAgent/1.0"},
            timeout=10,
            allow_redirects=False,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError("Web request failed") from error
    if len(response.content) > 500_000:
        raise ValueError("Web response is too large")
    content_type = response.headers.get("content-type", "").lower()
    if "text" not in content_type and "json" not in content_type:
        raise ValueError("URL did not return text content")
    return json.dumps(
        {
            "url": url,
            "content_type": content_type,
            "content": response.text[:100_000],
        },
        ensure_ascii=False,
    )
