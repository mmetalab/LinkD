from fastapi import APIRouter, Request
from services import precompute_overview

router = APIRouter()

# Cache overview data (computed on first request)
_overview_cache = None


@router.get("/overview")
def get_overview(request: Request):
    """Return precomputed overview data (stats, charts, table)."""
    global _overview_cache
    # Try app.state first (set by lifespan), fallback to lazy compute
    try:
        return request.app.state.overview
    except AttributeError:
        if _overview_cache is None:
            _overview_cache = precompute_overview()
        return _overview_cache
