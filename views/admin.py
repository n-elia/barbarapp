import streamlit as st
from libs.auth import list_users, generate_temp_password, update_password, current_user, is_admin, require_login, create_user, find_user_by_username
from libs.csv_utils import parse_pasted_csv, validate_row
from libs.db import get_conn
from datetime import datetime
import validators
from st_diff_viewer import diff_viewer


class MatchOperator:
    """Helper methods for creating or updating matches.

    Provides a single static method `apply_row` that performs an upsert using
    the same logic as manual inserts and CSV imports. Returns a tuple
    (action, id) where action is one of 'inserted' or 'updated'.
    """

    @staticmethod
    def apply_row(conn, match_number, date, opponents, hoa, place, source='manual', created_by=None):
        # normalize match_number
        try:
            match_number = int(match_number)
        except Exception:
            raise ValueError(f"match_number must be integer: {match_number}")
        # normalize date to ISO-like string where possible
        date_norm = None
        if date is not None:
            try:
                date_norm = datetime.fromisoformat(str(date)).date().isoformat()
            except Exception:
                date_norm = str(date).strip()
        place_url = place if validators.url(str(place or '')) else None
        now = datetime.utcnow().isoformat()

        # prefer matching by date (import rule), otherwise use match_number
        existing = None
        if date_norm:
            existing = conn.execute(
                "SELECT id, match_number, date, opponents_team, home_or_away, place_text, place_parsed_url FROM matches WHERE date = ?", 
                (date_norm,)
            ).fetchone()
        if not existing:
            existing = conn.execute(
                "SELECT id, match_number, date, opponents_team, home_or_away, place_text, place_parsed_url FROM matches WHERE match_number = ?", 
                (match_number,)
            ).fetchone()

        if existing:
            # Check if values are identical - if so, skip update
            if (existing['match_number'] == match_number and
                existing['date'] == date_norm and
                existing['opponents_team'] == opponents and
                existing['home_or_away'] == hoa and
                existing['place_text'] == place and
                existing['place_parsed_url'] == place_url):
                return 'skipped', existing['id']
            
            conn.execute(
                "UPDATE matches SET match_number=?, date=?, opponents_team=?, home_or_away=?, place_text=?, place_parsed_url=?, updated_at=?, source_import=? WHERE id=?",
                (match_number, date_norm, opponents, hoa, place, place_url, now, source, existing['id']),
            )
            return 'updated', existing['id']
        else:
            cur = conn.execute(
                "INSERT INTO matches (match_number, date, opponents_team, home_or_away, place_text, place_parsed_url, source_import, created_by, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (match_number, date_norm, opponents, hoa, place, place_url, source, created_by, now),
            )
            return 'inserted', cur.lastrowid


