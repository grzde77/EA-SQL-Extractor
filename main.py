from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pyodbc
import os
import re

app = FastAPI(title="EA SQL Executor")

FORBIDDEN = re.compile(
    r"\b(update|delete|insert|drop|alter|create|truncate|merge|exec|grant|revoke)\b",
    re.IGNORECASE
)

class SQLRequest(BaseModel):
    query: str

def conn_str() -> str:
    # Option 1: full connection string from env (simplest)
    if os.environ.get("EA_SQL_CONN_STR"):
        return os.environ["EA_SQL_CONN_STR"]

    # Option 2: build from parts
    server = os.environ["EA_DB_SERVER"]      # e.g. mssql.example.local,1433
    db = os.environ["EA_DB_NAME"]            # e.g. EA_DB
    user = os.environ["EA_DB_USER"]
    pwd = os.environ["EA_DB_PASSWORD"]

    # Encrypt/Trust settings depend on your SQL Server config
    return (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};"
        f"DATABASE={db};"
        f"UID={user};"
        f"PWD={pwd};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/ea/sql")
def run_sql(req: SQLRequest):
    sql = (req.query or "").strip()

    # Security: only SELECT
    if not sql.lower().startswith("select"):
        raise HTTPException(400, "Only SELECT allowed")
    if FORBIDDEN.search(sql):
        raise HTTPException(400, "Forbidden SQL keyword detected")

    try:
        conn = pyodbc.connect(conn_str(), timeout=5)
        cur = conn.cursor()
        cur.execute(sql)

        cols = [c[0] for c in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()] if cols else []

        return {"columns": cols, "rows": rows}

    except Exception as e:
        raise HTTPException(500, str(e))

    finally:
        try:
            conn.close()
        except:
            pass
