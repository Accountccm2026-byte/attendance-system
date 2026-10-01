import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import base64

st.set_page_config(page_title="ระบบบันทึกเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน")

EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

REC_COLUMNS = [
    "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
    "วันที่", "สถานะ", "เวลาเข้า", "เวลาออก",
    "จำนวนชั่วโมง", "หมายเหตุ", "รูปเช็คอิน", "รูปเช็คเอาท์",
    "สายนาที", "สายชม", "OT 1.5(ชม.)", "OT 1(ชม.)"
]

def load_records():
    """Load records.csv and normalize it to the current 16-column schema."""
    if not os.path.exists(REC_FILE) or os.path.getsize(REC_FILE) == 0:
        return pd.DataFrame(columns=REC_COLUMNS)
    try:
        df = pd.read_csv(REC_FILE, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(REC_FILE, encoding="cp874")
    for col in REC_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REC_COLUMNS].copy()


if not os.path.exists(EMP_FILE) or os.path.getsize(EMP_FILE) == 0:
    pd.DataFrame(columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"]).to_csv(EMP_FILE, index=False, encoding="utf-8")
if not os.path.exists(REC_FILE) or os.path.getsize(REC_FILE) == 0:
    pd.DataFrame(columns=[
        "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
        "วันที่", "สถานะ", "เวลาเข้า", "เวลาออก",
        "จำนวนชั่วโมง", "หมายเหตุ", "รูปเช็คอิน", "รูปเช็คเอาท์",
        "สายนาที", "สายชม", "OT 1.5(ชม.)", "OT 1(ชม.)"
    ]).to_csv(REC_FILE, index=False, encoding="utf-8")

menu = st.sidebar.selectbox("เมนูหลัก", [
    "จัดการรายชื่อพนักงาน",
    "บันทึกการเข้างาน/ลา",
    "หน้าสรุปภาพรวม",
    "รายงานรายชื่อ+วันทำงาน",
    "หน้าสรุปส่ง HR",
    "📥 สำรองข้อมูล"
])

def img_cell(val):
    s = str(val)
    if s.startswith("data:image"):
        return f'<img src="{s}" width="70" />'
    return "-"

def parse_time_str(s):
    try:
        return datetime.strptime(str(s), "%H:%M")
    except:
        return None

# ==========================================
# 1. จัดการรายชื่อพนักงาน
# ==========================================
if menu == "จัดการรายชื่อพนักงาน":
    st.header("จัดการรายชื่อพนักงาน")
    df_emp = pd.read_csv(EMP_FILE, encoding="utf-8")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: eid = st.text_input("รหัสพนักงาน")
    with c2: enam = st.text_input("ชื่อพนักงาน")
    with c3: enick = st.text_input("ชื่อเล่น")
    with c4: epos = st.text_input("ตำแหน่ง")
    
    if st.button("เพิ่มพนักงาน") and eid and enam:
        exists = False
        if "รหัสพนักงาน" in df_emp.columns:
            exists = eid in df_emp["รหัสพนักงาน"].astype(str).values
        if not exists:
            new = pd.DataFrame([[eid, enam, enick, epos]],
                columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"])
            df_emp = pd.concat([df_emp, new], ignore_index=True)
            df_emp.to_csv(EMP_FILE, index=False, encoding="utf-8")
            st.success("เพิ่มสำเร็จ ✅")
            st.rerun()
        else:
            st.warning("มีรหัสนี้อยู่แล้ว ⚠️")
    
    st.subheader("รายชื่อทั้งหมด")
    if df_emp.empty:
        st.info("ยังไม่มีข้อมูล")
    else:
        if "edit_idx" not in st.session_state:
            st.session_state.edit_idx = None
        for idx, row in df_emp.iterrows():
            eid_row = row["รหัสพนักงาน"]
            name_row = row["ชื่อพนักงาน"]
            nick_row = row["ชื่อเล่น"]
            pos_row = row["ตำแหน่ง"]
            if st.session_state.edit_idx == idx:
                with st.form(f"edit_form_{idx}"):
                    ceid = st.text_input("รหัสพนักงาน", value=eid_row, disabled=True)
                    cnam = st.text_input("ชื่อพนักงาน", value=name_row)
                    cnick = st.text_input("ชื่อเล่น", value=nick_row)
                    cpos = st.text_input("ตำแหน่ง", value=pos_row)
                    sv, cl = st.columns(2)
                    with sv:
                        if st.form_submit_button("💾 บันทึก"):
                            df_emp.at[idx, "ชื่อพนักงาน"] = cnam
                            df_emp.at[idx, "ชื่อเล่น"] = cnick
                            df_emp.at[idx, "ตำแหน่ง"] = cpos
                            df_emp.to_csv(EMP_FILE, index=False, encoding="utf-8")
                            st.session_state.edit_idx = None
                            st.rerun()
                    with cl:
                        if st.form_submit_button("❌ ยกเลิก"):
                            st.session_state.edit_idx = None
                            st.rerun()
            else:
                c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 2, 2, 1.2, 1.2])
                c1.write(eid_row)
                c2.write(name_row)
                c3.write(nick_row)
                c4.write(pos_row)
                if c5.button("✏️ แก้ไข", key=f"edit_btn_{idx}"):
                    st.session_state.edit_idx = idx
                    st.rerun()
                if c6.button("🗑️ ลบ", key=f"del_btn_{idx}"):
                    st.session_state[f"confirm_del_{idx}"] = True
                if f"confirm_del_{idx}" in st.session_state and st.session_state[f"confirm_del_{idx}"]:
                    st.warning(f"ต้องการลบ {name_row} ใช่หรือไม่?")
                    y, n = st.columns(2)
                    if y.button("✅ ยืนยันลบ", key=f"del_ok_{idx}"):
                        df_emp = df_emp.drop(idx).reset_index(drop=True)
                        df_emp.to_csv(EMP_FILE, index=False, encoding="utf-8")
                        del st.session_state[f"confirm_del_{idx}"]
                        st.success("ลบสำเร็จ ✅")
                        st.rerun()
                    if n.button("❌ ยกเลิก", key=f"del_no_{idx}"):
                        del st.session_state[f"confirm_del_{idx}"]

