from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

if __name__ == "__main__":
    client = TestClient(app)
    resp = client.get("/openapi.json")
    resp.raise_for_status()
    data = resp.json()
    out = Path(__file__).resolve().parents[1] / "openapi.json"
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {out}")





