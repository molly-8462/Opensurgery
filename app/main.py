from pathlib import Path
from time import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .api import router
from .config import settings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PAGES_ROOT = FRONTEND_ROOT / "pages"
ASSETS_ROOT = FRONTEND_ROOT / "assets"
app = FastAPI(title=settings.site_name, version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 30, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.rate_limited_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/password-reset",
            "/api/v1/media",
            "/api/v1/messages",
        }

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.rate_limited_paths and request.method == "POST":
            client_ip = request.client.host if request.client else "127.0.0.1"
            now = time()
            timestamps = [t for t in self.requests[client_ip] if now - t < self.window_seconds]
            if len(timestamps) >= self.max_requests:
                return Response(content='{"detail":"Rate limit exceeded. Please try again later."}', status_code=429, media_type="application/json")
            timestamps.append(now)
            self.requests[client_ip] = timestamps
        return await call_next(request)


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(router)
app.mount("/assets", StaticFiles(directory=ASSETS_ROOT), name="assets")


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(PAGES_ROOT / "home.html")


SURGEON_PAGE_FILES = {
    "info": "index.html",
    "reviews": "reviews.html",
    "talk": "talk.html",
    "edit": "edit.html",
    "history": "history.html",
}


@app.get("/surgeons/{slug}", include_in_schema=False)
def surgeon_profile_page(slug: str):
    """Serve the profile shell; the slug remains in the path for client hydration."""
    return FileResponse(PAGES_ROOT / SURGEON_PAGE_FILES["info"])


@app.get("/surgeons/{slug}/{section}", include_in_schema=False)
def surgeon_section_page(slug: str, section: str):
    filename = SURGEON_PAGE_FILES.get(section)
    if not filename:
        raise HTTPException(404, "Not found")
    return FileResponse(PAGES_ROOT / filename)


@app.get("/surgeon.html", include_in_schema=False)
def legacy_surgeon_page():
    return FileResponse(PAGES_ROOT / "index.html")


PUBLIC_PAGES = {path.name for path in PAGES_ROOT.glob("*.html")}


@app.get("/{filename}", include_in_schema=False)
def frontend_file(filename: str):
    if filename not in PUBLIC_PAGES:
        raise HTTPException(404, "Not found")
    return FileResponse(PAGES_ROOT / filename)
