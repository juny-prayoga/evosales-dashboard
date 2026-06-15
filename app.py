import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
from datetime import datetime
from streamlit_option_menu import option_menu # Library Menu Baru

# Import module lokal
from database import (init_db, get_all_sales, add_master_produk, get_all_master, 
                      delete_master, get_upload_history, delete_by_upload_time,
                      add_store_mapping, get_all_store_mappings, delete_store_mapping,
                      get_targets_by_store, update_target_value, 
                      delete_sales_by_ids, get_existing_imeis)

from logic import (generate_excel_template, process_daily_recap, 
                   classify_product, get_weekly_data, get_detailed_breakdown)

st.set_page_config(page_title="Samsung Sales Analyst", layout="wide", page_icon="📱")
init_db()

# --- FUNGSI BANTUAN ---
def get_week_label(date_obj):
    try:
        year, week, day = date_obj.isocalendar()
        return f"{year}-W{week:02d}"
    except:
        return "Unknown"

# ==============================================================================
# 🎨 MODERN SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/samsung.png", width=60)
    st.markdown("### **Sales Analyst**")
    
    selected_nav = option_menu(
        menu_title=None, 
        options=["Dashboard", "Weekly Report", "Monthly Report", "Input Data", "Database View", "Admin Panel"],
        icons=["speedometer2", "bar-chart-line", "calendar-month", "cloud-upload", "table", "gear"], 
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#3182ce", "font-size": "16px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin":"2px", "--hover-color": "#f0f2f6"},
            "nav-link-selected": {"background-color": "#0066cc", "color": "white"},
        }
    )

# Mapping Menu
if selected_nav == "Dashboard": menu = "Dashboard Utama"
elif selected_nav == "Weekly Report": menu = "Weekly Report (Target vs Actual)"
elif selected_nav == "Monthly Report": menu = "Monthly Report" # <--- TAMBAHKAN BARIS INI
elif selected_nav == "Input Data": menu = "Input Daily Report"
elif selected_nav == "Database View": menu = "Lihat Data & Filter"
elif selected_nav == "Admin Panel": menu = "ADMIN_PAGE"

# ==============================================================================
# 1. DASHBOARD UTAMA (REKAP & WA ONLY)
# ==============================================================================
if menu == "Dashboard Utama":
    current_date = datetime.now()
    current_week_label = get_week_label(current_date)
    
    st.title(f"📊 Dashboard Utama")
    st.caption("Monitoring harian performa penjualan Smartphone.")
    
    df_sales = get_all_sales()
    
    if not df_sales.empty:
        bulan_map = {
            'Januari': 'January', 'Februari': 'February', 'Maret': 'March', 
            'April': 'April', 'Mei': 'May', 'Juni': 'June', 'Juli': 'July', 
            'Agustus': 'August', 'September': 'September', 'Oktober': 'October', 
            'November': 'November', 'Desember': 'December'
        }
        
        # 1. Ambil kolom date_scan dan terjemahkan bulannya
        temp_date_scan = df_sales['date_scan'].astype(str)
        for id_bln, en_bln in bulan_map.items():
            temp_date_scan = temp_date_scan.str.replace(id_bln, en_bln, case=False, regex=False)
            
        # 2. Paksa baca dari date_scan
        df_sales['date_obj'] = pd.to_datetime(temp_date_scan, errors='coerce')
        
        # 3. (Opsional) Jika date_scan kosong melompong, baru pakai 'tgl' sebagai cadangan darurat
        df_sales['date_obj'] = df_sales['date_obj'].fillna(pd.to_datetime(df_sales['tgl'], errors='coerce'))
        
        # 4. Buat label Week
        df_sales['week_period'] = df_sales['date_obj'].apply(get_week_label)
        
        all_weeks = sorted(df_sales['week_period'].unique().tolist(), reverse=True)
        default_index = all_weeks.index(current_week_label) if current_week_label in all_weeks else 0
        selected_week = st.selectbox("📅 Pilih Periode Minggu:", all_weeks, index=default_index)
        
        df_view = df_sales[df_sales['week_period'] == selected_week].copy()
        
        if not df_view.empty:
            st.divider()
            rekap = process_daily_recap(df_view)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📋 Tabel Rekap")
                st.dataframe(rekap, use_container_width=True)
            
            with col2:
                st.subheader("💬 Format WhatsApp")
                full_name_map = {
                    "ELIZA": "ELIZA DEA ARRAHMA", "CARMEL": "CARMELITA CRISTY",
                    "FITRI": "FITRIA NUR AINI", "MARWA": "MARWAH SOLIHAH",
                    "DELA": "CECILIA DELA", "RASDI": "RASDI",
                    "RISMA": "RISMA MELATI", "SATRIA": "SATRIA ARTIA MUKTI",
                    "SINTIYA": "SINTIYA RAHMA",
                }

                sort_wa = st.radio("Urutkan Nama:", ["Abjad (A-Z)", "Penjualan Tertinggi"], horizontal=True, label_visibility="collapsed")
                
                if not rekap.empty:
                    rekap_wa = rekap.copy()
                    rekap_wa['NAMA DISPLAY'] = rekap_wa['NAMA PROMOTOR'].apply(lambda x: full_name_map.get(str(x).upper(), str(x).upper()))
                    
                    if sort_wa == "Abjad (A-Z)":
                        rekap_wa = rekap_wa.sort_values(by="NAMA DISPLAY", ascending=True)
                    else:
                        rekap_wa = rekap_wa.sort_values(by="TOTAL CLOSING", ascending=False)

                    try:
                        week_num = int(selected_week.split('-')[1].replace("W", ""))
                        header_week = f"W{week_num}"
                    except: header_week = selected_week

                    wa_text = f"*{header_week} smartphone only*\n\n*Evogad group*\n\n"
                    for _, row in rekap_wa.iterrows():
                        wa_text += f"{row['NAMA DISPLAY']} : {int(row['TOTAL CLOSING'])}\n"
                    st.text_area("Copy Text:", value=wa_text, height=350)
                else:
                    st.warning("Tidak ada data Smartphone.")
    else:
        st.info("Database kosong.")

