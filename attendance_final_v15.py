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
    "จำนวนชั่วโมง", "หมายเหตุ", "รูปเช็คอิน", "รูปเช็คเอาท์",
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
        "เวลาเข้า", "เวลาออก", "หมายเหตุ", "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]
    for col in text_cols:
        df[col] = df[col].astype("string")

    # Numeric columns are kept numeric so summaries can use sum().
    numeric_cols = ["จำนวนชั่วโมง", "สายนาที", "สายชม", "OT 1.5(ชม.)", "OT 1(ชม.)"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].replace({"-": pd.NA, "": pd.NA}), errors="coerce")

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



def order_summary_columns(df):
    """บังคับลำดับคอลัมน์สรุปให้เหมือนกันทุกตาราง โดยลากิจไม่รับเงิน(ชม.) อยู่หลัง WOP(วัน)."""
    base = ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"]
    summary = [
        "มาปกติ(วัน)", "ลาป่วย(วัน)", "WOP(วัน)",
        "ลากิจไม่รับเงิน(ชม.)", "ขาดงาน(วัน)",
        "OT 1.5(ชม.)", "OT 1(ชม.)", "สายชม", "สายนาที",
        "มาสายรวม(ชม.)", "มาสายรวม(นาที)"
    ]
    preferred = [c for c in base + summary if c in df.columns]
    others = [c for c in df.columns if c not in preferred]
    return df[preferred + others]


def get_payroll_period(base_date=None):
    """Return payroll cycle: 26th through 25th of the following month.
    Example: 26/09/2026 - 25/10/2026.
    """
    if base_date is None:
        base_date = datetime.now().date()
    else:
        base_date = base_date if hasattr(base_date, "year") else datetime.now().date()

    if base_date.day >= 26:
        start_date = base_date.replace(day=26)
        if base_date.month == 12:
            end_date = base_date.replace(year=base_date.year + 1, month=1, day=25)
        else:
            end_date = base_date.replace(month=base_date.month + 1, day=25)
    else:
        if base_date.month == 1:
            start_date = base_date.replace(year=base_date.year - 1, month=12, day=26)
        else:
            start_date = base_date.replace(month=base_date.month - 1, day=26)
        end_date = base_date.replace(day=25)
    return start_date, end_date

def extract_leave_hours_from_note(note):
    """Recover hours from an old note such as 'ลากิจไม่รับเงิน 1 ชม.' when needed."""
    if note is None or pd.isna(note):
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*ชม\.?", str(note))
    return float(m.group(1)) if m else 0.0


