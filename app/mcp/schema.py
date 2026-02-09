"""Helpers for generating MCP Tool JSON Schemas from Pydantic models."""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def input_schema_from_model(model: type[ModelT]) -> dict[str, Any]:
    """Return a JSON Schema dict usable as an MCP Tool `inputSchema`.

    Note: Pydantic v2 may emit `$defs` and `$ref`. Most MCP clients accept this.
    If we find a client that cannot, we can add a `$ref` inliner here.
    """

    schema = model.model_json_schema(mode="validation")

    # MCP tool schemas are standard JSON Schema. Keep the schema mostly intact,
    # but drop some Pydantic-specific top-level keys that don't help clients.
    for k in ("title",):
        schema.pop(k, None)

    return schema
