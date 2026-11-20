"""FastAPI service: analyse an Android app with the per-category RL privacy models."""
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import playstore
from .model import CATEGORY_LABELS, GENRE_TO_CATEGORY, Registry

app = FastAPI(title="PermiSense API", version="1.0.0",
              description="Malicious-app detection and permission recommendations from six category RL models.")
app.add_middleware(CORSMiddleware, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["GET", "POST"], allow_headers=["*"])
registry = Registry()


class AppInput(BaseModel):
    category: Optional[str] = Field(None, description="Category key; derived from genre when omitted")
    genre: Optional[str] = Field(None, description="Dataset genre, e.g. 'Education' or 'Arcade & Action'")
    app_name: str = ""
    package: str = ""
    description: str = ""
    related_apps: str = ""
    rating: float = Field(0.0, ge=0, le=5)
    num_ratings: float = Field(0.0, ge=0)
    price: float = Field(0.0, ge=0)
    permissions: List[str] = Field(default_factory=list, description="Dataset permission labels")
    permission_groups: List[str] = Field(default_factory=list, description="Permission groups such as 'Camera'")


class UrlInput(BaseModel):
    url: str
    category: Optional[str] = Field(None, description="Override when the Play Store genre is not covered")


def _resolve_category(app_in):
    key = app_in.get("category") or GENRE_TO_CATEGORY.get(app_in.get("genre") or "")
    if not key:
        raise HTTPException(422, "Choose a category: it could not be derived from the genre.")
    if key not in registry.available():
        raise HTTPException(422, f"Unknown or unavailable category '{key}'.")
    cfg = registry.config(key)
    if app_in.get("genre") not in cfg["genres"]:   # every training app has one of the category's genres
        app_in["genre"] = cfg["genres"][0]
    return key


def _run(app_in, trust=0.0):
    key = _resolve_category(app_in)
    return registry.get(key).analyze(app_in, trust=trust)


@app.get("/api/health")
def health():
    return {"status": "ok", "categories": registry.available()}


@app.get("/api/categories")
def categories():
    out = []
    for key in registry.available():
        cfg = registry.config(key)
        out.append({
            "key": key, "label": CATEGORY_LABELS[key], "genres": cfg["genres"],
            "permissions": [{"name": p, "weight": cfg["weight_map"].get(p, 0.0), "utility": cfg["utility_map"][p],
                             "raw": cfg["permission_column_map"].get(p, [])} for p in cfg["rl_features"]],
            "test_metrics": cfg["test_metrics"], "rules": len(cfg["rules"]),
            "coefficients": {"alpha": cfg["alpha"], "beta": cfg["beta"], "gamma": cfg["gamma"]},
            "threshold": cfg["threshold"], "risk_model": cfg["risk_model_name"],
        })
    return out


@app.get("/api/permissions")
def permissions():
    keys = registry.available()
    if not keys:
        raise HTTPException(503, "No models are exported yet.")
    cfg = registry.config(keys[0])
    raw_to_group = {c: g for g, cols in cfg["permission_column_map"].items() for c in cols}
    sections = {}
    for col in cfg["raw_permission_columns"]:
        section, _, label = col.partition(" : ")
        sections.setdefault(section, []).append({"id": col, "label": label, "group": raw_to_group.get(col)})
    return {"sections": sections}


@app.get("/api/categories/{key}/examples")
def examples(key: str):
    if key not in registry.available():
        raise HTTPException(404, "Unknown category")
    cfg = registry.config(key)
    return [{k: v for k, v in e.items() if k != "notebook"} | {"category": key} for e in cfg["examples"]]


@app.post("/api/analyze")
def analyze(body: AppInput):
    app_in = body.model_dump()
    return {"input": app_in, "result": _run(app_in)}


@app.post("/api/analyze-url")
def analyze_url(body: UrlInput):
    try:
        fetched = playstore.fetch(body.url)
    except playstore.PlayStoreError as e:
        raise HTTPException(422, str(e))
    app_in = fetched["app"]
    if body.category:
        app_in["category"] = body.category
    if not app_in.get("category"):
        return {"input": app_in, "store": fetched["store"], "result": None,
                "message": f"Google Play genre '{fetched['store']['genre']}' is not one of the six categories. "
                           "Choose a category to continue."}
    return {"input": app_in, "store": fetched["store"], "result": _run(app_in, fetched["reputation"]["trust"])}


# ---------------------------------------------------------------------- website
DIST = os.environ.get("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.isdir(DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = os.path.join(DIST, path)
        if path and os.path.isfile(target):
            return FileResponse(target)
        # index.html must never be cached, so a new deployment's hashed assets are picked up at once.
        return FileResponse(os.path.join(DIST, "index.html"), headers={"Cache-Control": "no-cache"})