def add_unpaid_leave_hours(df):
    """สร้างชั่วโมงลากิจไม่รับเงินเป็นคอลัมน์ตัวเลข โดยไม่แก้ค่าใน Series เดิมแบบเสี่ยง dtype error."""
    out = df.copy()
    hours = pd.to_numeric(out["จำนวนชั่วโมง"], errors="coerce").astype("float64")
    leave_mask = out["สถานะ"].astype(str).eq("ลากิจไม่รับเงิน")
    recover_mask = leave_mask & (hours.isna() | (hours <= 0))

    # สร้างค่าที่จะใช้สำหรับทุกแถวก่อน แล้วเลือกด้วย where/mask
    # เพื่อหลีกเลี่ยง LossySetitemError จาก pandas รุ่นใหม่
    recovered_all = pd.Series(0.0, index=out.index, dtype="float64")
    if "หมายเหตุ" in out.columns:
        recovered_all = out["หมายเหตุ"].apply(extract_leave_hours_from_note)
        recovered_all = pd.to_numeric(recovered_all, errors="coerce").fillna(0.0).astype("float64")

    # ถ้ามีจำนวนชั่วโมงจริง > 0 ให้ใช้ค่านั้น; ถ้าไม่มี ให้ใช้ค่าจากหมายเหตุ
    final_hours = hours.where(~recover_mask, recovered_all)
    out["_ลากิจไม่รับเงินชม"] = final_hours.fillna(0.0).where(leave_mask, 0.0).astype("float64")
    return out


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
    leave_hours_existing = 0.0
    late_min = late_hr = ot15 = ot1 = hrs_work = 0.0
    if not existing.empty:
        rec = existing.iloc[0]
        tin = str(rec["เวลาเข้า"]) if pd.notna(rec["เวลาเข้า"]) and rec["เวลาเข้า"] != "-" else ""
        tout = str(rec["เวลาออก"]) if pd.notna(rec["เวลาออก"]) and rec["เวลาออก"] != "-" else ""
        pin = str(rec["รูปเช็คอิน"]) if pd.notna(rec["รูปเช็คอิน"]) and rec["รูปเช็คอิน"] != "-" else ""
        pout = str(rec["รูปเช็คเอาท์"]) if pd.notna(rec["รูปเช็คเอาท์"]) and rec["รูปเช็คเอาท์"] != "-" else ""
        note = str(rec["หมายเหตุ"]) if pd.notna(rec["หมายเหตุ"]) and rec["หมายเหตุ"] != "-" else ""
        leave_hours_existing = (
            float(rec["จำนวนชั่วโมง"])
            if pd.notna(rec["จำนวนชั่วโมง"])
            else extract_leave_hours_from_note(note)
        )
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
                        wh if tout else None, "-", pin_new, pout, lmin, lhr, ot15, ot1
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
                        wh if tin else None, "-", pin, pout_new, lmin, lhr, ot15, ot1
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
        if stt == "ลากิจไม่รับเงิน":
            leave_hours = st.number_input(
                "จำนวนชั่วโมงลากิจไม่รับเงิน",
                min_value=0.0,
                max_value=24.0,
                value=float(leave_hours_existing),
                step=0.5,
                format="%.2f",
                key=f"leave_hours_{eid}_{dt}"
            )
            st.caption("💡 ตัวอย่าง: ลากิจไม่รับเงิน 1 ชั่วโมง ให้กรอก 1.00")
        else:
            leave_hours = 0.0

        note = st.text_area("หมายเหตุ / เหตุผล", value=note)
        if st.button("✅ บันทึกข้อมูล", type="primary"):
            if existing.empty:
                new_rec = pd.DataFrame([[
                    eid, enam, enick, epos, dt, stt, "-", "-",
                    leave_hours if stt == "ลากิจไม่รับเงิน" else None,
                    note, "-", "-", 0, 0, 0, 0
                ]], columns=REC_COLUMNS)
                df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
            else:
                idx = existing.index[0]
                df_rec.at[idx, "สถานะ"] = stt
                df_rec.at[idx, "หมายเหตุ"] = note
                df_rec.at[idx, "จำนวนชั่วโมง"] = leave_hours if stt == "ลากิจไม่รับเงิน" else None
                df_rec.at[idx, "เวลาเข้า"] = "-"
                df_rec.at[idx, "เวลาออก"] = "-"
                df_rec.at[idx, "OT 1.5(ชม.)"] = 0.0
                df_rec.at[idx, "OT 1(ชม.)"] = 0.0
                df_rec.at[idx, "สายชม"] = 0.0
                df_rec.at[idx, "สายนาที"] = 0.0
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
    df_rec = add_unpaid_leave_hours(df_rec)
    summary = df_rec.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).agg({
        "สถานะ": [
            # นับทั้ง "มาปกติ" และ "ทำงานล่วงเวลา" เป็นวันทำงาน
            ("มาปกติ(วัน)", lambda x: x.isin(["มาปกติ", "ทำงานล่วงเวลา"]).sum()),
            ("ลาป่วย(วัน)", lambda x: (x=="ลาป่วย").sum()),
            ("WOP(วัน)", lambda x: (x=="WOP").sum()),
            ("ขาดงาน(วัน)", lambda x: (x=="ขาดงาน").sum()),
        ],
        "OT 1.5(ชม.)": "sum",
        "OT 1(ชม.)": "sum",
        "สายชม": "sum",
        "สายนาที": "sum",
        "_ลากิจไม่รับเงินชม": "sum"
    }).reset_index()
    summary.columns = [flatten_agg_col(c) for c in summary.columns]
    if "_ลากิจไม่รับเงินชม" in summary.columns:
        summary = summary.rename(columns={"_ลากิจไม่รับเงินชม": "ลากิจไม่รับเงิน(ชม.)"})
    summary = summary.loc[:, ~summary.columns.duplicated()]
    summary = order_summary_columns(summary)
    st.dataframe(summary, use_container_width=True)

