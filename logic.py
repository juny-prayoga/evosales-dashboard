import pandas as pd
from io import BytesIO
import re

def generate_excel_template():
    columns = ["TGL", "TIPE", "IMEI", "QTY", "DATE SCAN", "PROMOTOR", "Claim Type", "HARGA"]
    example_data = [["2026-01-31 20:03:00", "Samsung Galaxy A26 5G 8/256 - Mint", "351630680729299", 1, "31 Januari 2026", "Rasdi", "tembak", 4199000]]
    df = pd.DataFrame(example_data, columns=columns)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Template_Upload')
    return output.getvalue()

def process_daily_recap(df):
    """Fungsi hitung rekap harian (Smartphone Only) - DASHBOARD"""
    if df.empty: return pd.DataFrame()
    df_proc = df.copy()
    df_proc.columns = [str(c).strip().upper() for c in df_proc.columns]
    
    if 'PROMOTOR' not in df_proc.columns or 'QTY' not in df_proc.columns: return pd.DataFrame()
    df_proc['QTY'] = pd.to_numeric(df_proc['QTY'], errors='coerce').fillna(0)
    
    exclude_common = ['TAB', 'WATCH', 'BUDS', 'TWS', 'BAND', 'TV', 'FIT', 'CASE', 'COVER', 'STRAP', 'ADAPTER', 'CABLE', 'CHARGER']
    exclude_strict = [r'\bPO\b', r'\bAT\b']
    pattern = f"{'|'.join(exclude_common)}|{'|'.join(exclude_strict)}"
    
    if 'TIPE' in df_proc.columns:
        df_proc['TIPE'] = df_proc['TIPE'].astype(str)
        df_smartphone = df_proc[~df_proc['TIPE'].str.contains(pattern, case=False, na=False, regex=True)].copy()
    else:
        df_smartphone = df_proc.copy()
    
    recap = df_smartphone.groupby('PROMOTOR')['QTY'].sum().reset_index()
    recap.columns = ['NAMA PROMOTOR', 'TOTAL CLOSING']
    recap = recap.sort_values(by='TOTAL CLOSING', ascending=False).reset_index(drop=True)
    return recap

# --- FUNGSI KLASIFIKASI & WEEKLY REPORT ---

def classify_product(product_name):
    name = str(product_name).upper()
    
    # 1. ACCESSORIES FILTER
    if any(x in name for x in ['CASE', 'ADAPTER', 'CABLE', 'CHARGER', 'STRAP']): return None, None

    # 2. ECO
    if 'TAB' in name: return 'ECO', 'TABLET'
    if 'BAND' in name or 'FIT' in name : return 'ECO', 'BAND'
    if 'WATCH' in name: return 'ECO', 'WATCH'
    if 'BUDS' in name : return 'ECO', 'TWS'
    if 'TV' in name: return 'ECO', 'TV'
    
    # 3. FLAGSHIP
    if 'Z FLIP' in name or 'Z FOLD' in name: return 'FLAGSHIP', 'Z SERIES'
    if re.search(r'S\d\d', name): return 'FLAGSHIP', 'S SERIES' 
    
    # 4. A SERIES
    if re.search(r'A5\d', name): return 'A SERIES', 'HIGH'
    if re.search(r'A3\d', name) or re.search(r'A2\d', name) or 'A17 5G' in name: return 'A SERIES', 'MID'
    if re.search(r'A1\d', name) or re.search(r'A0\d', name): return 'A SERIES', 'ENTRY'
    
    return 'OTHERS', 'OTHERS'

def get_weekly_data(df, selected_week, mapping_dict, target_store=None):
    """
    Menghitung ACTUAL sales dengan membaca stempel Toko secara permanen.
    """
    if df.empty: return {}
    if 'week_period' not in df.columns: return {}
    
    df_week = df[df['week_period'] == selected_week].copy()
    actuals = {}
    
    for _, row in df_week.iterrows():
        promotor = str(row.get('promotor', '')).strip().upper()
        
        # --- FIX STEMPEL PERMANEN ---
        # Prioritaskan baca dari database, jika kosong baru pakai mapping admin
        if 'toko' in row and pd.notna(row['toko']) and str(row['toko']).strip() != "":
            current_store = str(row['toko']).strip().upper()
        else:
            current_store = mapping_dict.get(promotor, 'OTHERS').upper()
            
        if target_store and current_store != target_store.upper():
            continue 
            
        qty = row.get('qty', 0)
        name = str(row.get('tipe', ''))
        
        if re.search(r'\bPO\b|\bAT\b', name, re.IGNORECASE): continue
            
        main_cat, sub_cat = classify_product(name)
        
        if main_cat and sub_cat:
            key = (main_cat, sub_cat)
            actuals[key] = actuals.get(key, 0) + qty
            
    return actuals

def get_detailed_breakdown(df, simplify=False):
    """
    Menghasilkan data breakdown dengan tetap mempertahankan stempel Toko.
    """
    if df.empty: return pd.DataFrame()
    
    df_proc = df.copy()
    df_proc.columns = [str(c).strip().upper() for c in df_proc.columns]
    
    df_proc['QTY'] = pd.to_numeric(df_proc['QTY'], errors='coerce').fillna(0)
    df_proc['HARGA'] = pd.to_numeric(df_proc['HARGA'], errors='coerce').fillna(0)
    
    exclude_common = ['TAB', 'WATCH', 'BUDS', 'TWS', 'BAND', 'TV', 'FIT', 'CASE', 'COVER', 'STRAP', 'ADAPTER', 'CABLE', 'CHARGER']
    exclude_strict = [r'\bPO\b', r'\bAT\b']
    pattern = f"{'|'.join(exclude_common)}|{'|'.join(exclude_strict)}"
    
    if 'TIPE' in df_proc.columns:
        df_proc['TIPE'] = df_proc['TIPE'].astype(str)
        df_clean = df_proc[~df_proc['TIPE'].str.contains(pattern, case=False, na=False, regex=True)].copy()
    else:
        df_clean = df_proc.copy()
        
    if simplify:
        df_clean['TIPE'] = df_clean['TIPE'].apply(simplify_model_name)
        
    # --- FIX STEMPEL PERMANEN ---
    # Jika tabel punya kolom TOKO, ikut sertakan dalam grouping agar tidak hilang!
    if 'TOKO' in df_clean.columns:
        breakdown = df_clean.groupby(['TOKO', 'PROMOTOR', 'TIPE'])[['QTY', 'HARGA']].sum().reset_index()
    else:
        breakdown = df_clean.groupby(['PROMOTOR', 'TIPE'])[['QTY', 'HARGA']].sum().reset_index()
    
    return breakdown

def simplify_model_name(full_name):
    """
    Membersihkan nama produk agar varian RAM/Warna hilang.
    Contoh: "Samsung Galaxy A07 8/128 - Black" -> "Samsung Galaxy A07"
    """
    name = str(full_name)
    
    # 1. Hapus pola RAM/ROM (Angka/Angka), contoh: 8/128, 12/256, 4/64
    name = re.sub(r'\b\d+/\d+\b', '', name)
    
    # 2. Hapus Warna (Biasanya dipisah tanda strip " - ")
    # Ambil kata SEBELUM tanda strip pertama
    if ' - ' in name:
        name = name.split(' - ')[0]
        
    # 3. Hapus kata-kata spesifik yang mengganggu (Opsional)
    # Misal: "Game Edition", "Power Pack"
    name = re.sub(r'(?i)Game Edition|Power Pack', '', name)
    
    # 4. Rapikan spasi berlebih
    return name.strip()