# ==========================================
# 2. บันทึกการเข้างาน/ลา
# ==========================================
elif menu == "บันทึกการเข้างาน/ลา":
    st.header("บันทึกการเข้างาน/ลา")
    df_emp = pd.read_csv(EMP_FILE, encoding="utf-8")
    if df_emp.empty:
        st.warning("กรุณาเพิ่มรายชื่อพนักงานก่อน ⚠️")
        st.stop()

    sel = st.selectbox("เลือกพนักงาน", [
        f"{r['รหัสพนักงาน']} | {r['ชื่อพนักงาน']} — {r['ตำแหน่ง']}"
        for _, r in df_emp.iterrows()
    ])
    eid = sel.split(" | ")[0]
    enam = sel.split(" | ")[1].split(" — ")[0]
    emp_row = df_emp[df_emp["รหัสพนักงาน"].astype(str) == eid].iloc[0]
    enick = emp_row["ชื่อเล่น"]
    epos = emp_row["ตำแหน่ง"]

    dt = st.date_input("วันที่", datetime.now())
    stt = st.selectbox("สถานะ", [
        "มาปกติ", "ลาป่วย", "ลากิจไม่รับเงิน", "WOP", "ขาดงาน", "ทำงานล่วงเวลา"
    ])

    df_rec = load_records()
    today_mask = (
        (df_rec["รหัสพนักงาน"].astype(str) == str(eid)) &
        (pd.to_datetime(df_rec["วันที่"], errors="coerce").dt.date == dt)
    )
    existing = df_rec.loc[today_mask]

    tin = tout = pin = pout = note = ""
    late_min = late_hr = ot15 = ot1 = hrs_work = 0.0
    if not existing.empty:
        rec = existing.iloc[0]
        tin = str(rec["เวลาเข้า"]) if pd.notna(rec["เวลาเข้า"]) and rec["เวลาเข้า"] != "-" else ""
        tout = str(rec["เวลาออก"]) if pd.notna(rec["เวลาออก"]) and rec["เวลาออก"] != "-" else ""
        pin = str(rec["รูปเช็คอิน"]) if pd.notna(rec["รูปเช็คอิน"]) and rec["รูปเช็คอิน"] != "-" else ""
        pout = str(rec["รูปเช็คเอาท์"]) if pd.notna(rec["รูปเช็คเอาท์"]) and rec["รูปเช็คเอาท์"] != "-" else ""
        note = str(rec["หมายเหตุ"]) if pd.notna(rec["หมายเหตุ"]) and rec["หมายเหตุ"] != "-" else ""
        st.info(f"📋 มีบันทึกของวันนี้แล้ว | เวลาเข้า: {tin or '—'} | เวลาออก: {tout or '—'}")

    def calc_times(tin_str, tout_str, work_date):
        t_in = parse_time_str(tin_str)
        t_out = parse_time_str(tout_str)
        if not t_in or not t_out:
            return 0, 0, 0, 0, 0.0
        ref_8am = t_in.replace(hour=8, minute=0, second=0)
        late_delta = (t_in - ref_8am).total_seconds() / 60 if t_in > ref_8am else 0
        late_hr_val = round(late_delta / 60, 2) if late_delta >= 60 else 0
        late_min_val = late_delta % 60 if late_delta > 0 else 0
        day_of_week = work_date.weekday()
        total_sec = (t_out - t_in).total_seconds() - 3600
        total_hr = round(total_sec / 3600, 2) if total_sec > 0 else 0
        std_hr = 8
        ot15_val = 0.0
        ot1_val = 0.0
        # จันทร์-เสาร์ = OT 1 และวันอาทิตย์ = OT 1.5
        if day_of_week == 6:
            ot15_val = total_hr
        elif total_hr > std_hr:
            ot1_val = total_hr - std_hr
        return late_min_val, late_hr_val, ot15_val, ot1_val, total_hr

    if stt in ["มาปกติ", "ทำงานล่วงเวลา"]:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🕘 เช็คอินเวลาเข้า")
            default_tin = datetime.strptime(tin, "%H:%M") if tin else datetime.strptime("08:00", "%H:%M")
            tin_new = st.time_input("เวลาเข้า", default_tin).strftime("%H:%M")
            st.write("แนบรูปเช็คอิน")
            fin = st.file_uploader("อัปโหลดรูปเช็คอิน", type=["jpg", "jpeg", "png"], key="pin_upload")
            pin_new = f"data:image/jpeg;base64,{base64.b64encode(fin.read()).decode()}" if fin else pin
            if st.button("✅ บันทึกเวลาเข้า", type="primary"):
                lmin, lhr, ot15, ot1, wh = calc_times(tin_new, tout, dt)
                if existing.empty:
                    new_rec = pd.DataFrame([[
                        eid, enam, enick, epos, dt, stt, tin_new, tout,
                        wh if tout else "-", "-", pin_new, pout, lmin, lhr, ot15, ot1
                    ]], columns=REC_COLUMNS)
                    df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
                else:
                    idx = existing.index[0]
                    df_rec.at[idx, "เวลาเข้า"] = tin_new
                    df_rec.at[idx, "รูปเช็คอิน"] = pin_new
                    if tout:
                        df_rec.at[idx, "จำนวนชั่วโมง"] = wh
                        df_rec.at[idx, "สายนาที"] = lmin
                        df_rec.at[idx, "สายชม"] = lhr
                        df_rec.at[idx, "OT 1.5(ชม.)"] = ot15
                        df_rec.at[idx, "OT 1(ชม.)"] = ot1
                df_rec.to_csv(REC_FILE, index=False, encoding="utf-8")
                st.success("บันทึกเวลาเข้าสำเร็จ ✅")
                st.rerun()
        with col2:
            st.subheader("🕕 เช็คเอาท์เวลาออก")
            default_tout = datetime.strptime(tout, "%H:%M") if tout else datetime.strptime("17:00", "%H:%M")
            tout_new = st.time_input("เวลาออก", default_tout).strftime("%H:%M")
            st.write("แนบรูปเช็คเอาท์")
            fout = st.file_uploader("อัปโหลดรูปเช็คเอาท์", type=["jpg", "jpeg", "png"], key="pout_upload")
            pout_new = f"data:image/jpeg;base64,{base64.b64encode(fout.read()).decode()}" if fout else pout
            if st.button("✅ บันทึกเวลาออก", type="primary"):
                lmin, lhr, ot15, ot1, wh = calc_times(tin or tin_new, tout_new, dt)
                if existing.empty:
                    new_rec = pd.DataFrame([[
                        eid, enam, enick, epos, dt, stt, tin or tin_new, tout_new,
                        wh if tin else "-", "-", pin, pout_new, lmin, lhr, ot15, ot1
                    ]], columns=REC_COLUMNS)
                    df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
                else:
                    idx = existing.index[0]
                    df_rec.at[idx, "เวลาออก"] = tout_new
                    df_rec.at[idx, "รูปเช็คเอาท์"] = pout_new
                    if tin:
                        df_rec.at[idx, "จำนวนชั่วโมง"] = wh
                        df_rec.at[idx, "สายนาที"] = lmin
                        df_rec.at[idx, "สายชม"] = lhr
                        df_rec.at[idx, "OT 1.5(ชม.)"] = ot15
                        df_rec.at[idx, "OT 1(ชม.)"] = ot1
                df_rec.to_csv(REC_FILE, index=False, encoding="utf-8")
                st.success("บันทึกเวลาออกสำเร็จ ✅")
                st.rerun()
    else:
        note = st.text_area("หมายเหตุ / เหตุผล", value=note)
        if st.button("✅ บันทึกข้อมูล", type="primary"):
            if existing.empty:
                new_rec = pd.DataFrame([[
                    eid, enam, enick, epos, dt, stt, "-", "-", "-", note, "-", "-", 0, 0, 0, 0
                ]], columns=REC_COLUMNS)
                df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
            else:
                idx = existing.index[0]
                df_rec.at[idx, "สถานะ"] = stt
                df_rec.at[idx, "หมายเหตุ"] = note
            df_rec.to_csv(REC_FILE, index=False, encoding="utf-8")
            st.success("บันทึกสำเร็จ ✅")
            st.rerun()

