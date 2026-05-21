import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    odoo_url = os.environ.get("ODOO_URL", "http://web:8069")
    odoo_db = os.environ.get("ODOO_DB", "")
    odoo_user = os.environ.get("ODOO_USER", "")
    odoo_password = os.environ.get("ODOO_PASSWORD", "")
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    search_token = os.environ.get("SEARCH_TOKEN", "")
    sync_interval_min = int(os.environ.get("SYNC_INTERVAL_MIN", "5"))
    reconcile_every = int(os.environ.get("RECONCILE_EVERY", "12"))
    embed_model = os.environ.get("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    chroma_path = os.environ.get("CHROMA_PATH", "/data/chroma")
    top_k = int(os.environ.get("TOP_K", "10"))


settings = Settings()
