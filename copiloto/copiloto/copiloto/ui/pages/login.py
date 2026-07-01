from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from copiloto.auth.models import Usuario
from copiloto.core.config import APP_NAME


def render_login(
    autenticar: Callable[[str, str], tuple[bool, Usuario | None, str]],
) -> None:
    st.markdown('<div class="login-shell">', unsafe_allow_html=True)
    st.markdown(f"## {APP_NAME}")
    st.caption("Acesse sua operação industrial")

    with st.form("form_login"):
        email = st.text_input("E-mail", placeholder="seu.email@empresa.com")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        entrar = st.form_submit_button("Entrar", use_container_width=True)

    if entrar:
        sucesso, usuario, mensagem = autenticar(email, senha)
        if sucesso and usuario:
            st.session_state.usuario = usuario
            st.success(mensagem)
            st.rerun()
        else:
            st.error(mensagem)

    st.markdown("</div>", unsafe_allow_html=True)
