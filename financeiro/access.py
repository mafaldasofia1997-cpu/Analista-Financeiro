"""Controlo de edição: o site é privado, mas só o autor pode alterar carteira/notas.

Se o secret `ADMIN_PASSWORD` não estiver definido (desenvolvimento local), a edição
fica livre. Caso contrário, é preciso introduzir a palavra-passe na barra lateral.
"""
from __future__ import annotations

import streamlit as st

from .store import secret


def editor_gate() -> bool:
    """Desenha a caixa de palavra-passe na sidebar e devolve True se for editor."""
    pw = secret("ADMIN_PASSWORD")
    if not pw:
        return True  # sem palavra-passe definida -> edição livre (local)
    if st.session_state.get("is_editor"):
        st.sidebar.caption("✏️ Modo edição ativo")
        return True

    with st.sidebar.expander("🔒 Modo edição"):
        attempt = st.text_input("Palavra-passe do autor", type="password", key="pw_try")
        if attempt:
            if attempt == pw:
                st.session_state["is_editor"] = True
                st.rerun()
            st.error("Palavra-passe incorreta.")
    return False
