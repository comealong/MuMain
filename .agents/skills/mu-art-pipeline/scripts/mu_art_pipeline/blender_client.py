"""Narrow TCP client for Blender Lab's official MCP add-on."""

from __future__ import annotations

import json
import os
import socket
from typing import Any


BLENDER_HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
BLENDER_PORT = int(os.environ.get("BLENDER_PORT", "9876"))
BLENDER_TIMEOUT = float(os.environ.get("BLENDER_TIMEOUT", "60"))
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class BlenderConnectionError(RuntimeError):
    """Raised when Blender cannot complete a local bridge request."""


def execute_blender(code: str) -> dict[str, Any]:
    request = json.dumps(
        {"type": "execute", "code": code, "strict_json": True},
        ensure_ascii=False,
    ).encode("utf-8") + b"\x00"

    try:
        with socket.create_connection((BLENDER_HOST, BLENDER_PORT), timeout=BLENDER_TIMEOUT) as connection:
            connection.settimeout(BLENDER_TIMEOUT)
            connection.sendall(request)
            response = _receive_response(connection)
    except OSError as error:
        raise BlenderConnectionError(
            f"Could not reach Blender MCP at {BLENDER_HOST}:{BLENDER_PORT}. "
            "Open Blender and enable the Blender Lab MCP add-on."
        ) from error

    try:
        result = json.loads(response.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BlenderConnectionError("Blender MCP returned an invalid JSON response.") from error
    if result.get("status") != "ok":
        raise BlenderConnectionError(result.get("message", "Blender reported an unknown error."))
    payload = result.get("result")
    if not isinstance(payload, dict):
        raise BlenderConnectionError("Blender MCP returned an unexpected result.")
    return payload


def _receive_response(connection: socket.socket) -> bytes:
    response = bytearray()
    while len(response) <= MAX_RESPONSE_BYTES:
        chunk = connection.recv(8192)
        if not chunk:
            break
        terminator = chunk.find(b"\x00")
        response.extend(chunk if terminator < 0 else chunk[:terminator])
        if terminator >= 0:
            break
    if len(response) > MAX_RESPONSE_BYTES:
        raise BlenderConnectionError("Blender MCP response exceeded the 16 MiB limit.")
    if not response:
        raise BlenderConnectionError("Blender MCP closed the connection without a response.")
    return bytes(response)
