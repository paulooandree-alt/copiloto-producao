from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Copiloto Industrial"
PAGE_ICON = "🏭"

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "copiloto_industrial_saas.db"

PERFIS = ("Administrador", "Supervisor", "Operador")

ADMIN_EMAIL_PADRAO = "admin@copilotoindustrial.com"
ADMIN_SENHA_PADRAO = "admin123"


def obter_segredo(nome: str, padrao: str) -> str:
    valor_env = os.getenv(nome)
    if valor_env:
        return valor_env

    try:
        import streamlit as st

        valor_secret = st.secrets.get(nome)
        if valor_secret:
            return str(valor_secret)
    except Exception:
        pass

    return padrao


def obter_credenciais_admin_inicial() -> tuple[str, str]:
    return (
        obter_segredo("COPILOTO_ADMIN_EMAIL", ADMIN_EMAIL_PADRAO),
        obter_segredo("COPILOTO_ADMIN_PASSWORD", ADMIN_SENHA_PADRAO),
    )
