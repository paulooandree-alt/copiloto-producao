from __future__ import annotations

from pathlib import Path

APP_NAME = "Copiloto Industrial"
PAGE_ICON = "🏭"

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "copiloto_industrial_saas.db"

PERFIS = ("Administrador", "Supervisor", "Operador")

ADMIN_EMAIL_PADRAO = "admin@copilotoindustrial.com"
ADMIN_SENHA_PADRAO = "admin123"
