"""Pre-defined themes for screen styling."""

THEMES = {
    # ============== General Purpose Themes ==============
    "default": {
        "background_color": "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
        "panel_color": "rgba(255, 255, 255, 0.1)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#f0f0f0",
        "gap": "1.25rem",
        "border_radius": "1rem",
        "panel_shadow": "0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)",
    },
    "minimal": {
        "background_color": "#ffffff",
        "panel_color": "#f8f9fa",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#212529",
        "gap": "2rem",
        "border_radius": "0.5rem",
        "panel_shadow": None,
    },
    "elegant": {
        "background_color": "linear-gradient(135deg, #1a1a2e 0%, #2d1b4e 100%)",
        "panel_color": "rgba(255, 255, 255, 0.08)",
        "font_family": "Georgia, 'Times New Roman', serif",
        "font_color": "#f0e6d3",
        "gap": "1.5rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 8px 32px rgba(0, 0, 0, 0.3)",
    },
    "modern": {
        "background_color": "#0a0a0a",
        "panel_color": "#1a1a1a",
        "font_family": "Inter, system-ui, sans-serif",
        "font_color": "#fafafa",
        "gap": "0.75rem",
        "border_radius": "0",
        "panel_shadow": "0 1px 3px rgba(0, 0, 0, 0.5)",
    },
    "mono": {
        "background_color": "#0d1117",
        "panel_color": "#161b22",
        "font_family": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
        "font_color": "#c9d1d9",
        "gap": "1rem",
        "border_radius": "0.5rem",
        "panel_shadow": None,
    },
    # ============== Catppuccin ==============
    # https://github.com/catppuccin/catppuccin
    "catppuccin-mocha": {
        "background_color": "#1e1e2e",  # Base
        "panel_color": "#313244",  # Surface0
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#cdd6f4",  # Text
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 4px 12px rgba(0, 0, 0, 0.4)",
    },
    "catppuccin-latte": {
        "background_color": "#eff1f5",  # Base
        "panel_color": "#ccd0da",  # Surface0
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#4c4f69",  # Text
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
    },
    # ============== Solarized ==============
    # https://ethanschoonover.com/solarized/
    "solarized-dark": {
        "background_color": "#002b36",  # base03
        "panel_color": "#073642",  # base02
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#839496",  # base0
        "gap": "1rem",
        "border_radius": "0.5rem",
        "panel_shadow": None,
    },
    "solarized-light": {
        "background_color": "#fdf6e3",  # base3
        "panel_color": "#eee8d5",  # base2
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#657b83",  # base00
        "gap": "1rem",
        "border_radius": "0.5rem",
        "panel_shadow": None,
    },
    # ============== Dracula ==============
    # https://draculatheme.com/
    "dracula": {
        "background_color": "#282a36",  # Background
        "panel_color": "#44475a",  # Current Line
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#f8f8f2",  # Foreground
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 4px 16px rgba(0, 0, 0, 0.4)",
    },
    # ============== Nord ==============
    # https://www.nordtheme.com/
    "nord": {
        "background_color": "#2e3440",  # Polar Night nord0
        "panel_color": "#3b4252",  # Polar Night nord1
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#eceff4",  # Snow Storm nord6
        "gap": "1rem",
        "border_radius": "0.5rem",
        "panel_shadow": "0 2px 8px rgba(0, 0, 0, 0.3)",
    },
    # ============== Gruvbox ==============
    # https://github.com/morhetz/gruvbox
    "gruvbox-dark": {
        "background_color": "#282828",  # bg
        "panel_color": "#3c3836",  # bg1
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#ebdbb2",  # fg
        "gap": "1rem",
        "border_radius": "0.5rem",
        "panel_shadow": None,
    },
    # ============== Tokyo Night ==============
    # https://github.com/enkia/tokyo-night-vscode-theme
    "tokyo-night": {
        "background_color": "#1a1b26",  # bg
        "panel_color": "#24283b",  # bg_highlight
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#a9b1d6",  # fg
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 4px 12px rgba(0, 0, 0, 0.4)",
    },
}


def get_theme(name: str) -> dict | None:
    """Get a theme by name from hardcoded dict. Returns None if not found.

    NOTE: This is a sync fallback. Use get_theme_async() for database lookup.
    """
    return THEMES.get(name)


def list_themes() -> list[dict]:
    """List all available themes from hardcoded dict.

    NOTE: This is a sync fallback. Use list_themes_async() for database lookup.
    """
    return [{"name": name, **values} for name, values in THEMES.items()]


def get_theme_names() -> list[str]:
    """Get just the theme names from hardcoded dict."""
    return list(THEMES.keys())


def get_builtin_themes() -> dict:
    """Get the built-in themes dict for database seeding."""
    return THEMES.copy()


# ============== Async Database-Backed Functions ==============


async def get_theme_async(name: str) -> dict | None:
    """Get a theme by name from database. Returns None if not found."""
    # Import here to avoid circular import
    from .database import get_theme_from_db

    return await get_theme_from_db(name)


async def list_themes_async() -> list[dict]:
    """List all available themes from database."""
    # Import here to avoid circular import
    from .database import get_all_themes

    return await get_all_themes()
