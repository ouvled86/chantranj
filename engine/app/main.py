"""Engine service skeleton.

Phase 0: /healthz reports whether the Stockfish binary is reachable.
Phase 5 implements /botmove, /analyse and /review on a bounded UCI process pool.
"""

import os
import shutil

from fastapi import FastAPI, HTTPException

STOCKFISH_PATH = os.environ.get("STOCKFISH_PATH") or shutil.which("stockfish") or "/usr/games/stockfish"

app = FastAPI(title="The Study — Engine Service", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, object]:
    available = shutil.which("stockfish") is not None or os.path.exists(STOCKFISH_PATH)
    return {"status": "ok", "stockfish": available, "path": STOCKFISH_PATH if available else None}


@app.post("/botmove")
def botmove() -> None:
    raise HTTPException(status_code=501, detail="Implemented in Phase 5 (TASKS 5.1-5.2)")


@app.post("/analyse")
def analyse() -> None:
    raise HTTPException(status_code=501, detail="Implemented in Phase 5 (TASKS 5.1)")


@app.post("/review")
def review() -> None:
    raise HTTPException(status_code=501, detail="Implemented in Phase 5 (TASKS 5.4)")
