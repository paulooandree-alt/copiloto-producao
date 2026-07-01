from __future__ import annotations

import pandas as pd
import streamlit as st

from copiloto.auth.models import Usuario
from copiloto.auth.service import alterar_senha_usuario, cadastrar_usuario, listar_usuarios
from copiloto.core.config import PERFIS


def render_settings(usuario: Usuario) -> None:
    st.markdown(
        """
        <div class="hero-card">
            <span class="status-pill">Administração</span>
            <h1>Configurações</h1>
            <p>Gerencie usuários e prepare a estrutura da plataforma.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_alterar_senha(usuario)

    if usuario.perfil != "Administrador":
        st.warning("Apenas administradores podem cadastrar usuários.")
        render_lista_usuarios()
        return

    st.subheader("Cadastro de usuários")
    with st.form("form_cadastro_usuario"):
        col1, col2 = st.columns(2)
        nome = col1.text_input("Nome")
        email = col2.text_input("E-mail")
        col3, col4 = st.columns(2)
        perfil = col3.selectbox("Perfil", PERFIS)
        senha = col4.text_input("Senha inicial", type="password")
        salvar = st.form_submit_button("Cadastrar usuário")

    if salvar:
        sucesso, mensagem = cadastrar_usuario(nome, email, senha, perfil)
        if sucesso:
            st.success(mensagem)
        else:
            st.error(mensagem)

    render_lista_usuarios()


def render_alterar_senha(usuario: Usuario) -> None:
    st.subheader("Alterar minha senha")
    with st.form("form_alterar_senha"):
        col1, col2, col3 = st.columns(3)
        senha_atual = col1.text_input("Senha atual", type="password")
        nova_senha = col2.text_input("Nova senha", type="password")
        confirmar_senha = col3.text_input("Confirmar nova senha", type="password")
        alterar = st.form_submit_button("Alterar senha")

    if alterar:
        sucesso, mensagem = alterar_senha_usuario(
            usuario.id,
            senha_atual,
            nova_senha,
            confirmar_senha,
        )
        if sucesso:
            st.success(mensagem)
        else:
            st.error(mensagem)

    st.divider()


def render_lista_usuarios() -> None:
    st.subheader("Usuários cadastrados")
    usuarios = listar_usuarios()
    dados = [
        {
            "Nome": u.nome,
            "E-mail": u.email,
            "Perfil": u.perfil,
            "Status": "Ativo" if u.ativo else "Inativo",
        }
        for u in usuarios
    ]
    st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
