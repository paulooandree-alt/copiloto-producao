from __future__ import annotations

import streamlit as st

from copiloto.auth.service import autenticar_usuario
from copiloto.core.config import APP_NAME, PAGE_ICON
from copiloto.core.database import inicializar_banco
from copiloto.ui.layout import aplicar_estilos, render_sidebar
from copiloto.ui.pages.dashboard import render_dashboard
from copiloto.ui.pages.login import render_login
from copiloto.ui.pages.placeholder import render_placeholder
from copiloto.ui.pages.settings import render_settings


def configurar_pagina() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inicializar_sessao() -> None:
    st.session_state.setdefault("usuario", None)
    st.session_state.setdefault("pagina_atual", "Dashboard")


def run() -> None:
    configurar_pagina()
    inicializar_banco()
    inicializar_sessao()
    aplicar_estilos()

    if not st.session_state.usuario:
        render_login(autenticar_usuario)
        return

    pagina = render_sidebar(st.session_state.usuario)

    if pagina == "Dashboard":
        render_dashboard(st.session_state.usuario)
    elif pagina == "Configurações":
        render_settings(st.session_state.usuario)
    else:
        render_placeholder(pagina)


if __name__ == "__main__":
    run()
