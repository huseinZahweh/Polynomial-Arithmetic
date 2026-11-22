"""Load the course milestones together and serve the browser workbench."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / path) for path in (
    "milestone2/milestone2", "milestone1", "milestone3",
)]

from fastapi.staticfiles import StaticFiles
from app.main import app
from explorations import router as explorations_router


app.include_router(explorations_router)
app.mount("/workbench", StaticFiles(directory=ROOT / "web", html=True), name="workbench")