# ==============================================================================
# MENU BARU: MONTHLY REPORT & INSENTIF
# ==============================================================================
elif menu == "Monthly Report":
    st.title("📅 Monthly Report & Insentif")
    st.markdown("💡 **Aturan:** 100% insentif cair 100%. | 90% insentif cair 50%.")

    df_sales = get_all_sales()
    if not df_sales.empty:
        # --- PRE-PROCESSING TANGGAL ---
        bulan_map = {
            'Januari': 'January', 'Februari': 'February', 'Maret': 'March', 
            'April': 'April', 'Mei': 'May', 'Juni': 'June', 'Juli': 'July', 
            'Agustus': 'August', 'September': 'September', 'Oktober': 'October', 
            'November': 'November', 'Desember': 'December'
        }
        
        temp_date_scan = df_sales['date_scan'].astype(str)
        for id_bln, en_bln in bulan_map.items():
            temp_date_scan = temp_date_scan.str.replace(id_bln, en_bln, case=False, regex=False)
            
        df_sales['date_obj'] = pd.to_datetime(temp_date_scan, errors='coerce').fillna(pd.to_datetime(df_sales['tgl'], errors='coerce'))
        df_sales['bulan_label'] = df_sales['date_obj'].dt.strftime('%B %Y')
        df_sales['week_period'] = df_sales['date_obj'].apply(get_week_label)
        
        list_bulan = df_sales['bulan_label'].dropna().unique().tolist()
        
        if list_bulan:
            # --- BAGIAN FILTER (BULAN & MINGGU) ---
            st.divider()
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                sel_bulan = st.selectbox("📅 Pilih Bulan:", list_bulan, key="sel_bulan_omzet")
            
            # Filter Data by Bulan
            df_bulan = df_sales[df_sales['bulan_label'] == sel_bulan].copy()
            
            with col_f2:
                list_week = sorted(df_bulan['week_period'].dropna().unique().tolist())
                sel_week = st.multiselect("📆 Filter Minggu (Opsional):", list_week, default=list_week, help="Kosongkan atau pilih semua untuk melihat full 1 bulan.")
            
            # Filter Data by Minggu
            if sel_week:
                df_bulan = df_bulan[df_bulan['week_period'].isin(sel_week)]
                
            # --- MAPPING TOKO ---
            df_map_toko = get_all_store_mappings()
            dict_toko = dict(zip(df_map_toko['promotor'].str.upper(), df_map_toko['store_name'].str.upper()))
            
            if 'toko' in df_bulan.columns:
                df_bulan['toko'] = df_bulan['toko'].replace(['', 'UNKNOWN', None], pd.NA).fillna(df_bulan['promotor'].str.upper().map(dict_toko)).fillna('UNKNOWN')
            else:
                df_bulan['toko'] = df_bulan['promotor'].str.upper().map(dict_toko).fillna('UNKNOWN')
            
            # --- HITUNG OMZET (ACTUAL) ---
            df_omzet = df_bulan.groupby(['toko', 'promotor'])['harga'].sum().reset_index()
            
            # --- UI: SATU HALAMAN OVERVIEW SEMUA TOKO ---
            st.subheader("📊 Executive Summary")
            
            # 1. AMBIL TARGET DARI DATABASE
            from database import get_promotor_targets, save_promotor_target
            saved_targets_data = get_promotor_targets(sel_bulan)
            
            df_base = df_omzet[['toko', 'promotor']].drop_duplicates().copy()
            df_base['promotor'] = df_base['promotor'].str.upper()
            
            # Ekstrak target dan manual grade dari dict
            df_base['Target'] = df_base['promotor'].apply(lambda p: saved_targets_data.get(p, {}).get('target', 450000000))
            df_base['Manual_Grade'] = df_base['promotor'].apply(lambda p: saved_targets_data.get(p, {}).get('grade', None))
            df_targets = df_base.copy()
            
            # 2. GABUNGKAN DENGAN ACTUAL HARI INI
            dict_actual = dict(zip(df_omzet['promotor'].str.upper(), df_omzet['harga']))
            df_targets['Actual'] = df_targets['promotor'].map(dict_actual).fillna(0)
            
            # 3. KALKULASI PENCAPAIAN
            df_targets['% Ach'] = (df_targets['Actual'] / df_targets['Target']) * 100
            df_targets['% Ach'] = df_targets['% Ach'].fillna(0)
            
            # Tentukan Auto Grade
            df_targets['Auto_Grade'] = df_targets['% Ach'].apply(lambda x: 'A' if x >= 100 else ('B' if x >= 90 else ('C' if x >= 80 else 'D')))
            
            # Gunakan Manual Grade jika ada, kalau tidak pakai Auto Grade
            df_targets['Grade'] = df_targets.apply(lambda row: row['Manual_Grade'] if pd.notna(row['Manual_Grade']) and row['Manual_Grade'] != "" else row['Auto_Grade'], axis=1)
            
            # 4. REKAP TOKO (SUMMARY)
            summary_data = []
            toko_list = sorted(df_targets['toko'].unique())
            
            grand_target = df_targets['Target'].sum()
            grand_actual = df_targets['Actual'].sum()
            
            for t_name in toko_list:
                df_t = df_targets[df_targets['toko'] == t_name]
                t_target = df_t['Target'].sum()
                t_actual = df_t['Actual'].sum()
                t_ach = (t_actual / t_target * 100) if t_target > 0 else 0
                
                summary_data.append({
                    "Toko": t_name,
                    "Target": f"Rp {t_target:,.0f}".replace(",", "."),
                    "Actual": f"Rp {t_actual:,.0f}".replace(",", "."),
                    "% Ach": t_ach
                })

            # 5. UI METRIK GRAND TOTAL
            st.write("") 
            m1, m2, m3 = st.columns(3)
            m1.metric("🌟 GRAND TOTAL TARGET", f"Rp {grand_target:,.0f}".replace(",", "."))
            m2.metric("🏆 GRAND TOTAL ACTUAL", f"Rp {grand_actual:,.0f}".replace(",", "."))
            grand_ach = (grand_actual / grand_target * 100) if grand_target > 0 else 0
            m3.metric("📈 TOTAL ACHIEVEMENT", f"{grand_ach:.2f}%")
            
            # 6. UI TABEL REKAP TOKO
            if summary_data:
                st.dataframe(
                    pd.DataFrame(summary_data),
                    column_config={
                        "Toko": st.column_config.TextColumn("🏪 Nama Toko"),
                        "Target": st.column_config.TextColumn("🎯 Target"), 
                        "Actual": st.column_config.TextColumn("💰 Actual"), 
                        "% Ach": st.column_config.ProgressColumn("📊 % Ach", format="%.2f%%", min_value=0, max_value=150)
                    },
                    hide_index=True, use_container_width=True
                )

            # ====================================================================
            # 8. UI TABEL DETAIL PROMOTOR (UPDATABLE GRADE)
            # ====================================================================
            st.subheader("👥 Detail Kinerja per Promotor")
            
            df_display = df_targets[['toko', 'promotor', 'Target', 'Actual', '% Ach', 'Grade']].sort_values(by=["toko", "promotor"]).reset_index(drop=True)
            
            df_display['Target_Text'] = df_display['Target'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            df_display['Actual_Text'] = df_display['Actual'].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
          
            # Gunakan data_editor alih-alih dataframe
            edited_df = st.data_editor(
                df_display[['toko', 'promotor', 'Target_Text', 'Actual_Text', '% Ach', 'Grade']],
                column_config={
                    "toko": st.column_config.TextColumn("🏪 Toko"),
                    "promotor": st.column_config.TextColumn("👤 Promotor"),
                    "Target_Text": st.column_config.TextColumn("🎯 Target"),
                    "Actual_Text": st.column_config.TextColumn("💰 Actual"),
                    "% Ach": st.column_config.ProgressColumn("📊 % Ach", format="%.2f%%", min_value=0, max_value=150),
                    "Grade": st.column_config.SelectboxColumn("🏆 Grade", options=["A", "B", "C", "D"], required=False) # Kolom interaktif
                },
                # PENGUNCIAN KOLOM DIPINDAHKAN KE SINI:
                disabled=["toko", "promotor", "Target_Text", "Actual_Text", "% Ach"], 
                hide_index=True, use_container_width=True,
                key=f"editor_grade_{sel_bulan}"
            )
            
            col_save1, col_save2 = st.columns([1, 4])
            with col_save1:
                if st.button("💾 Simpan Grade", type="primary", use_container_width=True):
                    # Bandingkan data awal dengan data hasil edit
                    for i in range(len(df_display)):
                        promo = df_display.loc[i, 'promotor']
                        old_grade = df_display.loc[i, 'Grade']
                        new_grade = edited_df.loc[i, 'Grade']
                        
                        # Jika ada perubahan grade, simpan ke database
                        if old_grade != new_grade:
                            current_target = df_targets[df_targets['promotor'] == promo]['Target'].values[0]
                            # Panggil save_promotor_target dengan grade baru
                            save_promotor_target(sel_bulan, promo, current_target, new_grade)
                    
                    st.success("Perubahan Grade berhasil disimpan!")
                    st.rerun()

            # ====================================================================
            # 7. FITUR EDIT TARGET
            # ====================================================================
            st.divider()
            st.subheader("🎯 Setup Target Promotor")
            
            with st.expander("⚙️ Klik di sini untuk Mengatur Target Promotor", expanded=False):
                col_ed1, col_ed2, col_ed3 = st.columns([2, 2, 1])
                
                with col_ed1:
                    list_promo = sorted(df_targets['promotor'].unique().tolist())
                    pilih_promo = st.selectbox("👤 Pilih Promotor:", list_promo, key="edit_promo_sel")
                
                with col_ed2:
                    # Target value (bukan dictionary)
                    target_saat_ini = df_targets[df_targets['promotor'] == pilih_promo]['Target'].values[0]
                    input_target = st.number_input("💰 Masukkan Target Baru:", min_value=0, step=10000000, value=int(target_saat_ini), key="edit_target_val")
                
                with col_ed3:
                    st.write("") 
                    st.write("")
                    if st.button("💾 Simpan Target", type="primary", use_container_width=True):
                        # Ambil grade saat ini agar tidak hilang
                        current_grade = df_targets[df_targets['promotor'] == pilih_promo]['Grade'].values[0]
                        save_promotor_target(sel_bulan, pilih_promo, input_target, current_grade)
                        st.success(f"Target {pilih_promo} diperbarui!")
                        st.rerun()

    else:
        st.info("Belum ada data penjualan.")

# ==============================================================================
# 2. WEEKLY REPORT (DENGAN TABS: EVALUASI & TREN)
# ==============================================================================
elif menu == "Weekly Report (Target vs Actual)":
    st.title("📈 Weekly Report")
    st.caption("Laporan Target vs Actual Mingguan.")
    
    df = get_all_sales()
    df_map = get_all_store_mappings()
    mapping_dict = dict(zip(df_map['promotor'], df_map['store_name']))
    
    if not df.empty:
        # --- APPLY STEMPEL PERMANEN KE DF MINGGUAN ---
        dict_toko = dict(zip(df_map['promotor'].str.upper(), df_map['store_name'].str.upper()))
        if 'toko' in df.columns:
            df['toko'] = df['toko'].replace(['', 'UNKNOWN', None], pd.NA).fillna(df['promotor'].str.upper().map(dict_toko)).fillna('UNKNOWN')
        else:
            df['toko'] = df['promotor'].str.upper().map(dict_toko).fillna('UNKNOWN')
        # ---------------------------------------------
        
        bulan_map = {
            'Januari': 'January', 'Februari': 'February', 'Maret': 'March', 
            'April': 'April', 'Mei': 'May', 'Juni': 'June', 'Juli': 'July', 
            'Agustus': 'August', 'September': 'September', 'Oktober': 'October', 
            'November': 'November', 'Desember': 'December'
        }
        
        temp_date_scan = df['date_scan'].astype(str)
        for id_bln, en_bln in bulan_map.items():
            temp_date_scan = temp_date_scan.str.replace(id_bln, en_bln, case=False, regex=False)
            
        df['date_obj'] = pd.to_datetime(temp_date_scan, errors='coerce').fillna(pd.to_datetime(df['tgl'], errors='coerce'))
        df['week_period'] = df['date_obj'].apply(get_week_label)
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
        
        all_weeks = sorted(df['week_period'].unique().tolist(), reverse=True)
        
        # --- PEMBUATAN DUA TAB UTAMA ---
        tab_eval, tab_trend = st.tabs(["🎯 Evaluasi Mingguan", "📉 Tren Performa Multi-Minggu"])
        
        with tab_eval:
            selected_week = st.selectbox("📅 Pilih Periode Minggu:", all_weeks, key="sel_week_weekly")
            
            st.divider()
            if not mapping_dict: st.warning("⚠️ Belum ada mapping Promotor-Toko.")
            
            # --- TABEL UTAMA TARGET VS ACTUAL ---
            tab1, tab2, tab3 = st.tabs(["🟦 EVOGAD", "🟩 EVOGAD2", "🟪 SPS"])
            stores_config = [("EVOGAD", tab1), ("EVOGAD2", tab2), ("SPS", tab3)]
            
            skeleton = [
                ("FLAGSHIP", "Z SERIES"), ("FLAGSHIP", "S SERIES"),
                ("A SERIES", "HIGH"), ("A SERIES", "MID"), ("A SERIES", "ENTRY"),
                ("ECO", "TABLET"), ("ECO", "WATCH"), ("ECO", "TWS"), ("ECO", "BAND"), ("ECO", "TV")
            ]
            
            for store_name, tab in stores_config:
                with tab:
                    saved_targets = get_targets_by_store(store_name, selected_week)
                    actual_data = get_weekly_data(df, selected_week, mapping_dict, target_store=store_name)
                    
                    final_report = []
                    for main, sub in skeleton:
                        target = saved_targets.get((main, sub), 0)
                        actual = actual_data.get((main, sub), 0)
                        percent = (actual / target * 100) if target > 0 else (0 if actual == 0 else 100)
                        final_report.append({
                            "Kategori": main, "Sub-Kategori": sub,
                            "TARGET": int(target), "ACTUAL": int(actual), "% ACH": f"{percent:.0f}%"
                        })
                    
                    df_report = pd.DataFrame(final_report)

                    col_left, col_right = st.columns([1.2, 1]) 
                    
                    with col_left:
                        st.subheader(f"🎯 Target {store_name}")
                        edited_report = st.data_editor(
                            df_report,
                            column_config={
                                "TARGET": st.column_config.NumberColumn("TARGET", min_value=0, step=1, required=True),
                                "ACTUAL": st.column_config.NumberColumn(disabled=True),
                                "% ACH": st.column_config.TextColumn(disabled=True),
                                "Kategori": st.column_config.TextColumn(disabled=True),
                                "Sub-Kategori": st.column_config.TextColumn(disabled=True),
                            },
                            hide_index=True, use_container_width=True, key=f"editor_{store_name}_{selected_week}"
                        )
                        
                        if st.button(f"💾 Simpan Target {store_name}", key=f"btn_save_{store_name}_{selected_week}", type="primary", use_container_width=True):
                            for index, row in edited_report.iterrows():
                                update_target_value(store_name, row['Kategori'], row['Sub-Kategori'], selected_week, row['TARGET'])
                            st.success(f"✅ Target {store_name} disimpan!"); st.rerun()

                    with col_right:
                        st.subheader("📊 Pencapaian")
                        t_t = edited_report["TARGET"].sum(); t_a = edited_report["ACTUAL"].sum()
                        t_ach = (t_a / t_t * 100) if t_t > 0 else 0
                        
                        m1, m2 = st.columns(2)
                        m1.metric("Actual", f"{t_a} Unit")
                        m2.metric("Achievement", f"{t_ach:.1f}%")

                        if not edited_report.empty:
                            chart_data = edited_report.melt(id_vars=['Sub-Kategori'], value_vars=['TARGET', 'ACTUAL'], var_name='Jenis', value_name='Jumlah')
                            chart = alt.Chart(chart_data).mark_bar().encode(
                                x=alt.X('Jumlah', title='Unit'),
                                y=alt.Y('Sub-Kategori', sort=None, title=None),
                                color=alt.Color('Jenis', scale=alt.Scale(domain=['TARGET', 'ACTUAL'], range=['#CBD5E0', '#3182CE'])),
                                yOffset='Jenis:N', tooltip=['Sub-Kategori', 'Jenis', 'Jumlah']
                            ).properties(height=350) 
                            st.altair_chart(chart, use_container_width=True)

            # --- RINCIAN PENJUALAN PER TOKO (TETAP UTUH 100%) ---
            st.divider()
            c_title, c_option = st.columns([2, 1])
            with c_title:
                st.subheader("📂 Rincian Penjualan per Toko")
            with c_option:
                view_mode = st.radio("Group by:", ["Warna", "Varian RAM", "Model"], horizontal=True, key="vw_weekly")
            
            df_view_weekly = df[df['week_period'] == selected_week].copy()
            
            if view_mode == "Varian RAM":
                df_detail = get_detailed_breakdown(df_view_weekly, simplify=False)
                import re
                def clean_to_ram(text):
                    match = re.search(r'(.*?\d+/\d+)', str(text))
                    return match.group(1).strip() if match else str(text)
                
                df_detail['TIPE'] = df_detail['TIPE'].apply(clean_to_ram)
                group_cols = ['TOKO', 'PROMOTOR', 'TIPE'] if 'TOKO' in df_detail.columns else ['PROMOTOR', 'TIPE']
                df_detail = df_detail.groupby(group_cols).agg({'QTY': 'sum', 'HARGA': 'sum'}).reset_index()

            elif view_mode == "Model":  
                df_detail = get_detailed_breakdown(df_view_weekly, simplify=True)
                group_cols = ['TOKO', 'PROMOTOR', 'TIPE'] if 'TOKO' in df_detail.columns else ['PROMOTOR', 'TIPE']
                df_detail = df_detail.groupby(group_cols).agg({'QTY': 'sum', 'HARGA': 'sum'}).reset_index()

            else:
                df_detail = get_detailed_breakdown(df_view_weekly, simplify=False)
            
            if not df_detail.empty:
                # --- FIX PENENTUAN TOKO ---
                if 'TOKO' in df_detail.columns:
                    df_detail['STORE'] = df_detail['TOKO']
                else:
                    mapping_dict_upper = {k.upper(): v.upper() for k, v in mapping_dict.items()}
                    df_detail['STORE'] = df_detail['PROMOTOR'].str.upper().map(mapping_dict_upper).fillna('OTHERS')
                
                available_stores = sorted(df_detail['STORE'].unique().tolist())
                
                tabs_detail = st.tabs([f"🏠 {s}" for s in available_stores])
                for i, store_name in enumerate(available_stores):
                    with tabs_detail[i]:
                        df_store = df_detail[df_detail['STORE'] == store_name]
                        t_qty = df_store['QTY'].sum(); t_val = df_store['HARGA'].sum()
                        st.info(f"📊 Total {store_name}: **{int(t_qty)} Unit** (Rp {t_val:,.0f})")
                        
                        with st.expander(f"📈 Detail Penjualan {store_name}"):
                            df_rekap = df_store.groupby('TIPE').agg({'QTY': 'sum', 'HARGA': 'sum'}).reset_index()
                            df_rekap.columns = ['Model HP', 'Qty', 'Total Nilai'] 
                            df_rekap = df_rekap.sort_values('Qty', ascending=False)
                            df_rekap['Total Nilai'] = df_rekap['Total Nilai'].apply(lambda x: f"Rp {x:,.0f}")
                            st.dataframe(df_rekap, use_container_width=True, hide_index=True)
                            
                        with st.expander("👥 Detail Penjualan Promotor"):
                            promotor_stats = df_store.groupby('PROMOTOR')['QTY'].sum().reset_index().sort_values('QTY', ascending=False)
                            for _, p_row in promotor_stats.iterrows():
                                p_name = p_row['PROMOTOR']
                                this_p_data = df_store[df_store['PROMOTOR'] == p_name][['TIPE', 'QTY', 'HARGA']].copy()
                                this_p_data.columns = ['Model HP', 'Qty', 'Total Nilai']
                                with st.expander(f"👤 **{p_name}** ( Total: {int(p_row['QTY'])} Unit | Rp {this_p_data['Total Nilai'].sum():,.0f} )"):
                                    this_p_data['Total Nilai'] = this_p_data['Total Nilai'].apply(lambda x: f"Rp {x:,.0f}")
                                    st.dataframe(this_p_data, use_container_width=True, hide_index=True)
            else:
                st.info("Tidak ada data rincian untuk minggu ini.")

        with tab_trend:
            # --- ISI TAB 2: FITUR TREN BARU ---
            st.subheader("📈 Analisis Tren Kuantitas Penjualan")
            st.caption("Gunakan fitur ini untuk melihat fluktuasi penjualan dalam rentang beberapa minggu.")

            all_weeks_asc = sorted(df['week_period'].unique().tolist())
            
            # --- TATA LETAK FILTER ---
            c1, c2 = st.columns(2)
            with c1:
                start_w = st.selectbox("Dari Minggu:", all_weeks_asc, index=0, key="trend_start")
            with c2:
                end_w = st.selectbox("Sampai Minggu:", all_weeks_asc, index=len(all_weeks_asc)-1, key="trend_end")
                
            # Filter Kategori (Multi-Select) dibuat panjang ke samping
            pilihan_kategori = ["Smartphone", "Tablet", "Watch", "TWS", "Band", "Other Ecosystem"]
            tipe_filter = st.multiselect(
                "Filter Kategori Produk (Pilih kombinasi sesuka hati):", 
                options=pilihan_kategori, 
                default=["Smartphone"], # Default awal yang dicentang
                key="trend_filter"
            )

            df_trend = df[(df['week_period'] >= start_w) & (df['week_period'] <= end_w)].copy()

            # Pastikan data ada dan minimal 1 kategori dipilih
            if not df_trend.empty and len(tipe_filter) > 0:
                
                # --- LOGIKA PENYARINGAN PRODUK (MULTIPLE CHOICE) ---
                def get_broad_category(nama_produk):
                    main, sub = classify_product(nama_produk) if pd.notna(nama_produk) else ("UNKNOWN", "UNKNOWN")
                    if main in ["FLAGSHIP", "A SERIES"]: return "Smartphone"
                    if main == "ECO" and sub == "TABLET": return "Tablet"
                    if main == "ECO" and sub == "WATCH": return "Watch"
                    if main == "ECO" and sub in ["TWS", "BUDS"]: return "TWS"
                    if main == "ECO" and sub == "BAND": return "Band"
                    if main == "ECO": return "Other Ecosystem"
                    return "Other"
                
                # Beri label sementara pada tiap baris data
                df_trend['broad_cat'] = df_trend['tipe'].apply(get_broad_category)
                
                # Pangkas data HANYA sesuai dengan yang dicentang user
                df_trend = df_trend[df_trend['broad_cat'].isin(tipe_filter)]
                
                # Cek lagi apakah setelah disaring datanya masih ada isinya
                if not df_trend.empty:
                    view_mode_trend = st.radio("Lihat Tren Berdasarkan:", ["Total Per Minggu", "Per Toko", "Per Kategori"], horizontal=True, key="view_trend")

                    if view_mode_trend == "Total Per Minggu":
                        chart_data = df_trend.groupby('week_period')['qty'].sum().reset_index()
                        color_col = None
                    elif view_mode_trend == "Per Toko":
                        chart_data = df_trend.groupby(['week_period', 'toko'])['qty'].sum().reset_index()
                        color_col = 'toko'
                    else:
                        df_trend['Category'] = df_trend['tipe'].apply(lambda x: classify_product(x)[0] if pd.notna(x) else "UNKNOWN")
                        chart_data = df_trend.groupby(['week_period', 'Category'])['qty'].sum().reset_index()
                        color_col = 'Category'

                    # --- Visualisasi Grafik ---
                    if color_col:
                        line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                            x=alt.X('week_period:N', title='Minggu'),
                            y=alt.Y('qty:Q', title='Total Qty Terjual'),
                            color=alt.Color(f'{color_col}:N', title=view_mode_trend),
                            tooltip=['week_period', 'qty', color_col]
                        ).properties(height=400).interactive()
                    else:
                        line_chart = alt.Chart(chart_data).mark_line(point=True).encode(
                            x=alt.X('week_period:N', title='Minggu'),
                            y=alt.Y('qty:Q', title='Total Qty Terjual'),
                            color=alt.value('#3182CE'),
                            tooltip=['week_period', 'qty']
                        ).properties(height=400).interactive()

                    st.altair_chart(line_chart, use_container_width=True)

                    with st.expander("📊 Lihat Tabel Data"):
                        if color_col:
                            # 1. Buat pivot table seperti biasa
                            pivot = chart_data.pivot(index=color_col, columns='week_period', values='qty').fillna(0)
                            
                            # 2. TAMBAHKAN KOLOM TOTAL DI PALING KANAN
                            # axis=1 artinya kita menjumlahkan secara horizontal (antar minggu)
                            pivot['Total'] = pivot.sum(axis=1)
                            
                            # Tampilkan dataframe (dengan pembulatan 0 desimal agar bersih)
                            st.dataframe(pivot.style.format(precision=0), use_container_width=True)
                        else:
                            # Untuk tampilan 'Total Per Minggu', kita tambahkan baris TOTAL di bawah
                            df_total_minggu = chart_data.copy()
                            total_qty = df_total_minggu['qty'].sum()
                            
                            # Tambahkan baris rangkuman di akhir
                            st.dataframe(df_total_minggu, use_container_width=True, hide_index=True)
                            st.info(f"📈 **Total Akumulasi Qty:** {int(total_qty)} Unit")
                else:
                    st.warning("⚠️ Tidak ada penjualan untuk kategori yang dipilih pada rentang minggu ini.")
            elif len(tipe_filter) == 0:
                st.warning("⚠️ Silakan centang minimal satu kategori produk di atas.")
            else:
                st.info("Pilih rentang minggu yang valid.")

