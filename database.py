import sqlite3
import pandas as pd

def init_db():
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    
    # ... (Tabel sales_daily, master_produk, store_mapping TETAP SAMA) ...
    c.execute('''CREATE TABLE IF NOT EXISTS sales_daily
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tgl TEXT, tipe TEXT, imei TEXT, qty INTEGER,
                  date_scan TEXT, promotor TEXT, claim_type TEXT, harga REAL,
                  upload_timestamp TEXT)''') 
    
    c.execute('''CREATE TABLE IF NOT EXISTS master_produk
                 (keyword TEXT PRIMARY KEY, category TEXT, sub_category TEXT, harga REAL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS store_mapping
                 (promotor TEXT PRIMARY KEY, store_name TEXT)''')

    # --- PERUBAHAN DISINI: Tambah kolom week_period ---
    # Kita hapus tabel lama dulu biar struktur baru bisa masuk (khusus dev mode)
    # c.execute("DROP TABLE IF EXISTS sales_targets") 
    # (Aktifkan baris DROP di atas SEKALI SAJA jika error, lalu matikan lagi)
    
    c.execute('''CREATE TABLE IF NOT EXISTS sales_targets_weekly
                 (store_name TEXT, category TEXT, sub_category TEXT, 
                  week_period TEXT, target_value INTEGER,
                  PRIMARY KEY (store_name, category, sub_category, week_period))''')
                 
    conn.commit()
    conn.close()

# --- FUNGSI SALES (SAMA SEPERTI SEBELUMNYA) ---
def get_all_sales():
    conn = sqlite3.connect('business_data.db')
    try: df = pd.read_sql_query("SELECT * FROM sales_daily", conn)
    except: df = pd.DataFrame()
    conn.close()
    return df

def get_existing_imeis():
    conn = sqlite3.connect('business_data.db')
    try:
        df = pd.read_sql_query("SELECT imei FROM sales_daily WHERE imei IS NOT NULL AND imei != ''", conn)
        existing_imeis = df['imei'].astype(str).str.strip().tolist()
    except: existing_imeis = []
    conn.close()
    return existing_imeis

def update_sales_data(id_data, promotor, tipe, qty, harga):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute('''UPDATE sales_daily SET promotor=?, tipe=?, qty=?, harga=? WHERE id=?''', 
              (promotor, tipe, qty, harga, id_data))
    conn.commit()
    conn.close()

def delete_sales_by_ids(id_list):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    ph = ', '.join('?' for _ in id_list)
    c.execute(f"DELETE FROM sales_daily WHERE id IN ({ph})", id_list)
    conn.commit()
    conn.close()

# --- FUNGSI MASTER PRODUK ---
def add_master_produk(kw, cat, sub, prc):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO master_produk VALUES (?, ?, ?, ?)", (kw, cat, sub, prc))
    conn.commit()
    conn.close()

def get_all_master():
    conn = sqlite3.connect('business_data.db')
    df = pd.read_sql_query("SELECT * FROM master_produk", conn)
    conn.close()
    return df

def delete_master(kw):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM master_produk WHERE keyword = ?", (kw,))
    conn.commit()
    conn.close()

# --- FUNGSI MAPPING TOKO ---
def add_store_mapping(promotor, store_name):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO store_mapping VALUES (?, ?)", (promotor.upper(), store_name.upper()))
    conn.commit()
    conn.close()

def get_all_store_mappings():
    conn = sqlite3.connect('business_data.db')
    try: df = pd.read_sql_query("SELECT * FROM store_mapping", conn)
    except: df = pd.DataFrame(columns=['promotor', 'store_name'])
    conn.close()
    return df

def delete_store_mapping(promotor):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM store_mapping WHERE promotor = ?", (promotor,))
    conn.commit()
    conn.close()

# --- FUNGSI RIWAYAT UPLOAD ---
def get_upload_history():
    conn = sqlite3.connect('business_data.db')
    try: df = pd.read_sql_query("SELECT upload_timestamp, COUNT(*) as jumlah_data FROM sales_daily GROUP BY upload_timestamp ORDER BY upload_timestamp DESC", conn)
    except: df = pd.DataFrame()
    conn.close()
    return df

def delete_by_upload_time(ts):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM sales_daily WHERE upload_timestamp = ?", (ts,))
    conn.commit()
    conn.close()

# --- FUNGSI TARGET BARU (DENGAN MINGGU) ---

def get_targets_by_store(store_name, week_period):
    """Ambil target spesifik untuk toko DAN minggu tertentu"""
    conn = sqlite3.connect('business_data.db')
    try:
        query = """SELECT category, sub_category, target_value 
                   FROM sales_targets_weekly 
                   WHERE store_name = ? AND week_period = ?"""
        df = pd.read_sql_query(query, conn, params=(store_name, week_period))
        
        target_dict = {}
        for _, row in df.iterrows():
            target_dict[(row['category'], row['sub_category'])] = row['target_value']
    except:
        target_dict = {}
    conn.close()
    return target_dict

def update_target_value(store_name, category, sub_category, week_period, new_target):
    """Simpan target spesifik untuk minggu itu"""
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO sales_targets_weekly 
                 (store_name, category, sub_category, week_period, target_value) 
                 VALUES (?, ?, ?, ?, ?)''', 
              (store_name, category, sub_category, week_period, new_target))
    conn.commit()
    conn.close()
    
# --- UPDATE DATA (AUTO DETECT TABLE) ---
def update_sales_simple(id_row, col_name, new_val):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    try:
        # 1. Coba simpan ke 'sales_data' (Versi Stabil/Rollback)
        query_a = f"UPDATE sales_data SET {col_name} = ? WHERE id = ?"
        c.execute(query_a, (new_val, id_row))
        
        # 2. Jika tidak ada yang terupdate (rowcount=0), coba ke 'sales_daily' (Versi Upload)
        if c.rowcount == 0:
            query_b = f"UPDATE sales_daily SET {col_name} = ? WHERE id = ?"
            c.execute(query_b, (new_val, id_row))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"Gagal Update: {e}") # Cek terminal jika masih gagal
        return False
    finally:
        conn.close()

# --- FITUR TARGET PROMOTOR PERMANEN ---
def save_promotor_target(bulan, promotor, target_value):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    try:
        # Bikin tabel otomatis jika belum ada
        c.execute('''CREATE TABLE IF NOT EXISTS promotor_targets 
                     (bulan TEXT, promotor TEXT, target INTEGER,
                     PRIMARY KEY (bulan, promotor))''')
        # Simpan atau update targetnya
        c.execute('''INSERT OR REPLACE INTO promotor_targets (bulan, promotor, target) 
                     VALUES (?, ?, ?)''', (bulan, promotor, target_value))
        conn.commit()
    except Exception as e:
        print(f"Error simpan target: {e}")
    finally:
        conn.close()

def get_promotor_targets(bulan):
    conn = sqlite3.connect('business_data.db')
    c = conn.cursor()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS promotor_targets 
                     (bulan TEXT, promotor TEXT, target INTEGER,
                     PRIMARY KEY (bulan, promotor))''')
        c.execute('SELECT promotor, target FROM promotor_targets WHERE bulan = ?', (bulan,))
        return dict(c.fetchall())
    except Exception:
        return {}
    finally:
        conn.close()