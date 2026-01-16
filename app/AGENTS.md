## App

Primary FastAPI backend and HTML templates.

### Key areas
- `app/main.py`: app setup and router wiring.
- `app/routes/`: API + admin routes.
- `app/auth.py`: Clerk auth + session handling.
- `app/templates/`: Jinja templates for admin UI.

### Tips
- When changing auth flows, check `app/routes/admin.py` and `app/auth.py` together.
- Templates rely on `static/admin.css` for layout tweaks.