# ==============================================================================
# 3. INPUT DAILY REPORT (DENGAN UPSERT: INSERT & UPDATE CERDAS)
# ==============================================================================
elif menu == "Input Daily Report":
    st.title("📥 Input Data Penjualan")
    st.caption("Upload data harian (Excel). Sistem otomatis menambah data baru, menimpa data yang berubah, dan mengabaikan data yang sama persis.")
    
    # Download Template
    st.download_button("📄 Download Template Excel", generate_excel_template(), "template_rekap.xlsx")
    st.divider()
    
    file = st.file_uploader("Upload File Excel", type=["xlsx"])
    
    if file:
        try: # <--- INI ADALAH 'TRY' UTAMA (Pasangannya ada di paling bawah)
            # 1. Baca File
            df_up = pd.read_excel(file)
            
            # 2. Standarisasi Nama Kolom
            df_up.columns = [str(c).strip().lower().replace(" ", "_") for c in df_up.columns]
            
            # BUANG KOLOM SILUMAN EXCEL ('unnamed')
            df_up = df_up.loc[:, ~df_up.columns.str.contains('unnamed', case=False)]
            
            # Cek kolom wajib
            required_cols = ['imei', 'tipe', 'promotor']
            missing = [c for c in required_cols if c not in df_up.columns]
            
            if missing:
                st.error(f"❌ Kolom wajib tidak ditemukan: {', '.join(missing)}")
            else:
                # 3. Bersihkan Data
                df_up['imei'] = df_up['imei'].astype(str).str.strip()
                
                # FIX: STEMPEL TOKO SECARA PERMANEN SAAT UPLOAD
                from database import get_all_store_mappings 
                df_map_toko = get_all_store_mappings()
                dict_toko_saat_ini = dict(zip(df_map_toko['promotor'].str.upper(), df_map_toko['store_name'].str.upper()))
                df_up['toko'] = df_up['promotor'].str.upper().map(dict_toko_saat_ini).fillna('UNKNOWN')
                
                # Filter Tipe Aksesoris
                if 'tipe' in df_up.columns:
                    df_up['tipe'] = df_up['tipe'].astype(str)
                    blacklist = ['POWERBANK', 'ADAPTER', 'TRAVEL ADAPTER', 'AMBIL TOKO', 'HEADSET', 'CABLE']
                    patt = '|'.join(blacklist)
                    mask_drop = df_up['tipe'].str.contains(patt, case=False) | df_up['tipe'].str.contains(r'\bAT\b', case=False, regex=True)
                    df_clean = df_up[~mask_drop].copy()
                else:
                    df_clean = df_up.copy()

                # 4. CEK DUPLIKAT & PERUBAHAN (LOGIKA UPSERT VIA SUPABASE)
                from database import get_connection
                engine = get_connection()
                
                try:
                    df_db = pd.read_sql("SELECT * FROM sales_daily", engine)
                except:
                    df_db = pd.DataFrame()
                
                dict_db = df_db.set_index('imei').to_dict('index') if not df_db.empty and 'imei' in df_db.columns else {}
                
                list_insert = []
                list_update = []
                list_skip = []
                
                # Cek satu per satu baris Excel
                for _, row in df_clean.iterrows():
                    imei_val = str(row['imei']).strip()
                    
                    if imei_val not in dict_db:
                        list_insert.append(row)
                    else:
                        data_lama = dict_db[imei_val]
                        ada_beda = False
                        
                        for col in df_clean.columns:
                            if col in data_lama and col != 'imei':
                                v_baru = str(row[col]).strip()
                                v_lama = str(data_lama[col]).strip()
                                
                                if v_baru.lower() in ['nan', 'none', '']: v_baru = ''
                                if v_lama.lower() in ['nan', 'none', '']: v_lama = ''
                                
                                try:
                                    if float(v_baru) == float(v_lama): continue
                                except ValueError:
                                    pass
                                
                                if v_baru != v_lama:
                                    ada_beda = True
                                    break
                        
                        if ada_beda:
                            list_update.append(row) 
                        else:
                            list_skip.append(row)   
                            
                df_insert = pd.DataFrame(list_insert)
                df_update = pd.DataFrame(list_update)
                df_skip = pd.DataFrame(list_skip)
                
                # 5. Tampilkan Laporan Pre-Upload
                st.subheader("🔍 Hasil Pengecekan Data")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Data Valid", len(df_clean))
                c2.metric("✨ Data Baru (Insert)", len(df_insert))
                c3.metric("🔄 Perlu Diperbarui (Update)", len(df_update))
                c4.metric("⏭️ Dilewati (Sama Persis)", len(df_skip), delta_color="inverse")
                
                if not df_update.empty:
                    with st.expander(f"⚠️ Lihat {len(df_update)} Data yang akan di-Update (Timpa)"):
                        st.dataframe(df_update[['promotor', 'tipe', 'imei']], use_container_width=True)
                        
                if not df_skip.empty:
                    with st.expander(f"⏭️ Lihat {len(df_skip)} Data yang Dilewati"):
                        st.caption("Data ini 100% identik dengan database. Tidak ada aksi yang dilakukan.")

                st.divider()

                # 6. Tombol Simpan (Eksekusi Insert & Update)
                if not df_insert.empty or not df_update.empty:
                    st.info(f"Siap mengeksekusi: **{len(df_insert)}** Insert Baru dan **{len(df_update)}** Update.")
                    
                    if st.button("🚀 Eksekusi Simpan ke Database", type="primary"):
                        from sqlalchemy import text
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        try:
                            # --- PROSES UPDATE ---
                            if not df_update.empty:
                                with engine.begin() as conn:
                                    for _, row in df_update.iterrows():
                                        imei_val = str(row['imei']).strip()
                                        kolom_update = [col for col in df_update.columns if col != 'imei']
                                        set_clause = ", ".join([f"{col} = :{col}" for col in kolom_update])
                                        query = text(f"UPDATE sales_daily SET {set_clause} WHERE imei = :imei")
                                        
                                        params = {col: str(row[col]) for col in kolom_update}
                                        params["imei"] = imei_val
                                        conn.execute(query, params)
                            
                            # --- PROSES INSERT ---
                            if not df_insert.empty:
                                df_save = df_insert.copy()
                                df_save['upload_timestamp'] = current_time
                                df_save.to_sql('sales_daily', engine, if_exists='append', index=False)
                            
                            st.success(f"✅ Sukses! Database berhasil diperbarui.")
                            st.balloons()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan ke database: {e}")
                else:
                    st.warning("Tidak ada data baru atau data yang perlu diupdate. Sistem aman!")

        # --- INI DIA BAGIAN YANG HILANG SEBELUMNYA ---
        except Exception as e:
            st.error(f"Gagal memproses file Excel: {e}")

