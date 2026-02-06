import os
from pathlib import Path
import streamlit as st
from libs.db import init_db, get_db_path
from libs.auth import current_user, is_admin

# ensure data dir and DB exist
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = get_db_path()
init_db(DB_PATH)

st.set_page_config(page_title="Darts Planner", layout="centered")

# Initialize a few global session keys used across pages
st.session_state.setdefault("_last_action", None)
st.session_state.setdefault("user", None)
# Page-specific editor versioning for calendar (page-prefixed as recommended)
st.session_state.setdefault("calendar.matches_editor_version", 0)
st.session_state.setdefault("calendar.matches_editor_key", f"matches_confirm_editor_{st.session_state['calendar.matches_editor_version']}")

# Shared app title(shown in each page when enabled)
# st.title("🏹 Darts Planner")

# Sidebar with user info and login/logout
with st.sidebar:
    cu = current_user()
    if cu:
        # Logged in - Show user info
        st.info(f"Welcome, {cu.get('nickname') or cu.get('username')}!")
        
        if st.button("Logout", use_container_width=True):
            # clear session and rerun
            for k in list(st.session_state.keys()):
                st.session_state.pop(k, None)
            st.rerun()
        
        # last action toast (if present)
        last = st.session_state.get("_last_action")
        if last:
            st.success(last)
    else:
        # Not logged in - show login button
        st.info("Not logged in")
        if st.button("Login", use_container_width=True):
            try:
                st.switch_page("app_pages/home.py")
            except Exception:
                st.rerun()

    st.markdown("---")

# Build navigation pages according to user role
pages = [
    st.Page("app_pages/home.py", title="BarbarApp", icon="🎯"),
]
if current_user():
    pages.append(st.Page("app_pages/calendar.py", title="Calendario", icon="📅"))
    pages.append(st.Page("app_pages/profile.py", title="Profilo", icon="👤"))
    if is_admin():
        pages.append(st.Page("app_pages/admin.py", title="Amministrazione", icon="⚙️"))
        pages.append(st.Page("app_pages/audit.py", title="Cronologia", icon="📝"))
# Render navigation in sidebar (good for many pages)
page = st.navigation(pages, position="top")

# Shared title for the active page
st.title(f"{page.icon} {page.title}")

# Run the selected page (page scripts delegate to views.*.show())
page.run()