def show():
    require_login()
    if not is_admin():
        st.error("Admin access required")
        return

    # st.header("Admin")

    tab_matches, tab_users = st.tabs(["Calendario Partite", "Utenti"])

    with tab_matches:
        st.subheader("Importazione partite da CSV")
        st.info("Incolla CSV con intestazioni: match_number,date,opponents_team,home_or_away,place")
        txt = st.text_area("Incolla il CSV qui", height=200)
        if st.button("Anteprima CSV", use_container_width=True):
            try:
                rows = parse_pasted_csv(txt)
            except Exception as e:
                st.error(f"Parse error: {e}")
                return
            if not rows:
                st.warning("Nessuna riga analizzata. Assicurati che il tuo CSV abbia una riga di intestazione con le colonne: match_number, date, opponents_team, home_or_away, place")
                return

            # show what header keys we detected (helpful for debugging mismatched headers)
            detected_keys = sorted(list(rows[0].keys())) if rows else []
            st.info(f"Detected columns: {detected_keys}")

            # Validate rows and check if they will insert or update
            preview = []
            conn = get_conn()
            for i, r in enumerate(rows, start=1):
                errs = validate_row(r)
                r['_row_no'] = i
                r['_errors'] = errs
                
                # Check if this row will insert or update, and get existing data if updating
                action = 'insert'
                existing_data = None
                if not errs and r.get('date'):
                    try:
                        date_norm = datetime.fromisoformat(str(r['date'])).date().isoformat()
                        place_url = r.get('place') if validators.url(str(r.get('place') or '')) else None
                        existing = conn.execute(
                            "SELECT match_number, date, opponents_team, home_or_away, place_text, place_parsed_url FROM matches WHERE date = ?", 
                            (date_norm,)
                        ).fetchone()
                        if existing:
                            # Check if values are identical
                            if (existing['match_number'] == int(r.get('match_number')) and
                                existing['date'] == date_norm and
                                existing['opponents_team'] == r.get('opponents_team') and
                                existing['home_or_away'] == r.get('home_or_away') and
                                existing['place_text'] == r.get('place') and
                                existing['place_parsed_url'] == place_url):
                                action = 'skip'
                            else:
                                action = 'update'
                            existing_data = dict(existing)
                    except Exception:
                        pass
                r['_action'] = action
                r['_existing'] = existing_data
                preview.append(r)
            conn.close()
            
            # Display as a formatted diff-like preview
            st.markdown("### Preview of changes")
            for r in preview:
                if r['_errors']:
                    # Red for errors
                    st.markdown(f"**Row {r['_row_no']}** - VALIDATION ERROR")
                    st.error(", ".join(r['_errors']))
                    st.code(f"match_number={r.get('match_number')} date={r.get('date')} opponents={r.get('opponents_team')} home_or_away={r.get('home_or_away')} place={r.get('place')}", language=None)
                else:
                    # Green for inserts, yellow for updates with diff, gray for skipped
                    if r['_action'] == 'insert':
                        st.markdown(f"**Row {r['_row_no']}** - NEW MATCH")
                        st.success(f"**{r.get('match_number')}** · {r.get('date')} · **{r.get('opponents_team')}** · {r.get('home_or_away')} · {r.get('place')}")
                    elif r['_action'] == 'skip':
                        st.markdown(f"**Row {r['_row_no']}** - ALREADY UP TO DATE (will skip)")
                        st.info(f"**{r.get('match_number')}** · {r.get('date')} · **{r.get('opponents_team')}** · {r.get('home_or_away')} · {r.get('place')}")
                    else:
                        st.markdown(f"**Row {r['_row_no']}** - UPDATE EXISTING")
                        
                        # Show diff for updates
                        existing = r['_existing']
                        old_text = f"""Match Number: {existing['match_number']}
Date: {existing['date']}
Opponents: {existing['opponents_team']}
Home/Away: {existing['home_or_away']}
Place: {existing['place_text'] or '(none)'}"""
                        
                        new_text = f"""Match Number: {r.get('match_number')}
Date: {r.get('date')}
Opponents: {r.get('opponents_team')}
Home/Away: {r.get('home_or_away')}
Place: {r.get('place') or '(none)'}"""
                        
                        diff_viewer(
                            old_text, 
                            new_text, 
                            split_view=True,
                            left_title="Current",
                            right_title="New",
                            hide_line_numbers=True,
                            key=f"diff_{r['_row_no']}"
                        )

            # persist preview and detected keys so the Approve step survives reruns
            st.session_state['_csv_preview'] = preview
            st.session_state['_csv_detected_keys'] = detected_keys

            # If all rows have errors, show a hint
            if all(r['_errors'] for r in preview):
                st.warning("All parsed rows have validation errors. Check column names and formats. Use headers like: match_number,date,opponents_team,home_or_away,place")
            else:
                valid_count = sum(1 for r in preview if not r['_errors'])
                insert_count = sum(1 for r in preview if not r['_errors'] and r['_action'] == 'insert')
                update_count = sum(1 for r in preview if not r['_errors'] and r['_action'] == 'update')
                skip_count = sum(1 for r in preview if not r['_errors'] and r['_action'] == 'skip')
                st.info(f"{valid_count} valid rows: {insert_count} new, {update_count} updates, {skip_count} unchanged · Rows will **overwrite existing matches that share the same `date`**")

        # Approve import button OUTSIDE the parse preview button scope
        if st.session_state.get('_csv_preview'):
            if st.button("Approva importazione", use_container_width=True):
                preview = st.session_state.pop('_csv_preview', None)
                detected_keys = st.session_state.pop('_csv_detected_keys', None)
                if not preview:
                    st.warning("No preview available. Paste CSV and click 'Parse preview' first.")
                else:
                    # show diagnostic info about the preview to help debug
                    st.info(f"Preview rows: {len(preview)}; Detected keys: {detected_keys}")

                    conn = get_conn()
                    inserted = 0
                    updated = 0
                    skipped = 0
                    errors = []
                    # only process rows without validation errors
                    valid_rows = [r for r in preview if not r.get('_errors')]
                    st.info(f"Valid rows to import: {len(valid_rows)}")
                    if not valid_rows:
                        st.error("No valid rows to import. Fix parsing/validation errors and re-parse.")

                    # capture DB counts before/after to help diagnose visibility issues
                    try:
                        before_count_row = conn.execute("SELECT COUNT(1) as c FROM matches").fetchone()
                        before_count = before_count_row['c'] if before_count_row else 0
                    except Exception:
                        before_count = None

                    row_notes = []
                    admin = current_user()

                    # Also collect the target filters we will query after apply (dates and match_numbers)
                    dates = set()
                    match_numbers = set()

                    for r in valid_rows:
                        try:
                            dates.add(str(r.get('date')).strip())
                            match_numbers.add(str(r.get('match_number')).strip())
                            action, mid = MatchOperator.apply_row(
                                conn,
                                r.get('match_number'),
                                r.get('date'),
                                r.get('opponents_team'),
                                r.get('home_or_away'),
                                r.get('place'),
                                source='csv-paste',
                                created_by=(admin['id'] if admin else None),
                            )
                            if action == 'inserted':
                                inserted += 1
                                row_notes.append((r['_row_no'], 'inserted', mid))
                            elif action == 'updated':
                                updated += 1
                                row_notes.append((r['_row_no'], 'updated', mid))
                            else:  # skipped
                                skipped += 1
                                row_notes.append((r['_row_no'], 'skipped', mid))
                        except Exception as e:
                            errors.append(f"Row {r.get('_row_no')}: {e}")
                            row_notes.append((r.get('_row_no'), 'error', str(e)))

                    try:
                        after_count_row = conn.execute("SELECT COUNT(1) as c FROM matches").fetchone()
                        after_count = after_count_row['c'] if after_count_row else 0
                    except Exception:
                        after_count = None

                    conn.commit()
                    conn.close()
                    
                    msg = f"Inserted={inserted} Updated={updated} Skipped={skipped}"
                    if errors:
                        st.error("Some rows failed: " + "; ".join(errors))
                    st.success(msg)

                    # Diagnostic summary to help understand why changes might not appear
                    diag = {
                        'before_count': before_count,
                        'after_count': after_count,
                        'row_notes': row_notes,
                    }
                    st.info(f"Import diagnostics: {diag}")

                    # Re-query the matches and display only those matching imported dates or match_numbers
                    try:
                        conn2 = get_conn()
                        placeholders_dates = ','.join('?' for _ in dates) if dates else ''
                        filtered_rows = []
                        if dates:
                            q = f"SELECT id, match_number, date, opponents_team, home_or_away, place_text FROM matches WHERE date IN ({placeholders_dates}) ORDER BY date"
                            filtered_rows = conn2.execute(q, tuple(dates)).fetchall()
                        import pandas as pd
                        df_new = pd.DataFrame(filtered_rows) if filtered_rows else pd.DataFrame(columns=["id","match_number","date","opponents_team","home_or_away","place_text"])
                        st.markdown("**Matches matching imported rows:**")
                        st.dataframe(df_new)

                        # also show full table for completeness
                        new_rows = conn2.execute("SELECT id, match_number, date, opponents_team, home_or_away, place_text FROM matches ORDER BY date").fetchall()
                        df_full = pd.DataFrame(new_rows) if new_rows else pd.DataFrame(columns=["id","match_number","date","opponents_team","home_or_away","place_text"])
                        st.markdown("**Full matches table:**")
                        st.dataframe(df_full)
                        conn2.close()
                    except Exception as e:
                        st.error(f"Unable to re-query matches for diagnostics: {e}")

                    # force a rerun to fully refresh the page
                    st.rerun()

        st.markdown("---")
        st.subheader("Inserimento manuale partita")
        with st.form("manual_insert_form"):
            match_number = st.number_input("Numero partita", min_value=1, step=1)
            date_val = st.date_input("Data")
            opponents = st.text_input("Squadra avversaria")
            home_or_away = st.selectbox("Casa/Trasferta", ["casa", "trasferta"], index=0)
            place = st.text_input("Luogo (testo o URL)")
            submit_manual = st.form_submit_button("Aggiungi partita", use_container_width=True)
            if submit_manual:
                if not opponents:
                    st.error("La squadra avversaria è obbligatoria")
                else:
                    conn = get_conn()
                    admin = current_user()
                    try:
                        action, mid = MatchOperator.apply_row(conn, int(match_number), date_val.isoformat(), opponents, home_or_away, place, source='manual', created_by=admin['id'])
                        conn.commit()
                        st.success("Partita aggiunta" if action == 'inserted' else "Partita aggiornata")
                    except Exception as e:
                        st.error(f"Errore nell'aggiungere la partita: {e}")
                    finally:
                        conn.close()

        st.markdown("---")
        st.subheader("Calendario attuale")
        import pandas as pd

        conn = get_conn()
        rows = conn.execute("SELECT id, match_number, date, opponents_team, home_or_away, place_text, place_parsed_url FROM matches ORDER BY date").fetchall()
        conn.close()

        df = pd.DataFrame(rows, columns=["id", "match_number", "date", "opponents_team", "home_or_away", "place_text", "place_parsed_url"]) if rows else pd.DataFrame(columns=["id", "match_number", "date", "opponents_team", "home_or_away", "place_text", "place_parsed_url"])
        # expose editable copy; hide the internal id in the editor but keep it for saves
        df_display = df[["match_number", "date", "opponents_team", "home_or_away", "place_text", "place_parsed_url"]].copy()
        # add a delete checkbox
        df_display["delete"] = False

        edited = st.data_editor(df_display, num_rows="dynamic", use_container_width=True, key="matches_editor")

        if st.button("Salva modifiche", use_container_width=True):
            conn = get_conn()
            inserted = 0
            updated = 0
            deleted = 0
            errors = []
            for i, row in edited.iterrows():
                try:
                    if row["delete"]:
                        # delete by match_number
                        conn.execute("DELETE FROM matches WHERE match_number = ?", (int(row["match_number"]),))
                        deleted += 1
                        continue
                    match_number = int(row["match_number"])
                    date = str(row["date"]) if not pd.isna(row["date"]) else None
                    opponents = row["opponents_team"]
                    hoa = row["home_or_away"]
                    place = row["place_text"]
                    place_url = place if validators.url(str(place)) else None
                    now = datetime.utcnow().isoformat()
                    existing = conn.execute("SELECT id FROM matches WHERE match_number = ?", (match_number,)).fetchone()
                    if existing:
                        conn.execute(
                            "UPDATE matches SET date=?, opponents_team=?, home_or_away=?, place_text=?, place_parsed_url=?, updated_at=? WHERE match_number=?",
                            (date, opponents, hoa, place, place_url, now, match_number),
                        )
                        updated += 1
                    else:
                        conn.execute(
                            "INSERT INTO matches (match_number, date, opponents_team, home_or_away, place_text, place_parsed_url, source_import, created_at) VALUES (?,?,?,?,?,?,?)",
                            (match_number, date, opponents, hoa, place, place_url, 'manual', now),
                        )
                        inserted += 1
                except Exception as e:
                    errors.append(str(e))
            conn.commit()
            conn.close()
            msg = f"Inserted={inserted} Updated={updated} Deleted={deleted}"
            if errors:
                st.error("Some rows failed: " + "; ".join(errors))
            st.success(msg)
            # set a toast message for the next render of this page
            st.session_state._last_action = msg
            try:
                st.switch_page("app_pages/admin.py")
            except Exception:
                st.rerun()

    with tab_users:
        st.subheader("Crea utente")
        with st.form("create_user_form"):
            new_username = st.text_input("Nome utente", key="new_user_input")
            # live check for username availability
            username_available = True
            if new_username.strip():
                if find_user_by_username(new_username.strip()):
                    st.warning("Nome utente già esistente")
                    username_available = False

            new_password = st.text_input("Password", type="password")
            new_role = st.selectbox("Ruolo", ["giocatore", "admin"], index=0)
            submitted = st.form_submit_button("Crea utente")
            if submitted:
                if not new_username or not new_password:
                    st.error("Fornisci nome utente e password")
                elif not username_available:
                    st.error("Nome utente già esistente; scegline un altro")
                else:
                    uid = create_user(new_username, new_password, role=new_role)
                    if uid:
                        st.success("Utente creato")
                        # set toast message; listing below will re-query DB so it will show the new user
                        st.session_state._last_action = f"Utente '{new_username}' creato (id={uid})"
                    else:
                        st.warning("Utente già esistente")

        st.markdown("---")
        st.subheader("Utenti attivi")
        conn = get_conn()
        users = list_users()
        if not users:
            st.info("No users yet")
        else:
            # header row (allocate more space for username and actions)
            cols = st.columns([1, 1, 1, 2], vertical_alignment="center")
            cols[0].markdown("**Nome utente**")
            cols[1].markdown("**Ruolo**")
            cols[2].markdown("**Soprannome**")
            cols[3].markdown("")
            for u in users:
                cols = st.columns([1, 1, 1, 2], vertical_alignment="center")
                cols[0].write(u["username"])
                cols[1].write(u["role"])
                cols[2].write(u.get("nickname") or "N/A")

                # Actions: Reset password + Delete (with safety checks)
                action_cols = cols[3].columns([1, 1], vertical_alignment="center")
                if action_cols[0].button("Reset PWD", key=f"reset_pwd_{u['id']}"):
                    temp = generate_temp_password()
                    update_password(u["id"], temp)
                    # record audit
                    admin = current_user()
                    now = datetime.utcnow().isoformat()
                    conn.execute(
                        "INSERT INTO user_audit (admin_id, target_user_id, action, details, created_at) VALUES (?,?,?,?,?)",
                        (admin["id"], u["id"], 'password_reset', f'Temporary password generated', now),
                    )
                    conn.commit()
                    st.info(f"Temporary password for {u['username']}: {temp}")

                # When Delete is clicked, set a per-user confirm flag and show confirm/cancel buttons
                confirm_key = f"confirm_delete_{u['id']}"
                if action_cols[1].button("Delete", key=f"delete_user_{u['id']}", type="primary"):
                    st.session_state[confirm_key] = True

                if st.session_state.get(confirm_key):
                    st.warning(f"Sei sicuro di voler eliminare l'utente **{u['username']}** (id={u['id']})? Questa azione è irreversibile.")
                    c1, c2 = st.columns([1, 1])
                    if c1.button("Conferma", key=f"confirm_yes_{u['id']}"):
                        admin = current_user()
                        # prevent self-deletion
                        if admin and admin['id'] == u['id']:
                            st.error("Non puoi eliminare il tuo account mentre sei loggato.")
                            st.session_state.pop(confirm_key, None)
                        else:
                            # don't allow deleting the last admin
                            if u.get('role') == 'admin':
                                admin_count_row = conn.execute("SELECT COUNT(1) as c FROM users WHERE role = 'admin'").fetchone()
                                if admin_count_row and admin_count_row['c'] <= 1:
                                    st.error("Impossibile eliminare l'ultimo amministratore.")
                                    st.session_state.pop(confirm_key, None)
                                    continue
                            # perform delete and audit
                            conn.execute("DELETE FROM users WHERE id = ?", (u['id'],))
                            now = datetime.utcnow().isoformat()
                            conn.execute(
                                "INSERT INTO user_audit (admin_id, target_user_id, action, details, created_at) VALUES (?,?,?,?,?)",
                                (admin['id'] if admin else None, u['id'], 'delete_user', f"Deleted user {u['username']}", now),
                            )
                            conn.commit()
                            st.success(f"User {u['username']} deleted")
                            st.session_state._last_action = f"User '{u['username']}' deleted (id={u['id']})"
                            st.session_state.pop(confirm_key, None)
                            st.rerun()
                    if c2.button("Annulla", key=f"confirm_no_{u['id']}"):
                        st.session_state.pop(confirm_key, None)
        conn.close()
