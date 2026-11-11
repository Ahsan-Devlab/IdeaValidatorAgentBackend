# Saves and loads reports in Supabase. Two small functions.
import secrets
from functools import lru_cache
from supabase import create_client
from app.config import settings

@lru_cache  # build the client once and reuse it, instead of on every request
def _client():
    return create_client(settings.supabase_url, settings.supabase_secret_key)

def save_report(data: dict) -> str:
    report_id = secrets.token_urlsafe(8)   # random short id, hard to guess
    _client().table("reports").insert({"id": report_id, "data": data}).execute()
    return report_id

def get_report(report_id: str) -> dict | None:
    res = (_client().table("reports")
           .select("data")
           .eq("id", report_id)   # WHERE id = report_id
           .limit(1)
           .execute())
    return res.data[0]["data"] if res.data else None   # res.data is a list of rows