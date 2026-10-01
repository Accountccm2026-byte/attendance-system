import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import base64
import re
import io
import zipfile

st.set_page_config(page_title="ระบบบันทึกเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน")

EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

REC_COLUMNS = [
    "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
    "วันที่", "สถานะ", "เวลาเข้า", "เวลาออก",
    "จำนวนชั่วโมง", "จำนวนวัน WOP", "หมายเหตุ", "เอกสารลาป่วย", "รูปเช็คอิน", "รูปเช็คเอาท์",
    "สายนาที", "สายชม", "OT 1.5(ชม.)", "OT 1(ชม.)"
]

def load_records():
    """Load records.csv and normalize dtypes so Streamlit/Pandas can safely edit rows."""
    if not os.path.exists(REC_FILE) or os.path.getsize(REC_FILE) == 0:
        return pd.DataFrame(columns=REC_COLUMNS)
    try:
        df = pd.read_csv(REC_FILE, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(REC_FILE, encoding="cp874")

    # Add missing columns from older CSV versions.
    for col in REC_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[REC_COLUMNS].copy()

    # Text/time/status/image columns must accept strings such as HH:MM and data:image...
    text_cols = [
        "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง", "วันที่", "สถานะ",
        "เวลาเข้า", "เวลาออก", "หมายเหตุ", "เอกสารลาป่วย", "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]
    for col in text_cols:
        df[col] = df[col].astype("string")

    # Numeric columns are kept numeric so summaries can use sum().
    numeric_cols = ["จำนวนชั่วโมง", "จำนวนวัน WOP", "สายนาที", "สายชม", "OT 1.5(ชม.)", "OT 1(ชม.)"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].replace({"-": pd.NA, "": pd.NA}), errors="coerce").astype("float64")

    # ลากิจไม่รับเงิน(ชม.) ไม่ถือเป็นการมาสายและไม่ควรมี OT
    # ล้างค่าความสาย/OT ที่อาจค้างมาจากข้อมูล CSV รุ่นเก่า
    leave_mask = df["สถานะ"].astype(str).eq("ลากิจไม่รับเงิน")
    for col in ["สายนาที", "สายชม", "OT 1.5(ชม.)", "OT 1(ชม.)"]:
        df.loc[leave_mask, col] = 0.0

    return df


if not os.path.exists(EMP_FILE) or os.path.getsize(EMP_FILE) == 0:
    pd.DataFrame(columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"]).to_csv(EMP_FILE, index=False, encoding="utf-8")
if not os.path.exists(REC_FILE) or os.path.getsize(REC_FILE) == 0:
    pd.DataFrame(columns=[
        "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
        "วันที่", "สถานะ", "เวลาเข้า", "เวลาออก",
        "จำนวนชั่วโมง", "จำนวนวัน WOP", "หมายเหตุ", "เอกสารลาป่วย", "รูปเช็คอิน", "รูปเช็คเอาท์",
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


def flatten_agg_col(c):
    """Flatten pandas groupby/agg column labels without creating duplicate names."""
    if isinstance(c, tuple):
        if len(c) >= 2:
            # Groupby index columns are typically (name, "").
            if c[1] in ("", "sum"):
                return c[0]
            return c[1]
        return c[0]
    return c



def get_payroll_period(base_date=None):
    """Return payroll cycle: 26th through 25th of the following month.
    Example: 26/09/2026 - 25/10/2026.
