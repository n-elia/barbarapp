import streamlit as st
from libs.db import get_conn
import pandas as pd


def show():
    st.subheader("Cronologia Conferme")
    
    conn = get_conn()
    
    # Get attendance history with user and match details
    query = """
    SELECT 
        ah.id,
        ah.changed_at,
        u.username,
        m.match_number,
        m.date as match_date,
        m.opponents_team,
        ah.old_status,
        ah.new_status,
        ah.comment,
        changer.username as changed_by_user
    FROM attendance_history ah
    LEFT JOIN users u ON ah.user_id = u.id
    LEFT JOIN matches m ON ah.match_id = m.id
    LEFT JOIN users changer ON ah.changed_by = changer.id
    ORDER BY ah.changed_at DESC 
    LIMIT 200
    """
    
    rows = conn.execute(query).fetchall()
    conn.close()
    
    if not rows:
        st.info("Nessun evento registrato")
        return
    
    # Convert to pandas for better display
    df = pd.DataFrame(rows, columns=[
        'ID', 'Data/Ora', 'Utente', 'Match #', 'Data Match', 
        'Avversari', 'Stato Precedente', 'Nuovo Stato', 'Commento', 'Modificato Da'
    ])
    
    # Format action description
    df['Azione'] = df.apply(lambda row: 
        '✅ Confermato' if row['Stato Precedente'] is None and row['Nuovo Stato'] == 'confirmed'
        else '❌ Cancellato' if row['Stato Precedente'] == 'confirmed' and row['Nuovo Stato'] is None
        else f"{row['Stato Precedente']} → {row['Nuovo Stato']}"
    , axis=1)
    
    # Display in a clean format
    display_df = df[[
        'Data/Ora', 'Utente', 'Azione', 'Match #', 
        'Data Match', 'Avversari', 'Modificato Da'
    ]].copy()
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Summary stats
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        confirmations = len(df[df['Nuovo Stato'] == 'confirmed'])
        st.metric("Conferme", confirmations)
    
    with col2:
        cancellations = len(df[(df['Stato Precedente'] == 'confirmed') & (df['Nuovo Stato'].isna())])
        st.metric("Cancellazioni", cancellations)
    
    with col3:
        unique_users = df['Utente'].nunique()
        st.metric("Utenti Attivi", unique_users)
