import streamlit as st
from views import login
from libs.auth import current_user

cu = current_user()

if cu:
    # Home page wrapper
    nickname = cu.get('nickname') or cu.get('username', 'viandante')
    st.markdown(f"""
## Hey **{nickname}**, bentornato tra I Barbari! ⚔️

Questa è la nostra app per organizzare partite e tenere traccia delle presenze. Piccola e rapida, come piace a noi.

**Sezioni disponibili:**
- **Calendar** → Conferma la tua presenza alle partite 🎯
- **Profile** → Modifica il tuo nickname o la password 🔐
- **Admin** *(solo amministratori)* → Gestione utenti e importazione calendario 🛠️

Che le frecce volino dritte e la birra sia sempre fresca! 🍻
""")
else:
    # Home page wrapper
    login.show()
