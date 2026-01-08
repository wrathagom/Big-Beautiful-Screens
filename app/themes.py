"""Pre-defined themes for screen styling."""

THEMES = {
    # ============== General Purpose Themes ==============
    "default": {
        # Deep purple with magenta and blue accents
        "background_color": "linear-gradient(135deg, #0f0c29 0%, rgba(139, 92, 246, 0.25) 30%, rgba(236, 72, 153, 0.2) 70%, #24243e 100%)",
        "panel_color": "rgba(255, 255, 255, 0.1)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#f0f0f0",
        "gap": "1.25rem",
        "border_radius": "1rem",
        "panel_shadow": "0 8px 32px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1)",
    },
    "minimal": {
        # Clean white with subtle warm rose tint
        "background_color": "linear-gradient(135deg, #ffffff 0%, rgba(251, 207, 232, 0.15) 50%, #f8f9fa 100%)",
        "panel_color": "rgba(255, 255, 255, 0.9)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#212529",
        "gap": "2rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 2px 8px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04)",
    },
    "elegant": {
        # Deep purple with gold/amber accents for luxury feel
        "background_color": "linear-gradient(135deg, #1a1a2e 0%, rgba(217, 175, 106, 0.15) 30%, rgba(139, 92, 246, 0.2) 70%, #1a1a2e 100%)",
        "panel_color": "rgba(255, 255, 255, 0.08)",
        "font_family": "Georgia, 'Times New Roman', serif",
        "font_color": "#f0e6d3",
        "gap": "1.5rem",
        "border_radius": "0.5rem",
        "panel_shadow": "0 8px 32px rgba(45, 27, 78, 0.4), inset 0 1px 0 rgba(217, 175, 106, 0.1)",
    },
    "modern": {
        # Pure black with subtle cyan accent
        "background_color": "linear-gradient(180deg, #0a0a0a 0%, rgba(6, 182, 212, 0.1) 50%, #0a0a0a 100%)",
        "panel_color": "linear-gradient(135deg, rgba(30, 30, 30, 0.95) 0%, rgba(20, 20, 20, 0.95) 100%)",
        "font_family": "Inter, system-ui, sans-serif",
        "font_color": "#fafafa",
        "gap": "0.5rem",
        "border_radius": "0",
        "panel_shadow": "0 1px 0 rgba(6, 182, 212, 0.1)",
    },
    "mono": {
        # GitHub-style with blue and green accents
        "background_color": "linear-gradient(135deg, #0d1117 0%, rgba(88, 166, 255, 0.15) 40%, rgba(63, 185, 80, 0.1) 70%, #0d1117 100%)",
        "panel_color": "linear-gradient(135deg, rgba(22, 27, 34, 0.95) 0%, rgba(13, 17, 23, 0.95) 100%)",
        "font_family": "'JetBrains Mono', 'Fira Code', 'Consolas', monospace",
        "font_color": "#c9d1d9",
        "gap": "1rem",
        "border_radius": "0.375rem",
        "panel_shadow": "0 4px 16px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(88, 166, 255, 0.15)",
    },
    # ============== Catppuccin ==============
    # https://github.com/catppuccin/catppuccin
    # Accents: Mauve #cba6f7, Pink #f5c2e7, Lavender #b4befe, Blue #89b4fa, Peach #fab387
    "catppuccin-mocha": {
        "background_color": "linear-gradient(135deg, #1e1e2e 0%, rgba(203, 166, 247, 0.25) 25%, rgba(245, 194, 231, 0.2) 50%, rgba(137, 180, 250, 0.2) 75%, #11111b 100%)",
        "panel_color": "linear-gradient(135deg, rgba(49, 50, 68, 0.9) 0%, rgba(203, 166, 247, 0.1) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#cdd6f4",
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 8px 24px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(245, 194, 231, 0.15)",
    },
    # Accents: Mauve #8839ef, Pink #ea76cb, Blue #1e66f5, Lavender #7287fd
    "catppuccin-latte": {
        "background_color": "linear-gradient(135deg, #eff1f5 0%, rgba(234, 118, 203, 0.2) 30%, rgba(136, 57, 239, 0.15) 60%, #dce0e8 100%)",
        "panel_color": "linear-gradient(135deg, rgba(204, 208, 218, 0.8) 0%, rgba(136, 57, 239, 0.08) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#4c4f69",
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 4px 16px rgba(76, 79, 105, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.8)",
    },
    # ============== Solarized ==============
    # https://ethanschoonover.com/solarized/
    # Accents: Yellow #b58900, Orange #cb4b16, Red #dc322f, Magenta #d33682, Cyan #2aa198, Blue #268bd2
    "solarized-dark": {
        "background_color": "linear-gradient(135deg, #002b36 0%, rgba(42, 161, 152, 0.25) 30%, rgba(38, 139, 210, 0.2) 70%, #002b36 100%)",
        "panel_color": "linear-gradient(135deg, rgba(7, 54, 66, 0.95) 0%, rgba(42, 161, 152, 0.1) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#839496",
        "gap": "1rem",
        "border_radius": "0.375rem",
        "panel_shadow": "0 4px 16px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(42, 161, 152, 0.2)",
    },
    "solarized-light": {
        "background_color": "linear-gradient(135deg, #fdf6e3 0%, rgba(181, 137, 0, 0.2) 30%, rgba(203, 75, 22, 0.15) 70%, #eee8d5 100%)",
        "panel_color": "linear-gradient(135deg, rgba(238, 232, 213, 0.9) 0%, rgba(181, 137, 0, 0.08) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#657b83",
        "gap": "1rem",
        "border_radius": "0.375rem",
        "panel_shadow": "0 2px 8px rgba(0, 0, 0, 0.08), inset 0 1px 0 rgba(181, 137, 0, 0.15)",
    },
    # ============== Dracula ==============
    # https://draculatheme.com/
    # Accents: Pink #ff79c6, Cyan #8be9fd, Green #50fa7b, Purple #bd93f9, Orange #ffb86c
    "dracula": {
        "background_color": "linear-gradient(135deg, #282a36 0%, rgba(255, 121, 198, 0.25) 25%, rgba(139, 233, 253, 0.2) 50%, rgba(189, 147, 249, 0.25) 75%, #282a36 100%)",
        "panel_color": "linear-gradient(135deg, rgba(68, 71, 90, 0.9) 0%, rgba(255, 121, 198, 0.1) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#f8f8f2",
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 8px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(139, 233, 253, 0.2)",
    },
    # ============== Nord ==============
    # https://www.nordtheme.com/
    # Frost: #8fbcbb, #88c0d0, #81a1c1, #5e81ac; Aurora: Red #bf616a, Orange #d08770, Yellow #ebcb8b, Green #a3be8c, Purple #b48ead
    "nord": {
        "background_color": "linear-gradient(135deg, #2e3440 0%, rgba(136, 192, 208, 0.2) 20%, rgba(163, 190, 140, 0.15) 40%, rgba(235, 203, 139, 0.15) 60%, rgba(180, 142, 173, 0.2) 80%, #2e3440 100%)",
        "panel_color": "linear-gradient(135deg, rgba(59, 66, 82, 0.9) 0%, rgba(136, 192, 208, 0.1) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#eceff4",
        "gap": "1rem",
        "border_radius": "0.5rem",
        "panel_shadow": "0 4px 16px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(136, 192, 208, 0.2)",
    },
    # ============== Gruvbox ==============
    # https://github.com/morhetz/gruvbox
    # Accents: Red #cc241d, Orange #d65d0e, Yellow #d79921, Green #98971a, Aqua #689d6a, Blue #458588, Purple #b16286
    "gruvbox-dark": {
        "background_color": "linear-gradient(135deg, #282828 0%, rgba(214, 93, 14, 0.25) 25%, rgba(215, 153, 33, 0.2) 50%, rgba(104, 157, 106, 0.2) 75%, #1d2021 100%)",
        "panel_color": "linear-gradient(135deg, rgba(60, 56, 54, 0.9) 0%, rgba(214, 93, 14, 0.1) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#ebdbb2",
        "gap": "1rem",
        "border_radius": "0.25rem",
        "panel_shadow": "0 4px 16px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(215, 153, 33, 0.2)",
    },
    # ============== Tokyo Night ==============
    # https://github.com/enkia/tokyo-night-vscode-theme
    # Accents: Magenta #bb9af7, Blue #7aa2f7, Cyan #7dcfff, Green #9ece6a, Yellow #e0af68, Orange #ff9e64
    "tokyo-night": {
        "background_color": "linear-gradient(135deg, #1a1b26 0%, rgba(187, 154, 247, 0.25) 25%, rgba(122, 162, 247, 0.2) 50%, rgba(125, 207, 255, 0.2) 75%, #1a1b26 100%)",
        "panel_color": "linear-gradient(135deg, rgba(36, 40, 59, 0.9) 0%, rgba(187, 154, 247, 0.1) 100%)",
        "font_family": "system-ui, -apple-system, sans-serif",
        "font_color": "#a9b1d6",
        "gap": "1rem",
        "border_radius": "0.75rem",
        "panel_shadow": "0 8px 24px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(122, 162, 247, 0.2)",
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