# ==========================================
# 4. รายงานรายชื่อ+วันทำงาน
# ==========================================
elif menu == "รายงานรายชื่อ+วันทำงาน":
    st.header("รายงานรายชื่อ+วันทำงาน")
    default_start, default_end = get_payroll_period()
    st.info("📅 รอบเงินเดือนอัตโนมัติ: วันที่ 26 ถึงวันที่ 25 ของเดือนถัดไป (สามารถเปลี่ยนวันที่เองได้)")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("วันที่เริ่ม", default_start)
    end_d = c2.date_input("วันที่สิ้นสุด", default_end)
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")
    if start_d > end_d:
        st.error("วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด")
        st.stop()
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
    df = add_unpaid_leave_hours(df)
    sum_df = df.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).agg({
        "สถานะ": [
            # นับทั้ง "มาปกติ" และ "ทำงานล่วงเวลา" เป็นวันทำงาน
            ("มาปกติ(วัน)", lambda x: x.isin(["มาปกติ", "ทำงานล่วงเวลา"]).sum()),
            ("ลาป่วย(วัน)", lambda x: (x=="ลาป่วย").sum()),
            ("WOP(วัน)", lambda x: (x=="WOP").sum()),
            ("ขาดงาน(วัน)", lambda x: (x=="ขาดงาน").sum()),
        ],
        "OT 1.5(ชม.)": "sum",
        "OT 1(ชม.)": "sum",
        "สายชม": "sum",
        "สายนาที": "sum",
        "_ลากิจไม่รับเงินชม": "sum"
    }).reset_index()
    sum_df.columns = [flatten_agg_col(c) for c in sum_df.columns]
    if "_ลากิจไม่รับเงินชม" in sum_df.columns:
        sum_df = sum_df.rename(columns={"_ลากิจไม่รับเงินชม": "ลากิจไม่รับเงิน(ชม.)"})
    sum_df = sum_df.loc[:, ~sum_df.columns.duplicated()]
    sum_df = order_summary_columns(sum_df)
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

    # ------------------------------
    # จัดการข้อมูลรายวัน: ลบรายการที่ผิด
    # ------------------------------
    st.subheader("🗑️ จัดการข้อมูลรายวัน")
    st.caption("หากเวลา/สถานะ/รูปเช็คอิน-เช็คเอาท์ผิด สามารถลบรายการนั้นแล้วกลับไปบันทึกใหม่ได้")

    # ใช้ index เดิมของ df_rec เพื่อให้ลบถูกแถวใน records.csv
    for row_idx, row in df.iterrows():
        with st.container(border=True):
            r1, r2, r3, r4, r5, r6 = st.columns([1.1, 1.4, 2.0, 1.5, 2.0, 1.0])
            r1.write(row["วันที่"].strftime("%d/%m/%y") if hasattr(row["วันที่"], "strftime") else str(row["วันที่"]))
            r2.write(str(row["รหัสพนักงาน"]))
            r3.write(str(row["ชื่อพนักงาน"]))
            r4.write(str(row["สถานะ"]))
            r5.write(f"เข้า {row['เวลาเข้า']} | ออก {row['เวลาออก']}")
            if r6.button("🗑️ ลบ", key=f"delete_record_{row_idx}"):
                st.session_state["confirm_delete_record"] = int(row_idx)
                st.rerun()

            if st.session_state.get("confirm_delete_record") == int(row_idx):
                st.warning("⚠️ ต้องการลบข้อมูลรายการนี้ใช่หรือไม่? การลบจะนำข้อมูลออกจาก records.csv และไม่สามารถกู้คืนจากในระบบได้ เว้นแต่มีไฟล์สำรอง")
                cy, cn = st.columns(2)
                with cy:
                    if st.button("✅ ยืนยันลบ", key=f"confirm_delete_{row_idx}", type="primary"):
                        df_rec = load_records()
                        if int(row_idx) in df_rec.index:
                            df_rec = df_rec.drop(index=int(row_idx))
                            df_rec.to_csv(REC_FILE, index=False, encoding="utf-8")
                            st.session_state.pop("confirm_delete_record", None)
                            st.success("ลบข้อมูลเรียบร้อยแล้ว ✅")
                            st.rerun()
                        else:
                            st.session_state.pop("confirm_delete_record", None)
                            st.warning("ไม่พบข้อมูลรายการนี้ อาจถูกลบไปแล้ว")
                            st.rerun()
                with cn:
                    if st.button("❌ ยกเลิก", key=f"cancel_delete_{row_idx}"):
                        st.session_state.pop("confirm_delete_record", None)
                        st.rerun()

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
    default_start, default_end = get_payroll_period()
    st.info("📅 ค่าเริ่มต้นเป็นรอบเงินเดือน 26–25 และ HR สามารถเลือกวันที่เริ่ม/สิ้นสุดเองได้")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("วันที่เริ่มต้น", default_start)
    end_d = c2.date_input("วันที่สิ้นสุด", default_end)
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")
    if start_d > end_d:
        st.error("วันที่เริ่มต้องไม่เกินวันที่สิ้นสุด")
        st.stop()
    df_rec = load_records()
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    mask = (df_rec["วันที่"] >= pd.to_datetime(start_d)) & (df_rec["วันที่"] <= pd.to_datetime(end_d))
    df = df_rec.loc[mask].copy()
    df = add_unpaid_leave_hours(df)
    if df.empty:
        st.info("ไม่มีข้อมูลในช่วงนี้")
        st.stop()
    
    df["วันที่_str"] = df["วันที่"].dt.strftime("%d/%m/%y")
    df["ค่า"] = df["สถานะ"].apply(lambda x: 1 if x in ["มาปกติ", "ทำงานล่วงเวลา"] else "")
    pivot = df.pivot_table(
        index=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"],
        columns="วันที่_str", values="ค่า", aggfunc="first", fill_value=""
    ).reset_index()
    
    emp_summary = df.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).apply(lambda g: pd.Series({
        "มาปกติ(วัน)": g["สถานะ"].isin(["มาปกติ", "ทำงานล่วงเวลา"]).sum(),
        "ลาป่วย(วัน)": (g["สถานะ"] == "ลาป่วย").sum(),
        "WOP(วัน)": (g["สถานะ"] == "WOP").sum(),
        "ลากิจไม่รับเงิน(ชม.)": g["_ลากิจไม่รับเงินชม"].sum(),
        "ขาดงาน(วัน)": (g["สถานะ"] == "ขาดงาน").sum(),
        "OT 1.5(ชม.)": g["OT 1.5(ชม.)"].sum(),
        "OT 1(ชม.)": g["OT 1(ชม.)"].sum(),
        "มาสายรวม(ชม.)": g["สายชม"].sum(),
        "มาสายรวม(นาที)": g["สายนาที"].sum()
    })).reset_index()
    
    final_df = pd.merge(pivot, emp_summary,
                        on=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"])
    final_df = order_summary_columns(final_df)
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
    st.info("💡 CSV เก็บข้อมูลเป็นข้อความ จึงไม่สามารถแสดงรูปภาพได้โดยตรง หากต้องการสำรองรูปเช็คอิน/เช็คเอาท์ ให้ใช้ ZIP หรือ Excel ด้านล่าง")

    # รายชื่อพนักงาน CSV (ภาษาไทยรองรับ Excel)
    if os.path.exists(EMP_FILE):
        emp_download = pd.read_csv(EMP_FILE, encoding="utf-8")
        emp_csv = emp_download.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 ดาวน์โหลด: รายชื่อพนักงาน.csv",
            data=emp_csv,
            file_name="รายชื่อพนักงาน.csv",
            mime="text/csv"
        )

    # ข้อมูลบันทึกเวลา CSV: เก็บข้อมูลข้อความ/รูปแบบ data URI แต่ Excel จะเห็นเป็นข้อความยาว
    if os.path.exists(REC_FILE):
        rec_download = load_records()
        rec_csv = rec_download.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 ดาวน์โหลด: ข้อมูลบันทึกเวลา.csv (ข้อมูลข้อความ)",
            data=rec_csv,
            file_name="ข้อมูลบันทึกเวลา.csv",
            mime="text/csv"
        )

        # สำรองพร้อมรูปเป็น ZIP: CSV + ไฟล์รูปจริง
        zip_buf = io.BytesIO()
        image_count = 0
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("ข้อมูลบันทึกเวลา.csv", rec_csv)
            for i, row in rec_download.reset_index(drop=True).iterrows():
                for field, prefix in [("รูปเช็คอิน", "เช็คอิน"), ("รูปเช็คเอาท์", "เช็คเอาท์")]:
                    val = row.get(field, "")
                    if pd.isna(val):
                        continue
                    val = str(val)
                    if not val.startswith("data:image"):
                        continue
                    try:
                        header, b64 = val.split(",", 1)
                        ext = "jpg"
                        if "png" in header:
                            ext = "png"
                        elif "webp" in header:
                            ext = "webp"
                        elif "jpeg" in header or "jpg" in header:
                            ext = "jpg"
                        eid = str(row.get("รหัสพนักงาน", ""))
                        d = str(row.get("วันที่", "")).replace("/", "-").replace(" ", "_")
                        filename = f"รูป/{i+1}_{eid}_{d}_{prefix}.{ext}"
                        zf.writestr(filename, base64.b64decode(b64))
                        image_count += 1
                    except Exception:
                        pass
        zip_buf.seek(0)
        st.download_button(
            f"🗂️ ดาวน์โหลดสำรองข้อมูลพร้อมรูป (ZIP) — พบรูป {image_count} รูป",
            data=zip_buf.getvalue(),
            file_name="สำรองข้อมูล_พร้อมรูป.zip",
            mime="application/zip"
        )

        # Excel สำรองพร้อมรูปฝังในเซลล์
        try:
            from openpyxl import Workbook
            from openpyxl.drawing.image import Image as XLImage
            from openpyxl.utils import get_column_letter

            wb = Workbook()
            ws = wb.active
            ws.title = "ข้อมูลบันทึกเวลา"
            cols = list(rec_download.columns)
            for c, col in enumerate(cols, 1):
                ws.cell(1, c, col)

            image_cols = {"รูปเช็คอิน": 11, "รูปเช็คเอาท์": 12}
            for r_idx, (_, row) in enumerate(rec_download.iterrows(), 2):
                for c_idx, col in enumerate(cols, 1):
                    val = row[col]
                    if col in image_cols and isinstance(val, str) and val.startswith("data:image"):
                        try:
                            _, b64 = val.split(",", 1)
                            img_bytes = base64.b64decode(b64)
                            img = XLImage(io.BytesIO(img_bytes))
                            img.width = 90
                            img.height = 70
                            ws.add_image(img, f"{get_column_letter(c_idx)}{r_idx}")
                            ws.row_dimensions[r_idx].height = 55
                            ws.cell(r_idx, c_idx, "มีรูป")
                        except Exception:
                            ws.cell(r_idx, c_idx, "มีรูป (เปิดไม่ได้)")
                    else:
                        if pd.isna(val):
                            val = ""
                        ws.cell(r_idx, c_idx, str(val))

            for c, col in enumerate(cols, 1):
                ws.column_dimensions[get_column_letter(c)].width = 18
            ws.column_dimensions["K"].width = 16
            ws.column_dimensions["L"].width = 16
            excel_buf = io.BytesIO()
            wb.save(excel_buf)
            excel_buf.seek(0)
            st.download_button(
                "📊 ดาวน์โหลด Excel พร้อมรูปภาพ",
                data=excel_buf.getvalue(),
                file_name="สำรองข้อมูล_พร้อมรูป.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.warning(f"ไม่สามารถสร้าง Excel พร้อมรูปได้: {e}")

    st.info("💡 แนะนำ: ถ้าต้องการเก็บรูปไว้ด้วย ให้ดาวน์โหลด ZIP หรือ Excel พร้อมรูป ไม่ควรใช้ CSV เป็นไฟล์สำรองรูปภาพ")
    st.subheader("กู้คืนข้อมูล")
    up_emp = st.file_uploader("อัปโหลด: รายชื่อพนักงาน.csv", type="csv")
    up_rec = st.file_uploader("อัปโหลด: ข้อมูลบันทึกเวลา.csv", type="csv")
    if up_emp and st.button("✅ บันทึกรายชื่อพนักงาน"):
        try:
            pd.read_csv(up_emp, encoding="utf-8-sig").to_csv(EMP_FILE, index=False, encoding="utf-8")
        except:
            pd.read_csv(up_emp, encoding="cp874").to_csv(EMP_FILE, index=False, encoding="utf-8")
        st.success("กู้คืนรายชื่อสำเร็จ ✅")
        st.rerun()
    if up_rec and st.button("✅ บันทึกข้อมูลบันทึกเวลา"):
        try:
            pd.read_csv(up_rec, encoding="utf-8-sig").to_csv(REC_FILE, index=False, encoding="utf-8")
        except:
            pd.read_csv(up_rec, encoding="cp874").to_csv(REC_FILE, index=False, encoding="utf-8")
        st.success("กู้คืนข้อมูลสำเร็จ ✅")
        st.rerun()

