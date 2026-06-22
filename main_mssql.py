"""
Minimal FastAPI backend to test MSSQL (SQL Server) connectivity.
Run locally, expose via Cloudflare Tunnel, call from GitHub Pages frontend
through a Cloudflare Worker proxy.

Requires the ODBC Driver for SQL Server installed on the host machine:
- Windows: usually already present, or install "ODBC Driver 17/18 for SQL Server"
- Linux: install msodbcsql17/18 + unixodbc (see README)
"""
import os
import time
from datetime import datetime

import pyodbc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config — set these via environment variables (recommended) or edit defaults
# ---------------------------------------------------------------------------
DB_SERVER = os.getenv("DB_SERVER", "localhost")        # e.g. "localhost\\SQLEXPRESS" or "localhost,1433"
DB_NAME = os.getenv("DB_NAME", "master")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_TRUST_CERT = os.getenv("DB_TRUST_CERT", "yes")        # "yes" for self-signed/dev, "no" for prod with valid cert

app = FastAPI(title="SCADA Deploy Test API (MSSQL)")

# CORS: allow the Cloudflare Worker / GitHub Pages origin to call this API.
# For initial testing "*" is fine; lock this down to your real domain later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate={DB_TRUST_CERT};"
        f"Connection Timeout=5;"
    )
    return pyodbc.connect(conn_str)


class PingResponse(BaseModel):
    status: str
    message: str
    timestamp: str


@app.get("/")
def root():
    return {"service": "scada-deploy-test-mssql", "status": "running"}


@app.get("/health")
def health():
    """Basic liveness check — does NOT touch the database."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/db-check", response_model=PingResponse)
def db_check():
    """
    Actually opens a connection to MSSQL and runs SELECT @@VERSION.
    This is the real test of whether deploy -> tunnel -> local -> db works.
    """
    start = time.time()
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT @@VERSION;")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        elapsed_ms = round((time.time() - start) * 1000, 1)
        # @@VERSION returns a long multi-line string — keep just the first line
        version_short = version.splitlines()[0]
        return PingResponse(
            status="success",
            message=f"Connected OK in {elapsed_ms}ms. {version_short}",
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
