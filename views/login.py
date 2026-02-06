import streamlit as st
from libs.auth import find_user_by_username, verify_password, create_user
from libs.auth import generate_temp_password
from libs.db import get_conn


def show():
    st.header("Login")
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Nome utente")
        password = st.text_input("Password", type="password")
        if st.button("Accedi"):
            user = find_user_by_username(username)
            if user and verify_password(password, user["password_hash"]):
                st.session_state.user = user
                st.success("Accesso effettuato")
                # programmatic navigation using st.switch_page
                try:
                    st.switch_page("app_pages/calendar.py")
                except Exception:
                    # fallback: force a rerun so the main navigation can pick up the new user
                    st.rerun()
            else:
                st.error("Credenziali non valide")

    # First-run bootstrap: create admin if no users exist
    conn = get_conn()
    row = conn.execute("SELECT COUNT(1) as c FROM users").fetchone()
    conn.close()
    if row and row["c"] == 0:
        st.info("Nessun utente trovato — crea l'amministratore iniziale")
        new_user = st.text_input("Nome utente admin", value="admin")
        new_pw = st.text_input("Password admin", type="password")
        if st.button("Crea amministratore"):
            if new_user and new_pw:
                create_user(new_user, new_pw, role="admin")
                st.success("Amministratore creato — effettua il login")
                try:
                    st.switch_page("app_pages/home.py")
                except Exception:
                    st.rerun()
