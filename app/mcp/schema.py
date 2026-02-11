"""Helpers for generating MCP Tool JSON Schemas from Pydantic models."""

from __future__ import annotations

import copy
from typing import Any, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)

_NULL_VARIANT = {"type": "null"}


def _simplify_anyof_nulls(schema: dict[str, Any]) -> None:
    """Simplify ``anyOf`` nullable patterns in-place for MCP client compatibility.

    Pydantic v2 emits ``anyOf: [{type: X}, {type: null}]`` for ``X | None``
    fields.  Many MCP clients (including Claude Code) expect a flat
    ``type: X`` and show "unknown" when they encounter ``anyOf``.

    Rules:
    - 2-item anyOf with one null variant → flatten the non-null variant into
      the property (preserving description, default, etc.).
    - 3+-item anyOf with a null variant → drop the null variant but keep
      ``anyOf`` with the remaining types (can't reduce to a single type).
    - anyOf without a null variant → leave untouched.
    """
    for prop in schema.get("properties", {}).values():
        any_of = prop.get("anyOf")
        if not any_of:
            continue

        non_null = [v for v in any_of if v != _NULL_VARIANT]
        if len(non_null) == len(any_of):
            # No null variant – nothing to simplify.
            continue

        if len(non_null) == 1:
            # Simple case: merge the single non-null variant into the prop.
            del prop["anyOf"]
            prop.update(non_null[0])
        else:
            # Multi-type union – drop null, keep anyOf with the rest.
            prop["anyOf"] = non_null


def _inline_refs(node: Any, defs: dict[str, Any]) -> Any:
    """Recursively replace ``$ref`` pointers with the referenced definition.

    This allows MCP clients that don't resolve JSON Schema ``$ref`` (e.g.
    Codex) to see the full type information inline.
    """
    if isinstance(node, dict):
        ref = node.get("$ref")
        if ref and ref.startswith("#/$defs/"):
            def_name = ref[len("#/$defs/") :]
            if def_name in defs:
                # Deep-copy to avoid mutating the shared definition, then
                # merge any sibling keys (description, default, etc.) that
                # sat next to the $ref.
                resolved = copy.deepcopy(defs[def_name])
                for k, v in node.items():
                    if k != "$ref":
                        resolved.setdefault(k, v)
                return _inline_refs(resolved, defs)
            return node
        return {k: _inline_refs(v, defs) for k, v in node.items()}
    if isinstance(node, list):
        return [_inline_refs(item, defs) for item in node]
    return node


def input_schema_from_model(model: type[ModelT]) -> dict[str, Any]:
    """Return a JSON Schema dict usable as an MCP Tool ``inputSchema``.

    Applies post-processing to make the schema friendlier for MCP clients
    that don't fully support ``$ref``, ``$defs``, or ``anyOf`` nullable
    patterns.
    """

    schema = model.model_json_schema(mode="validation")

    # Drop Pydantic-specific top-level keys that don't help clients.
    for k in ("title",):
        schema.pop(k, None)

    # Inline all $ref pointers so clients don't need to resolve them.
    defs = schema.get("$defs", {})
    if defs:
        # Simplify anyOf nulls inside $defs before inlining.
        for defn in defs.values():
            _simplify_anyof_nulls(defn)
        schema = _inline_refs(schema, defs)
        schema.pop("$defs", None)

    # Simplify anyOf nullable patterns in top-level properties.
    _simplify_anyof_nulls(schema)

    return schema
