from __future__ import annotations

import streamlit as st

from copiloto.auth.models import Usuario
from copiloto.core.config import APP_NAME


MENU_ITEMS = [
    ("🏠", "Dashboard", False),
    ("🏭", "Produção", False),
    ("📊", "Indicadores", False),
    ("📦", "Estoque", False),
    ("🛠", "Manutenção", False),
    ("📋", "Qualidade", False),
    ("🤖", "IA", True),
    ("⚙", "Configurações", False),
]


def aplicar_estilos() -> None:
    st.markdown(
        """
        <style>
        :root {
            --industrial-blue: #0f2747;
            --industrial-blue-2: #163f73;
            --industrial-gray: #f3f6fa;
            --industrial-border: #d8e0ea;
            --industrial-text: #142033;
        }

        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
            color: var(--industrial-text);
        }

        [data-testid="stSidebar"] {
            background: #0f2747;
        }

        [data-testid="stSidebar"] * {
            color: #ffffff;
        }

        [data-testid="stSidebar"] .stButton button {
            width: 100%;
            justify-content: flex-start;
            border: 1px solid rgba(255,255,255,.12);
            background: rgba(255,255,255,.06);
            color: #ffffff;
            border-radius: 10px;
            padding: .7rem .9rem;
        }

        [data-testid="stSidebar"] .stButton button:hover {
            border-color: rgba(255,255,255,.32);
            background: rgba(255,255,255,.13);
        }

        .login-shell {
            max-width: 440px;
            margin: 7vh auto 0 auto;
            padding: 34px;
            border: 1px solid var(--industrial-border);
            border-radius: 18px;
            background: #ffffff;
            box-shadow: 0 22px 60px rgba(15, 39, 71, .12);
        }

        .hero-card, .metric-card, .module-card {
            border: 1px solid var(--industrial-border);
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 12px 32px rgba(15, 39, 71, .08);
        }

        .hero-card {
            padding: 30px;
            margin-bottom: 22px;
            background: linear-gradient(135deg, #0f2747 0%, #163f73 100%);
            color: #ffffff;
        }

        .hero-card h1 {
            margin: 0 0 8px 0;
            font-size: 2rem;
            color: #ffffff;
        }

        .hero-card p {
            margin: 0;
            color: rgba(255,255,255,.82);
        }

        .module-card {
            padding: 20px;
            min-height: 145px;
        }

        .module-card h3 {
            margin: 0 0 8px 0;
            color: #0f2747;
        }

        .module-card p {
            color: #607085;
            margin: 0;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 7px 12px;
            border-radius: 999px;
            background: #eaf2ff;
            color: #163f73;
            font-weight: 700;
            font-size: .86rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid var(--industrial-border);
            background: #ffffff;
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 10px 26px rgba(15, 39, 71, .06);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(usuario: Usuario) -> str:
    with st.sidebar:
        st.markdown(f"### {APP_NAME}")
        st.caption("Base SaaS modular")
        st.divider()
        st.markdown(f"**{usuario.nome}**")
        st.caption(f"{usuario.perfil}")
        st.divider()

        for icone, nome, desabilitado in MENU_ITEMS:
            label = f"{icone} {nome}"
            if desabilitado:
                st.button(f"{label} · em breve", disabled=True)
                continue
            if st.button(label, key=f"menu_{nome}"):
                st.session_state.pagina_atual = nome

        st.divider()
        if st.button("Sair"):
            st.session_state.usuario = None
            st.session_state.pagina_atual = "Dashboard"
            st.rerun()

    return st.session_state.pagina_atual
