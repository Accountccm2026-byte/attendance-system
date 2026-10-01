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
