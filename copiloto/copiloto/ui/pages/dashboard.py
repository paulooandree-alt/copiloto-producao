from __future__ import annotations

import streamlit as st

from copiloto.auth.models import Usuario


def render_dashboard(usuario: Usuario) -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <span class="status-pill">Fundação SaaS ativa</span>
            <h1>Dashboard Executivo</h1>
            <p>Bem-vindo, {usuario.nome}. Esta tela usa dados demonstrativos e está pronta para receber módulos reais.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Empresas", "1", "Base inicial")
    col2.metric("Usuários", "3 perfis", "Admin, Supervisor, Operador")
    col3.metric("Módulos planejados", "8", "Estrutura preparada")
    col4.metric("Status", "Online", "SQLite ativo")

    st.subheader("Visão de exemplo")
    cards = st.columns(3)
    with cards[0]:
        st.markdown(
            """
            <div class="module-card">
                <h3>🏭 Produção</h3>
                <p>Área reservada para apontamentos, turnos, linhas e ordens de produção.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cards[1]:
        st.markdown(
            """
            <div class="module-card">
                <h3>📊 Indicadores</h3>
                <p>Base preparada para eficiência, OEE, perdas, metas e performance operacional.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with cards[2]:
        st.markdown(
            """
            <div class="module-card">
                <h3>📦 Operação Integrada</h3>
                <p>Espaço futuro para estoque, PCP, manutenção, qualidade, relatórios e mobile.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
