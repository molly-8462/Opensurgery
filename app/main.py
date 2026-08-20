from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .api import router


ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="OpenSurgery", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(router)


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(ROOT / "home.html")


PUBLIC_FILES = {path.name for pattern in ("*.html", "*.css", "*.js") for path in ROOT.glob(pattern)}
PUBLIC_FILES.add("history-export.json")


@app.get("/{filename}", include_in_schema=False)
def frontend_file(filename: str):
    if filename not in PUBLIC_FILES:
        raise HTTPException(404, "Not found")
    return FileResponse(ROOT / filename)
