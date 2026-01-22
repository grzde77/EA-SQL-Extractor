from fastapi import FastAPI, HTTPException, Header
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

def get_conn():
    # W OpenShift weźmiemy to z Secret jako EA_SQL_CONN_STR
    return pyodbc.connect(os.environ["EA_SQL_CONN_STR"], timeout=5)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/ea/sql")
def run_sql(req: SQLRequest, x_api_key: str = Header(default=None)):
    # prosta autoryzacja (polecane)
    expected = os.environ.get("API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(401, "Unauthorized")

    sql = (req.query or "").strip()

    # bezpieczeństwo: tylko SELECT
    if not sql.lower().startswith("select"):
        raise HTTPException(400, "Only SELECT allowed")
    if FORBIDDEN.search(sql):
        raise HTTPException(400, "Forbidden SQL keyword detected")

    # opcjonalnie: limit wyników na backendzie (jeśli LLM zapomni TOP)
    # możesz to wymuszać regexem, ale na start zostawiamy walidację w Pipe + tu tylko guard.

    try:
        conn = get_conn()
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
