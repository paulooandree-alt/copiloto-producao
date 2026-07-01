from __future__ import annotations

import streamlit as st


def render_placeholder(nome_modulo: str) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <span class="status-pill">Módulo reservado</span>
            <h1>{nome_modulo}</h1>
            <p>Esta área já está conectada ao menu e preparada para expansão futura.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info("Nenhuma funcionalidade operacional foi implementada nesta etapa. A fundação está pronta para crescimento.")
