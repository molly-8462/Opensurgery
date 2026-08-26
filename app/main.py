from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import settings


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PAGES_ROOT = FRONTEND_ROOT / "pages"
ASSETS_ROOT = FRONTEND_ROOT / "assets"
app = FastAPI(title=settings.site_name, version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
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


PUBLIC_PAGES = {path.name for path in PAGES_ROOT.glob("*.html")}


@app.get("/{filename}", include_in_schema=False)
def frontend_file(filename: str):
    if filename not in PUBLIC_PAGES:
        raise HTTPException(404, "Not found")
    return FileResponse(PAGES_ROOT / filename)
