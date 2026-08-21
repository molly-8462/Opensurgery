from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import router


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PAGES_ROOT = FRONTEND_ROOT / "pages"
ASSETS_ROOT = FRONTEND_ROOT / "assets"
app = FastAPI(title="OpenSurgery", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(router)
app.mount("/assets", StaticFiles(directory=ASSETS_ROOT), name="assets")


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(PAGES_ROOT / "home.html")


PUBLIC_PAGES = {path.name for path in PAGES_ROOT.glob("*.html")}


@app.get("/{filename}", include_in_schema=False)
def frontend_file(filename: str):
    if filename not in PUBLIC_PAGES:
        raise HTTPException(404, "Not found")
    return FileResponse(PAGES_ROOT / filename)
