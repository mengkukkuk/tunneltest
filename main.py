"""
Minimal FastAPI backend to test PostgreSQL connectivity.
Run locally, expose via Cloudflare Tunnel, call from GitHub Pages frontend
through a Cloudflare Worker proxy.
"""
import os
import time
from datetime import datetime

import psycopg2
import pydotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config — set these via environment variables (recommended) or edit defaults
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "tunnel")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "P@ssw0rd")

app = FastAPI(title="SCADA Deploy Test API")

# CORS: allow the Cloudflare Worker / GitHub Pages origin to call this API.
# For initial testing "*" is fine; lock this down to your real domain later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        connect_timeout=5,
    )


class PingResponse(BaseModel):
    status: str
    message: str
    timestamp: str


@app.get("/")
def root():
    return {"service": "scada-deploy-test", "status": "running"}


@app.get("/health")
def health():
    """Basic liveness check — does NOT touch the database."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/db-check", response_model=PingResponse)
def db_check():
    """
    Actually opens a connection to PostgreSQL and runs SELECT 1.
    This is the real test of whether deploy -> tunnel -> local -> db works.
    """
    start = time.time()
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        elapsed_ms = round((time.time() - start) * 1000, 1)
        return PingResponse(
            status="success",
            message=f"Connected OK in {elapsed_ms}ms. {version}",
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