# ==============================================================================
# 4. LIHAT DATA & FILTER (DENGAN FITUR HAPUS)
# ==============================================================================
# ==============================================================================
# 4. LIHAT DATA & FILTER (DENGAN FITUR HAPUS)
# ==============================================================================
elif menu == "Lihat Data & Filter": 
    st.title("🔍 Database View")
    
    df = get_all_sales()
    if not df.empty:
        # Pre-processing
        bulan_map = {
            'Januari': 'January', 'Februari': 'February', 'Maret': 'March', 
            'April': 'April', 'Mei': 'May', 'Juni': 'June', 'Juli': 'July', 
            'Agustus': 'August', 'September': 'September', 'Oktober': 'October', 
            'November': 'November', 'Desember': 'December'
        }
        
        # 1. Ambil kolom date_scan dan terjemahkan bulannya
        temp_date_scan = df['date_scan'].astype(str)
        for id_bln, en_bln in bulan_map.items():
            temp_date_scan = temp_date_scan.str.replace(id_bln, en_bln, case=False, regex=False)
            
        # 2. Paksa baca dari date_scan
        df['date_obj'] = pd.to_datetime(temp_date_scan, errors='coerce')
        
        # 3. (Opsional) Jika date_scan kosong melompong, baru pakai 'tgl' sebagai cadangan darurat
        df['date_obj'] = df['date_obj'].fillna(pd.to_datetime(df['tgl'], errors='coerce'))
        
        # 4. Buat label Week
        df['week_period'] = df['date_obj'].apply(get_week_label)
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
        
        # --- FILTERING ---
        with st.expander("🎛️ Menu Filter & Pencarian", expanded=True):
            c1, c2, c3 = st.columns(3)
            # Ambil unik value untuk filter
            week_opts = sorted(df['week_period'].unique(), reverse=True)
            promo_opts = sorted(df['promotor'].dropna().unique())
            tipe_opts = sorted(df['tipe'].dropna().unique())
            
            sel_week = c1.multiselect("📅 Minggu", week_opts)
            sel_promotor = c2.multiselect("👤 Promotor", promo_opts)
            sel_tipe = c3.multiselect("📱 Tipe", tipe_opts)
            
            c4, c5 = st.columns([1, 2])
            only_hp = c4.checkbox("📱 Smartphone Only", value=True)
            search = c5.text_input("🔍 Cari Text (IMEI / Tipe)")
            
        # Terapkan Filter
        df_f = df.copy()
        if only_hp:
            exc = ['TAB', 'WATCH', 'BUDS', 'TWS', 'BAND', 'TV', 'FIT', 'CASE', 'COVER', 'STRAP', 'ADAPTER', 'CABLE', 'CHARGER']
            exc_s = [r'\bPO\b', r'\bAT\b']
            pat = f"{'|'.join(exc)}|{'|'.join(exc_s)}"
            df_f = df_f[~df_f['tipe'].astype(str).str.contains(pat, case=False, regex=True)]
            
        if sel_week: df_f = df_f[df_f['week_period'].isin(sel_week)]
        if sel_promotor: df_f = df_f[df_f['promotor'].isin(sel_promotor)]
        if search:
            s = search.lower()
            m = df_f['tipe'].astype(str).str.lower().str.contains(s) | \
                df_f['imei'].astype(str).str.lower().str.contains(s) | \
                df_f['promotor'].astype(str).str.lower().str.contains(s)
            df_f = df_f[m]
            
        st.divider()
        st.write(f"Menampilkan **{len(df_f)}** data.")
        
        # --- FITUR HAPUS DATA ---
        mode_hapus = st.toggle("🔓 Buka Mode Hapus Data", help="Aktifkan untuk menghapus data yang salah input.")
        
        if mode_hapus:
            # Tambahkan kolom checkbox 'Pilih'
            df_f = df_f.copy() # Hindari SettingWithCopyWarning
            df_f.insert(0, "Pilih", False) # Kolom checkbox di paling kiri
            
            # Tampilkan Data Editor
            edited_df = st.data_editor(
                df_f,
                column_config={
                    "Pilih": st.column_config.CheckboxColumn("Hapus?", default=False),
                    "id": st.column_config.NumberColumn(disabled=True), # ID gak boleh diedit
                },
                disabled=["tgl", "tipe", "imei", "qty", "promotor", "harga", "date_scan"], # Kunci data asli biar gak kegeser
                hide_index=True,
                use_container_width=True,
                key="data_editor_delete"
            )
            
            # Tombol Eksekusi
            col_btn, _ = st.columns([1, 4])
            with col_btn:
                if st.button("🗑️ Hapus Data Tercentang", type="primary"):
                    # Ambil data yang dicentang
                    to_delete = edited_df[edited_df['Pilih'] == True]
                    
                    if not to_delete.empty:
                        # Ambil list ID
                        ids_to_delete = to_delete['id'].tolist()
                        
                        # Panggil fungsi database
                        delete_sales_by_ids(ids_to_delete)
                        
                        st.success(f"✅ Berhasil menghapus {len(ids_to_delete)} data!")
                        st.rerun() # Refresh halaman
                    else:
                        st.warning("⚠️ Belum ada data yang dicentang.")
        else:
            # --- MODE EDIT LANGSUNG (DENGAN NOTIFIKASI FIX) ---
            
            # 1. CEK STATUS PENYIMPANAN (Muncul setelah refresh)
            if "status_simpan" in st.session_state and st.session_state["status_simpan"]:
                st.success(f"✅ {st.session_state['pesan_simpan']}")
                # Reset status agar notifikasi hilang saat refresh berikutnya
                st.session_state["status_simpan"] = False

            st.info("📝 **Mode Edit**: Ubah angka QTY, Harga, dll di tabel lalu klik Simpan.")

            # 2. Konfigurasi Kolom
            edit_config = {
                "id": st.column_config.NumberColumn(disabled=True),
                "date_scan": st.column_config.TextColumn("Tgl Scan", disabled=True),
                "qty": st.column_config.NumberColumn("QTY", min_value=0, step=1),
                "harga": st.column_config.NumberColumn("Harga", format="Rp %d"),
                "tipe": st.column_config.TextColumn("Tipe HP"),
                "imei": st.column_config.TextColumn("IMEI")
            }

            # 3. Tampilkan Editor
            # Kita tampung hasilnya ke variabel 'df_hasil_edit'
            df_hasil_edit = st.data_editor(
                df_f,
                column_config=edit_config,
                disabled=["id", "date_scan", "tgl", "jam", "upload_timestamp", "promotor", "toko"],
                hide_index=True,
                use_container_width=True,
                key="editor_final_fix"
            )

            # 4. Tombol Simpan
            st.write("---")
            if st.button("💾 SIMPAN PERUBAHAN", type="primary"):
                try:
                    from database import get_connection
                    from sqlalchemy import text
                    engine = get_connection()
                    jumlah_berubah = 0
                    
                    data_lama = df_f.set_index('id').to_dict('index')
                    data_baru = df_hasil_edit.set_index('id').to_dict('index')
                    
                    with engine.begin() as conn:
                        for id_transaksi, row_baru in data_baru.items():
                            row_lama = data_lama.get(id_transaksi)
                            
                            if row_lama:
                                kolom_cek = ['qty', 'harga', 'tipe', 'imei']
                                ada_beda = False
                                
                                for col in kolom_cek:
                                    val_lama = row_lama.get(col)
                                    val_baru = row_baru.get(col)
                                    
                                    if str(val_lama) != str(val_baru):
                                        query = text(f"UPDATE sales_daily SET {col} = :val WHERE id = :id")
                                        conn.execute(query, {"val": val_baru, "id": id_transaksi})
                                        ada_beda = True
                                
                                if ada_beda:
                                    jumlah_berubah += 1
                    
                    if jumlah_berubah > 0:
                        st.session_state["status_simpan"] = True
                        st.session_state["pesan_simpan"] = f"Berhasil menyimpan {jumlah_berubah} data!"
                        st.rerun()
                    else:
                        st.warning("⚠️ Tidak ada perubahan yang terdeteksi. Tekan ENTER di tabel sebelum Simpan.")
                        
                except Exception as e:
                    st.error(f"Error Sistem: {e}")

