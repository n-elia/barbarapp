import streamlit as st
from libs.auth import require_login, current_user, update_password
from libs.db import get_conn


def show():
    require_login()
    # st.header("Profile")
    user = current_user()
    st.write(f"Username: {user['username']}")
    nick = st.text_input("Soprannome", value=user.get('nickname') or '')
    if st.button("Salva soprannome"):
        conn = get_conn()
        conn.execute("UPDATE users SET nickname = ?, updated_at = datetime('now') WHERE id = ?", (nick, user['id']))
        conn.commit()
        conn.close()
        st.success("Soprannome aggiornato")
    st.markdown("---")
    st.subheader("Cambio password")
    cur = st.text_input("Password attuale", type='password')
    new = st.text_input("Nuova password", type='password')
    if st.button("Cambia password"):
        if not cur or not new:
            st.error("Compila entrambi i campi")
        else:
            from libs.auth import find_user_by_username, verify_password
            u = find_user_by_username(user['username'])
            if verify_password(cur, u['password_hash']):
                update_password(u['id'], new)
                st.success("Password cambiata")
            else:
                st.error("Password attuale errata")
