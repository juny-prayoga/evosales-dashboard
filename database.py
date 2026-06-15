import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# --- KONEKSI SUPABASE ---
@st.cache_resource
def get_connection():
    db_url = st.secrets["SUPABASE_URL"]
    return create_engine(db_url)

def init_db():
    pass # Supabase sudah kita atur manual via SQL Editor

def get_all_sales():
    engine = get_connection()
    try: return pd.read_sql_query("SELECT * FROM sales_daily", engine)
    except: return pd.DataFrame()

def get_existing_imeis():
    engine = get_connection()
    try:
        df = pd.read_sql_query("SELECT imei FROM sales_daily WHERE imei IS NOT NULL AND imei != ''", engine)
        return df['imei'].astype(str).str.strip().tolist()
    except: return []

def update_sales_data(id_data, promotor, tipe, qty, harga):
    engine = get_connection()
    with engine.begin() as conn:
        conn.execute(text("UPDATE sales_daily SET promotor=:p, tipe=:t, qty=:q, harga=:h WHERE id=:id"), 
                     {"p":promotor, "t":tipe, "q":qty, "h":harga, "id":id_data})

def delete_sales_by_ids(id_list):
    if not id_list: return
    engine = get_connection()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sales_daily WHERE id IN :ids"), {"ids": tuple(id_list)})

def add_master_produk(kw, cat, sub, prc):
    engine = get_connection()
    with engine.begin() as conn:
        query = """INSERT INTO master_produk (keyword, category, sub_category, harga) 
                   VALUES (:k, :c, :s, :p) 
                   ON CONFLICT (keyword) DO UPDATE 
                   SET category=EXCLUDED.category, sub_category=EXCLUDED.sub_category, harga=EXCLUDED.harga"""
        conn.execute(text(query), {"k":kw, "c":cat, "s":sub, "p":prc})

def get_all_master():
    engine = get_connection()
    try: return pd.read_sql_query("SELECT * FROM master_produk", engine)
    except: return pd.DataFrame()

def delete_master(kw):
    engine = get_connection()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM master_produk WHERE keyword = :k"), {"k": kw})

def add_store_mapping(promotor, store_name):
    engine = get_connection()
    with engine.begin() as conn:
        query = """INSERT INTO store_mapping (promotor, store_name) 
                   VALUES (:p, :s) 
                   ON CONFLICT (promotor) DO UPDATE 
                   SET store_name=EXCLUDED.store_name"""
        conn.execute(text(query), {"p":promotor.upper(), "s":store_name.upper()})

def get_all_store_mappings():
    engine = get_connection()
    try: return pd.read_sql_query("SELECT * FROM store_mapping", engine)
    except: return pd.DataFrame(columns=['promotor', 'store_name'])

def delete_store_mapping(promotor):
    engine = get_connection()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM store_mapping WHERE promotor = :p"), {"p": promotor})

def get_upload_history():
    engine = get_connection()
    try: return pd.read_sql_query("SELECT upload_timestamp, COUNT(*) as jumlah_data FROM sales_daily GROUP BY upload_timestamp ORDER BY upload_timestamp DESC", engine)
    except: return pd.DataFrame()

def delete_by_upload_time(ts):
    engine = get_connection()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sales_daily WHERE upload_timestamp = :ts"), {"ts": ts})

def get_targets_by_store(store_name, week_period):
    engine = get_connection()
    try:
        df = pd.read_sql_query(text("SELECT category, sub_category, target_value FROM sales_targets_weekly WHERE store_name = :s AND week_period = :w"), engine, params={"s":store_name, "w":week_period})
        return {(row['category'], row['sub_category']): row['target_value'] for _, row in df.iterrows()}
    except: return {}

def update_target_value(store_name, category, sub_category, week_period, new_target):
    engine = get_connection()
    with engine.begin() as conn:
        query = """INSERT INTO sales_targets_weekly (store_name, category, sub_category, week_period, target_value) 
                   VALUES (:s, :c, :sub, :w, :t) 
                   ON CONFLICT (store_name, category, sub_category, week_period) DO UPDATE 
                   SET target_value=EXCLUDED.target_value"""
        conn.execute(text(query), {"s":store_name, "c":category, "sub":sub_category, "w":week_period, "t":new_target})

def save_promotor_target(bulan, promotor, target_value, grade=None):
    engine = get_connection()
    with engine.begin() as conn:
        query = """INSERT INTO promotor_targets (bulan, promotor, target, grade) 
                   VALUES (:b, :p, :t, :g) 
                   ON CONFLICT (bulan, promotor) DO UPDATE 
                   SET target=EXCLUDED.target, grade=EXCLUDED.grade"""
        conn.execute(text(query), {"b":bulan, "p":promotor, "t":target_value, "g":grade})

def get_promotor_targets(bulan):
    engine = get_connection()
    try:
        df = pd.read_sql_query(text("SELECT promotor, target, grade FROM promotor_targets WHERE bulan = :b"), engine, params={"b":bulan})
        return {row['promotor']: {'target': row['target'], 'grade': row['grade']} for _, row in df.iterrows()}
    except: return {}