# ==============================================================================
# 5. ADMIN PAGE (GABUNGAN SEMUA MENU ADMIN)
# ==============================================================================
elif menu == "ADMIN_PAGE":
    st.title("⚙️ Admin Panel")
    
    tab_toko, tab_harga, tab_history = st.tabs(["🏪 Manajemen Toko", "🏷️ Master Harga", "🕰️ Riwayat Upload"])
    
    with tab_toko:
        st.subheader("Atur Lokasi Promotor")
        with st.form("add_promotor_store"):
            c1, c2 = st.columns(2)
            nama_p = c1.text_input("Nama Promotor")
            toko_p = c2.selectbox("Pilih Toko", ["EVOGAD", "EVOGAD2", "SPS"])
            if st.form_submit_button("Simpan"):
                add_store_mapping(nama_p, toko_p)
                st.success(f"✅ {nama_p} -> {toko_p}")
                st.rerun()
        st.divider()
        df_map = get_all_store_mappings()
        if not df_map.empty:
            for i, row in df_map.iterrows():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"👤 **{row['promotor']}**"); c2.write(f"🏠 {row['store_name']}")
                if c3.button("Hapus", key=f"del_{row['promotor']}"):
                    delete_store_mapping(row['promotor']); st.rerun()

    with tab_harga:
        st.subheader("Master Harga Produk")
        with st.form("m"):
            c1, c2 = st.columns(2)
            kw = c1.text_input("Keyword"); cat = c1.selectbox("Cat", ["FLAGSHIP", "A SERIES", "ECO"])
            sub = c2.text_input("Sub"); prc = c2.number_input("Harga", min_value=0)
            if st.form_submit_button("Simpan"): add_master_produk(kw, cat, sub, prc); st.rerun()
        st.dataframe(get_all_master())

    with tab_history:
        st.subheader("Riwayat Upload Data")
        df_h = get_upload_history()
        st.dataframe(df_h)
        if not df_h.empty:
            opts = {f"{r['upload_timestamp']} ({r['jumlah_data']})": r['upload_timestamp'] for _, r in df_h.iterrows()}
            sel = st.selectbox("Pilih Sesi", list(opts.keys()))
            if st.button("Hapus Sesi"): delete_by_upload_time(opts[sel]); st.rerun()



