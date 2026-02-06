import streamlit as st
from libs.db import get_conn
from libs.auth import require_login, current_user
from datetime import datetime, timezone
import validators


def _relative_time(ts: str) -> str:
    if not ts:
        return "No updates"
    try:
        t = datetime.fromisoformat(ts)
    except Exception:
        return ts
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = now - t
    s = int(delta.total_seconds())
    if s < 60:
        return f"{s}s ago"
    if s < 3600:
        return f"{s//60}m ago"
    if s < 86400:
        return f"{s//3600}h ago"
    return f"{s//86400}d ago"


def _get_attendance_summary(conn, match_id, limit_names=4):
    # confirmed count and sample nicknames
    confirmed_rows = conn.execute(
        "SELECT u.nickname, u.username, a.updated_at FROM attendance a JOIN users u ON a.user_id = u.id WHERE a.match_id = ? AND a.status = 'confirmed' ORDER BY a.updated_at DESC LIMIT ?",
        (match_id, limit_names),
    ).fetchall()
    confirmed_count_row = conn.execute(
        "SELECT COUNT(1) as c FROM attendance WHERE match_id = ? AND status = 'confirmed'", (match_id,)
    ).fetchone()
    confirmed_count = confirmed_count_row["c"] if confirmed_count_row else 0
    # last update time from attendance_history
    last = conn.execute(
        "SELECT changed_at FROM attendance_history WHERE match_id = ? ORDER BY changed_at DESC LIMIT 1", (match_id,)
    ).fetchone()
    last_ts = last["changed_at"] if last else None
    names = []
    for r in confirmed_rows:
        nick = r["nickname"] or r["username"]
        names.append(nick)
    return confirmed_count, names, last_ts


def _shorten_place(place: str) -> str:
    """Return a compact representation of a place string.
    - Compute a short human-friendly display (domain/path or truncated text).
    - Return plain text (no links) as requested.
    """
    if not place:
        return ""
    s = str(place)
    from urllib.parse import urlparse

    display = s
    try:
        if validators.url(s):
            p = urlparse(s)
            netloc = p.netloc.replace("www.", "")
            path = p.path.rstrip("/")
            if path:
                display_path = path if len(path) <= 24 else path[:24] + "..."
                display = f"{netloc}{display_path}"
            elif p.query:
                q = p.query if len(p.query) <= 24 else p.query[:24] + "..."
                display = f"{netloc}?{q}"
            else:
                display = netloc
        if len(display) > 40:
            display = display[:37] + "..."
    except Exception:
        display = s if len(s) <= 40 else s[:37] + "..."

    return display