# ==========================================
# 3. หน้าสรุปภาพรวม
# ==========================================
elif menu == "หน้าสรุปภาพรวม":
    st.header("สรุปภาพรวม")
    df_rec = load_records()
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    summary = df_rec.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).agg({
        "สถานะ": [
            ("มาปกติ(วัน)", lambda x: (x=="มาปกติ").sum()),
            ("ลาป่วย(วัน)", lambda x: (x=="ลาป่วย").sum()),
            ("WOP(วัน)", lambda x: (x=="WOP").sum()),
            ("ลากิจไม่รับเงิน(ชม.)", lambda x: 0),
            ("ขาดงาน(วัน)", lambda x: (x=="ขาดงาน").sum()),
        ],
        "OT 1.5(ชม.)": "sum",
        "OT 1(ชม.)": "sum",
        "สายชม": "sum",
        "สายนาที": "sum"
    }).reset_index()
    summary.columns = [c[0] if isinstance(c, tuple) else c for c in summary.columns]
    st.dataframe(summary, use_container_width=True)

# ==========================================
# 4. รายงานรายชื่อ+วันทำงาน
# ==========================================
elif menu == "รายงานรายชื่อ+วันทำงาน":
    st.header("รายงานรายชื่อ+วันทำงาน")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("วันที่เริ่ม", datetime(2026, 9, 26))
    end_d = c2.date_input("วันที่สิ้นสุด", datetime(2026, 10, 25))
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")
    df_rec = load_records()
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    mask = (df_rec["วันที่"] >= pd.to_datetime(start_d)) & (df_rec["วันที่"] <= pd.to_datetime(end_d))
    df = df_rec.loc[mask].copy()
    if df.empty:
        st.info("ไม่มีข้อมูลในช่วงวันที่ที่เลือก")
        st.stop()
    st.subheader("สรุปรวม")
    sum_df = df.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).agg({
        "สถานะ": [
            ("มาปกติ(วัน)", lambda x: (x=="มาปกติ").sum()),
            ("ลาป่วย(วัน)", lambda x: (x=="ลาป่วย").sum()),
            ("WOP(วัน)", lambda x: (x=="WOP").sum()),
            ("ลากิจไม่รับเงิน(ชม.)", lambda x: 0),
            ("ขาดงาน(วัน)", lambda x: (x=="ขาดงาน").sum()),
        ],
        "OT 1.5(ชม.)": "sum",
        "OT 1(ชม.)": "sum",
        "สายชม": "sum",
        "สายนาที": "sum"
    }).reset_index()
    sum_df.columns = [c[0] if isinstance(c, tuple) else c for c in sum_df.columns]
    st.dataframe(sum_df, use_container_width=True)
    
    st.subheader("รายละเอียดรายวัน")
    day_df = df.copy()
    day_df["วันที่"] = day_df["วันที่"].dt.strftime("%d/%m/%y")
    day_df["รูปเช็คอิน"] = day_df["รูปเช็คอิน"].apply(img_cell)
    day_df["รูปเช็คเอาท์"] = day_df["รูปเช็คเอาท์"].apply(img_cell)
    day_cols = [
        "วันที่", "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
        "สถานะ", "เวลาเข้า", "เวลาออก", "จำนวนชั่วโมง",
        "OT 1.5(ชม.)", "OT 1(ชม.)", "สายชม", "สายนาที",
        "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]
    st.write(day_df[day_cols].to_html(escape=False, index=False), unsafe_allow_html=True)
    
    day_xl = day_df[day_cols].copy()
    day_xl["รูปเช็คอิน"] = day_xl["รูปเช็คอิน"].apply(lambda x: "มีรูป" if "<img" in str(x) else "-")
    day_xl["รูปเช็คเอาท์"] = day_xl["รูปเช็คเอาท์"].apply(lambda x: "มีรูป" if "<img" in str(x) else "-")
    out_file = f"รายงาน_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(out_file, engine="openpyxl") as w:
        sum_df.to_excel(w, sheet_name="สรุปรวม", index=False)
        day_xl.to_excel(w, sheet_name="รายละเอียด", index=False)
    with open(out_file, "rb") as f:
        st.download_button("📥 ดาวน์โหลดรายงาน Excel", f, out_file)

# ==========================================
# 5. หน้าสรุปส่ง HR
# ==========================================
elif menu == "หน้าสรุปส่ง HR":
    st.header("หน้าสรุปส่ง HR")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("วันที่เริ่มต้น", datetime(2026, 9, 26))
    end_d = c2.date_input("วันที่สิ้นสุด", datetime(2026, 10, 25))
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")
    df_rec = load_records()
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    mask = (df_rec["วันที่"] >= pd.to_datetime(start_d)) & (df_rec["วันที่"] <= pd.to_datetime(end_d))
    df = df_rec.loc[mask].copy()
    if df.empty:
        st.info("ไม่มีข้อมูลในช่วงนี้")
        st.stop()
    
    df["วันที่_str"] = df["วันที่"].dt.strftime("%d/%m/%y")
    df["ค่า"] = df["สถานะ"].apply(lambda x: 1 if x == "มาปกติ" else "")
    pivot = df.pivot_table(
        index=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"],
        columns="วันที่_str", values="ค่า", aggfunc="first", fill_value=""
    ).reset_index()
    
    emp_summary = df.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).apply(lambda g: pd.Series({
        "มาปกติ(วัน)": (g["สถานะ"] == "มาปกติ").sum(),
        "ลาป่วย(วัน)": (g["สถานะ"] == "ลาป่วย").sum(),
        "WOP(วัน)": (g["สถานะ"] == "WOP").sum(),
        "ลากิจไม่รับเงิน(ชม.)": 0,
        "ขาดงาน(วัน)": (g["สถานะ"] == "ขาดงาน").sum(),
        "OT 1.5(ชม.)": g["OT 1.5(ชม.)"].sum(),
        "OT 1(ชม.)": g["OT 1(ชม.)"].sum(),
        "มาสายรวม(ชม.)": g["สายชม"].sum(),
        "มาสายรวม(นาที)": g["สายนาที"].sum()
    })).reset_index()
    
    final_df = pd.merge(pivot, emp_summary,
                        on=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"])
    st.dataframe(final_df, use_container_width=True)
    
    fn = f"สรุปส่งHR_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(fn, engine="openpyxl") as w:
        final_df.to_excel(w, index=False, sheet_name="สรุปส่งHR")
    with open(fn, "rb") as f:
        st.download_button("📥 ดาวน์โหลดไฟล์ Excel", f, fn)

# ==========================================
# 6. สำรองข้อมูล
# ==========================================
elif menu == "📥 สำรองข้อมูล":
    st.header("สำรองข้อมูล")
    if os.path.exists(EMP_FILE):
        with open(EMP_FILE, "rb") as f:
            st.download_button("📥 ดาวน์โหลด: รายชื่อพนักงาน.csv", f, "รายชื่อพนักงาน.csv")
    if os.path.exists(REC_FILE):
        with open(REC_FILE, "rb") as f:
            st.download_button("📥 ดาวน์โหลด: ข้อมูลบันทึกเวลา.csv", f, "ข้อมูลบันทึกเวลา.csv")
    st.info("💡 คำแนะนำ: ดาวน์โหลดเก็บไว้ทุกครั้งก่อนแก้ไขโค้ด เพื่อป้องกันข้อมูลหาย")
    st.subheader("กู้คืนข้อมูล")
    up_emp = st.file_uploader("อัปโหลด: รายชื่อพนักงาน.csv", type="csv")
    up_rec = st.file_uploader("อัปโหลด: ข้อมูลบันทึกเวลา.csv", type="csv")
    if up_emp and st.button("✅ บันทึกรายชื่อพนักงาน"):
        try:
            pd.read_csv(up_emp, encoding="utf-8").to_csv(EMP_FILE, index=False, encoding="utf-8")
        except:
            pd.read_csv(up_emp, encoding="cp874").to_csv(EMP_FILE, index=False, encoding="utf-8")
        st.success("กู้คืนรายชื่อสำเร็จ ✅")
        st.rerun()
    if up_rec and st.button("✅ บันทึกข้อมูลบันทึกเวลา"):
        try:
            pd.read_csv(up_rec, encoding="utf-8").to_csv(REC_FILE, index=False, encoding="utf-8")
        except:
            pd.read_csv(up_rec, encoding="cp874").to_csv(REC_FILE, index=False, encoding="utf-8")
        st.success("กู้คืนข้อมูลสำเร็จ ✅")
        st.rerun()