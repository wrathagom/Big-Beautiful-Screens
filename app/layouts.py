"""Layout presets for panel arrangement."""

LAYOUT_PRESETS = {
    # ============== Auto (backward compatible) ==============
    "auto": {
        "description": "Auto-detect based on content count (current behavior)",
    },
    # ============== Vertical stacking (single column) ==============
    "vertical": {
        "columns": 1,
        "description": "Single column, rows auto-expand to fit content count",
    },
    "vertical-6": {
        "columns": 1,
        "rows": 6,
        "description": "Single column, fixed 6 rows",
    },
    "vertical-8": {
        "columns": 1,
        "rows": 8,
        "description": "Single column, fixed 8 rows",
    },
    "vertical-10": {
        "columns": 1,
        "rows": 10,
        "description": "Single column, fixed 10 rows",
    },
    "vertical-12": {
        "columns": 1,
        "rows": 12,
        "description": "Single column, fixed 12 rows",
    },
    # ============== Horizontal (single row) ==============
    "horizontal": {
        "rows": 1,
        "description": "Single row, columns auto-expand to fit content count",
    },
    "horizontal-4": {
        "columns": 4,
        "rows": 1,
        "description": "Single row, fixed 4 columns",
    },
    "horizontal-6": {
        "columns": 6,
        "rows": 1,
        "description": "Single row, fixed 6 columns",
    },
    # ============== Standard grids ==============
    "grid-2x2": {
        "columns": 2,
        "rows": 2,
        "description": "2 columns, 2 rows (4 panels)",
    },
    "grid-3x2": {
        "columns": 3,
        "rows": 2,
        "description": "3 columns, 2 rows (6 panels)",
    },
    "grid-2x3": {
        "columns": 2,
        "rows": 3,
        "description": "2 columns, 3 rows (6 panels)",
    },
    "grid-3x3": {
        "columns": 3,
        "rows": 3,
        "description": "3 columns, 3 rows (9 panels)",
    },
    "grid-4x3": {
        "columns": 4,
        "rows": 3,
        "description": "4 columns, 3 rows (12 panels)",
    },
    "grid-4x4": {
        "columns": 4,
        "rows": 4,
        "description": "4 columns, 4 rows (16 panels)",
    },
    # ============== Dashboard layouts (header/footer span full width) ==============
    "dashboard-header": {
        "columns": 3,
        "rows": "auto 1fr 1fr",
        "header_rows": 1,
        "description": "Full-width header, 3-column grid below",
    },
    "dashboard-footer": {
        "columns": 3,
        "rows": "1fr 1fr auto",
        "footer_rows": 1,
        "description": "3-column grid with full-width footer",
    },
    "dashboard-both": {
        "columns": 3,
        "rows": "auto 1fr 1fr auto",
        "header_rows": 1,
        "footer_rows": 1,
        "description": "Header and footer with 3-column grid in between",
    },
    # ============== Menu/schedule layouts ==============
    "menu-board": {
        "columns": 2,
        "rows": "auto 1fr 1fr 1fr 1fr 1fr 1fr",
        "header_rows": 1,
        "description": "Title header with 2-column menu items",
    },
    "menu-3col": {
        "columns": 3,
        "rows": "auto 1fr 1fr 1fr 1fr",
        "header_rows": 1,
        "description": "Title header with 3-column menu items",
    },
    "schedule": {
        "columns": 1,
        "rows": "auto 1fr 1fr 1fr 1fr 1fr 1fr 1fr 1fr",
        "header_rows": 1,
        "description": "Title header with stacked schedule rows",
    },
    # ============== Featured/sidebar layouts ==============
    "featured-top": {
        "columns": 3,
        "rows": "2fr 1fr",
        "header_rows": 1,
        "description": "Large header spanning full width, smaller panels below",
    },
    "sidebar-left": {
        "columns": "1fr 3fr",
        "description": "Narrow left sidebar with main content area",
    },
    "sidebar-right": {
        "columns": "3fr 1fr",
        "description": "Main content area with narrow right sidebar",
    },
}


def get_layout_preset(name: str) -> dict | None:
    """Get a layout preset by name."""
    return LAYOUT_PRESETS.get(name)


def list_layout_presets() -> list[dict]:
    """List all available layout presets."""
    return [{"name": name, **config} for name, config in LAYOUT_PRESETS.items()]


def resolve_layout(layout: str | dict | None, content_count: int) -> dict:
    """
    Resolve a layout specification to a concrete layout config.

    Args:
        layout: Layout preset name (str), config dict, or None for auto
        content_count: Number of content items

    Returns:
        Resolved layout config dict with 'type' key
    """
    # No layout = backward compatible auto-detection
    if layout is None:
        return {"type": "auto", "panel_count": min(content_count, 6)}

    # String = preset name
    if isinstance(layout, str):
        preset = LAYOUT_PRESETS.get(layout)
        if preset:
            # Special case: 'auto' preset
            if layout == "auto":
                return {"type": "auto", "panel_count": min(content_count, 6)}
            return {"type": "custom", **{k: v for k, v in preset.items() if k != "description"}}
        # Unknown preset, fall back to auto
        return {"type": "auto", "panel_count": content_count}

    # Dict = full layout config (could be LayoutConfig model serialized)
    if isinstance(layout, dict):
        # Check if it's using a preset
        if "preset" in layout and layout["preset"]:
            preset = LAYOUT_PRESETS.get(layout["preset"])
            if preset:
                # Merge preset with overrides
                config = {k: v for k, v in preset.items() if k != "description"}
                config.update({k: v for k, v in layout.items() if v is not None and k != "preset"})
                return {"type": "custom", **config}

        return {"type": "custom", **{k: v for k, v in layout.items() if v is not None}}

    # Fallback
    return {"type": "auto", "panel_count": content_count}