def show():
    require_login()
    # st.header("Calendar")
    st.markdown(
        """Modifica le tue presenze alle partite usando le checkbox nella tabella sottostante.\n\n"""
        """Una spunta verde ✅ indica che ci sono almeno 4 conferme per la partita, un pallino rosso 🔴 indica meno di 4 conferme."""
        """Dopo aver modificato le tue presenze, schiaccia "Salva" per salvare le modifiche."""
        )
    conn = get_conn()
    rows = conn.execute("SELECT id, match_number, date, opponents_team, home_or_away, place_text, place_parsed_url FROM matches ORDER BY date").fetchall()
    if not rows:
        st.info("No matches scheduled")
        conn.close()
        return

    # build dataframe
    import pandas as pd

    data = []
    for m in rows:
        confirmed_count, names, last_ts = _get_attendance_summary(conn, m['id'])
        players_preview = ", ".join(names) if names else ""
        # build a concise recap as a list of names, or empty list when none
        if names:
            players_recap = names
        else:
            players_recap = []
        place = m['place_parsed_url'] if m['place_parsed_url'] else m['place_text']
        # compute display text for Place
        display = _shorten_place(place)
        # mark date with a green check when >=4 confirmations, otherwise a red dot
        date_display = f"✅ {m['date']}" if confirmed_count >= 4 else f"🔴 {m['date']}"
        # map Home/Away to emojis for compact display
        hoa_map = {'home': '🏠', 'away': '🚗', 'neutral': '⚪'}
        hoa_value = m['home_or_away'] if m['home_or_away'] is not None else ''
        hoa_display = hoa_map.get((hoa_value or '').lower(), hoa_value)

        data.append({
            "Match #": m['match_number'],
            "Date": date_display,
            "Opponent": m['opponents_team'],
            "Home/Away": hoa_display,
            # show a shortened place label (domain / short path) for long URLs
            "Place": display,
            "Confirmed": confirmed_count,
            "Presenze": players_recap,
            "Last update": _relative_time(last_ts),
            "_id": m['id'],
        })

    import pandas as pd

    # add `Confirmed by me` column for this user
    u = current_user()
    confirmed_by_me = {}
    for m in rows:
        ra = conn.execute("SELECT id FROM attendance WHERE match_id = ? AND user_id = ? AND status = 'confirmed'", (m['id'], u['id'])).fetchone()
        confirmed_by_me[m['id']] = True if ra else False

    df = pd.DataFrame(data)

    # Editable confirmations table (single visible table)
    # use _id as index so it is not shown as a column but stays linked to each row
    # Hide 'Match #' column from the editor (kept in the index via _id)
    editable = df.set_index('_id')[['Date', 'Opponent', 'Home/Away', 'Place', 'Presenze']].copy()
    editable['Confirmed'] = editable.index.map(lambda i: bool(confirmed_by_me.get(i, False)))

    # build a column_config assuming modern Streamlit column_config API
    column_config = {}
    cc = getattr(st, 'column_config', None)
    if cc:
        # disable text columns (pin Date column). 'Match #' is intentionally hidden from the editor
        for col in ['Date', 'Opponent', 'Home/Away', 'Place', 'Presenze']:
            if col == 'Date':
                column_config[col] = cc.TextColumn(col, disabled=True, pinned=True)
            else:
                column_config[col] = cc.TextColumn(col, disabled=True)

        # Confirmed as a checkbox column
        column_config['Confirmed'] = cc.CheckboxColumn('Confirmed', help='Check to confirm attendance')

        # Make Place a disabled text column (no links) per user preference
        column_config['Place'] = cc.TextColumn('Place', disabled=True)
        # Prefer ListColumn for Presenze (renders lists/wrapped items nicely); fallback to TextColumn
        try:
            column_config['Presenze'] = cc.ListColumn('Presenze', width=300, disabled=True)
        except Exception:
            column_config['Presenze'] = cc.TextColumn('Presenze', disabled=True)

    editor_key = st.session_state.get('calendar.matches_editor_key', 'matches_confirm_editor')
    if column_config:
        edited = st.data_editor(editable, column_config=column_config, hide_index=True, key=editor_key)
    else:
        edited = st.data_editor(editable, hide_index=True, key=editor_key)

    if st.button('Salva', key='save_confirmations', type='secondary', use_container_width=True):
        conn = get_conn()
        inserted = 0
        deleted = 0
        for match_id, row in edited.iterrows():
            match_id = int(match_id)
            want = bool(row['Confirmed'])
            exists = conn.execute("SELECT id FROM attendance WHERE match_id = ? AND user_id = ? AND status = 'confirmed'", (match_id, u['id'])).fetchone()
            now = datetime.utcnow().isoformat()
            if want and not exists:
                res = conn.execute("INSERT INTO attendance (match_id, user_id, status, updated_at, updated_by, nickname_at_time) VALUES (?,?,?,?,?,?)", (match_id, u['id'], 'confirmed', now, u['id'], u.get('nickname')))
                aid = res.lastrowid
                conn.execute("INSERT INTO attendance_history (attendance_id, match_id, user_id, old_status, new_status, changed_at, changed_by) VALUES (?,?,?,?,?,?,?)", (aid, match_id, u['id'], None, 'confirmed', now, u['id']))
                inserted += 1
            if (not want) and exists:
                conn.execute("DELETE FROM attendance WHERE id = ?", (exists['id'],))
                conn.execute("INSERT INTO attendance_history (attendance_id, match_id, user_id, old_status, new_status, changed_at, changed_by) VALUES (?,?,?,?,?,?,?)", (exists['id'], match_id, u['id'], 'confirmed', None, now, u['id']))
                deleted += 1
        conn.commit()
        conn.close()
        # st.success(f'Inseriti: {inserted}. Eliminati: {deleted}.')
        # set a short-lived toast value for subsequent renders
        st.session_state._last_action = f'Inseriti: {inserted}. Eliminati: {deleted}.'
        # bump the page-specific editor key to avoid duplicate widget-key errors when re-rendering
        st.session_state['calendar.matches_editor_version'] = st.session_state.get('calendar.matches_editor_version', 0) + 1
        st.session_state['calendar.matches_editor_key'] = f"matches_confirm_editor_{st.session_state['calendar.matches_editor_version']}"
        # attempt a quick refresh to show updated counts; if it fails, rely on user navigation
        try:
            st.rerun()
        except Exception:
            pass