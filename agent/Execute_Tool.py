"""Compatibility facade for the built-in tool API.

The tool catalog, registry, and dispatcher live in :mod:`agent.tooling`.
"""

from .tooling import TOOL_DEFINITIONS, TOOL_FUNCTIONS, TOOL_PERMISSIONS, execute_tool
