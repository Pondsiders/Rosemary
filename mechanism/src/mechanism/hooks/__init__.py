"""HTTP hook handlers for Claude Code's hook surface.

Hook modules register their handlers against the shared `router` via
`@router.post(...)` decorators. Importing each module is what causes
the registration to fire; `app.py` does side-effect imports of every
hook module so that mounting `router` picks up the full hook surface.

Mirrors the pattern used by `cortex/__init__.py` for MCP tools.
"""

from fastapi import APIRouter

router: APIRouter = APIRouter()
