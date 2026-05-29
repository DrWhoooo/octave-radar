import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def _get(name: str) -> str:
    try:
        value = st.secrets.get(name, "")
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name, "")

def get_client():
    url = _get("SUPABASE_URL")
    key = _get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY sont requis.")
    return create_client(url, key)
