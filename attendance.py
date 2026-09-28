import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --------------------------
# ตั้งค่าหน้าเว็บ
# --------------------------
st.set_page_config(page_title="ระบบลงเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน - รอบ 26/09/69 - 25/10/69")

# --------------------------
# กำหนดไฟล์เก็บข้อมูล
# --------------------------
EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

# --------------------------
# ฟังก์ชันจัดการข้อมูล
# --------------------------
def init_data():
    if not os.path.exists(EMP_FILE):
        pd.DataFrame(columns=["emp_id", "name", "nickname", "position"]).to_csv(EMP_FILE, index=False)
    if not os.path.exists(REC_FILE):
        pd.DataFrame(columns=[
            "emp_id", "date", "status",
            "time_in", "time_out",
            "late_min", "late_hr",
            "normal_hr", "ot15", "ot1",
            "leave_hrs", "leave_type", "note"
        ]).to_csv(REC_FILE, index=False)

def load_emp():
    return pd.read_csv(EMP_FILE)

def load_rec():
    return pd.read_csv(REC_FILE, parse_dates=["date"])

def save_emp(df):
    df.to_csv(EMP_FILE, index=False)

def save_rec(df):
    df.to_csv(REC_FILE, index=False)

init_data()

# --------------------------
# เมนูหลัก
# --------------------------
menu = [
    "👥 จัดการรายชื่อพนักงาน",
    "✅ บันทึกการเข้างาน/ลา",
    "📊 หน้าสรุปภาพรวม",
    "📋 รายงานรายชื่อ+วันทำงาน",
    "📤 หน้าสรุปส่ง HR"
]
choice = st.sidebar.selectbox("เมนูหลัก", menu)

# ==================================================
# 1. 👥 จัดการรายชื่อพนักงาน
# ==================================================
if choice == "👥 จัดการรายชื่อพนักงาน":
    st.header("จัดการรายชื่อพนักงาน")
    df_emp = load_emp()

    with st.form("add_emp"):
        c1, c2, c3, c4 = st.columns(4)
        new_id = c1.text_input("รหัสพนักงาน")
        new_name = c2.text_input("ชื่อพนักงาน")
        new_nick = c3.text_input("ชื่อเล่น")
        new_pos = c4.text_input("ตำแหน่ง")
        if st.form_submit_button("เพิ่มพนักงาน"):
            if new_id.strip() == "":
                st.error("กรุณากรอกรหัสพนักงาน")
            elif new_id in df_emp["emp_id"].astype(str).values:
                st.error("รหัสพนักงานซ้ำ กรุณาใช้รหัสอื่น")
            else:
                df_emp.loc[len(df_emp)] = [new_id, new_name, new_nick, new_pos]
                save_emp(df_emp)
                st.success("เพิ่มสำเร็จ")
                st.rerun()

    st.subheader("รายชื่อทั้งหมด")
    if len(df_emp) == 0:
        st.info("ยังไม่มีข้อมูลพนักงาน")
    else:
        st.dataframe(df_emp, use_container_width=True)
        for idx, row in df_emp.iterrows():
            if st.button(f"ลบ {row['emp_id']} - {row['name']}", key=f"del_{idx}"):
                df_rec = load_rec()
                if row["emp_id"] in df_rec["emp_id"].values:
                    st.error("ไม่สามารถลบได้ มีประวัติการทำงานแล้ว")
                else:
                    df_emp.drop(idx, inplace=True)
                    save_emp(df_emp)
                    st.rerun()

# ==================================================
# 2. ✅ บันทึกการเข้างาน/ลา
# ==================================================
elif choice == "✅ บันทึกการเข้างาน/ลา":
    st.header("บันทึกการเข้างาน/ลา")
    df_emp = load_emp()
    if len(df_emp) == 0:
        st.warning("กรุณาเพิ่มรายชื่อพนักงานก่อน")
        st.stop()

    emp_sel = st.selectbox(
        "เลือกพนักงาน",
        [f"{r.emp_id} | {r.name} ({r.nickname}) — {r.position}" for _, r in df_emp.iterrows()]
    )
    emp_id = emp_sel.split(" | ")[0]
    emp_name = emp_sel.split(" | ")[1].split(" (")[0]
    emp_nick = emp_sel.split("(")[1].split(")")[0]
    emp_pos = emp_sel.split(" — ")[1]

    sel_date = st.date_input("วันที่")
    status = st.selectbox("สถานะ", [
        "✅ มาปกติ",
        "🤒 ลาป่วย",
        "⏸️ WOP",
        "📝 ลากิจไม่รับเงิน",
        "⚪ ขาดงาน"
    ])

    df_rec = load_rec()
    exists = df_rec[(df_rec["emp_id"] == emp_id) & (df_rec["date"] == pd.Timestamp(sel_date))]
    if len(exists) > 0:
        st.warning("มีบันทึกสำหรับพนักงาน+วันที่นี้แล้ว จะบันทึกทับข้อมูลเดิม")

    time_in = time_out = None
    late_min = late_hr = norm_hr = ot15 = ot1 = leave_hrs = 0.0
    note = ""

    if status == "✅ มาปกติ":
        c1, c2 = st.columns(2)
        t_in = c1.time_input("เวลาเข้า", value=datetime.strptime("08:00", "%H:%M").time())
        t_out = c2.time_input("เวลาออก", value=datetime.strptime("17:00", "%H:%M").time())
        time_in = t_in.strftime("%H:%M")
        time_out = t_out.strftime("%H:%M")
        
    # --- เพิ่มส่วนแนบรูป ---
    st.subheader("แนบรูปภาพ")
    pic_in = st.file_uploader("แนบรูปเช็คอิน", type=["jpg", "jpeg", "png"])
    pic_out = st.file_uploader("แนบรูปเช็คเอาท์", type=["jpg", "jpeg", "png"])
    
    if pic_in is not None:
        st.image(pic_in, caption="รูปเช็คอิน", width=200)
    if pic_out is not None:
        st.image(pic_out, caption="รูปเช็คเอาท์", width=200)
    # --- จบส่วนแนบรูป ---
        
        # คำนวณมาสาย
        ref_in = datetime.strptime("08:00", "%H:%M")
        act_in = datetime.strptime(time_in, "%H:%M")
        if act_in > ref_in:
            late_min = (act_in - ref_in).total_seconds() // 60
        late_hr = round(late_min / 60, 2) if late_min >= 60 else 0.0

        # ตรวจวันอาทิตย์
        is_sun = pd.Timestamp(sel_date).weekday() == 6

        # คำนวณชม.ทำงาน
        t1 = datetime.strptime(time_in, "%H:%M")
        t2 = datetime.strptime(time_out, "%H:%M")
        total = (t2 - t1).total_seconds() / 3600 - 1  # หักพัก 1 ชม.
        total = max(total, 0)

        if is_sun:
            ot1 = round(total, 2)
            norm_hr = 0.0
            ot15 = 0.0
        else:
            norm_hr = min(total, 8.0)
            ot15 = round(max(total - 8.0, 0), 2)
            ot1 = 0.0

        if late_min > 0:
            note = f"มาสาย {int(late_min)} นาที"
            if late_hr >= 1:
                note += f" ({late_hr} ชั่วโมง) — หากต้องการนับเป็นลากิจ ให้เปลี่ยนสถานะ"
            st.info(f"⚠️ {note}")

    elif status == "📝 ลากิจไม่รับเงิน":
        leave_hrs = st.number_input("จำนวนชั่วโมง", min_value=0.0, max_value=8.0, step=0.5)
        note = st.text_input("เหตุผล")

    elif status in ["🤒 ลาป่วย", "⏸️ WOP", "⚪ ขาดงาน"]:
        note = st.text_input("เหตุผล")

    if st.button("บันทึกข้อมูล", type="primary"):
        # ลบเก่าถ้ามี
        df_rec = df_rec[~((df_rec["emp_id"] == emp_id) & (df_rec["date"] == pd.Timestamp(sel_date)))]
        # เพิ่มใหม่
        df_rec.loc[len(df_rec)] = [
            emp_id, pd.Timestamp(sel_date), status,
            time_in, time_out,
            int(late_min), late_hr,
            norm_hr, ot15, ot1,
            leave_hrs, status, note
        ]
        save_rec(df_rec)
        st.success("บันทึกสำเร็จ")

# ==================================================
# 3. 📊 หน้าสรุปภาพรวม
# ==================================================
elif choice == "📊 หน้าสรุปภาพรวม":
    st.header("สรุปภาพรวม")
    df_emp = load_emp()
    df_rec = load_rec()
    start_date = pd.Timestamp("2026-09-26")
    end_date = pd.Timestamp("2026-10-25")
    df_rec = df_rec[(df_rec["date"] >= start_date) & (df_rec["date"] <= end_date)]

    if len(df_emp) == 0:
        st.info("ยังไม่มีข้อมูล")
        st.stop()

    summary = []
    for _, emp in df_emp.iterrows():
        r = df_rec[df_rec["emp_id"] == emp["emp_id"]]
        summary.append({
            "รหัสพนักงาน": emp["emp_id"],
            "ชื่อพนักงาน": emp["name"],
            "ชื่อเล่น": emp["nickname"],
            "ตำแหน่ง": emp["position"],
            "มาปกติ (วัน)": len(r[r["status"] == "✅ มาปกติ"]),
            "ลาป่วย (วัน)": len(r[r["status"] == "🤒 ลาป่วย"]),
            "WOP (วัน)": len(r[r["status"] == "⏸️ WOP"]),
            "ลากิจไม่รับเงิน (ชั่วโมง)": round(r["leave_hrs"].sum(), 2),
            "ขาดงาน (วัน)": len(r[r["status"] == "⚪ ขาดงาน"]),
            "OT 1.5 (ชั่วโมง)": round(r["ot15"].sum(), 2),
            "OT 1 (ชั่วโมง)": round(r["ot1"].sum(), 2),
            "มาสายรวม (ชั่วโมง)": round(r["late_hr"].sum(), 2),
            "มาสายรวม (นาที)": int(r["late_min"].sum())
        })
    df_sum = pd.DataFrame(summary)
    st.dataframe(df_sum, use_container_width=True)

# ==================================================
# 4. 📋 รายงานรายชื่อ+วันทำงาน
# ==================================================
elif choice == "📋 รายงานรายชื่อ+วันทำงาน":
    st.header("รายงานรายชื่อ+วันทำงาน")
    df_emp = load_emp()
    df_rec = load_rec()
    start_date = pd.Timestamp("2026-09-26")
    end_date = pd.Timestamp("2026-10-25")
    df_rec = df_rec[(df_rec["date"] >= start_date) & (df_rec["date"] <= end_date)]

    # สรุปรวม
    summary = []
    for _, emp in df_emp.iterrows():
        r = df_rec[df_rec["emp_id"] == emp["emp_id"]]
        summary.append({
            "รหัสพนักงาน": emp["emp_id"],
            "ชื่อพนักงาน": emp["name"],
            "ชื่อเล่น": emp["nickname"],
            "ตำแหน่ง": emp["position"],
            "มาปกติ (วัน)": len(r[r["status"] == "✅ มาปกติ"]),
            "ลาป่วย (วัน)": len(r[r["status"] == "🤒 ลาป่วย"]),
            "WOP (วัน)": len(r[r["status"] == "⏸️ WOP"]),
            "ลากิจไม่รับเงิน (ชั่วโมง)": round(r["leave_hrs"].sum(), 2),
            "ขาดงาน (วัน)": len(r[r["status"] == "⚪ ขาดงาน"]),
            "OT 1.5 (ชั่วโมง)": round(r["ot15"].sum(), 2),
            "OT 1 (ชั่วโมง)": round(r["ot1"].sum(), 2),
            "มาสายรวม (ชั่วโมง)": round(r["late_hr"].sum(), 2),
            "มาสายรวม (นาที)": int(r["late_min"].sum())
        })
    st.subheader("สรุปรวม")
    st.dataframe(pd.DataFrame(summary), use_container_width=True)

    # รายวัน
    st.subheader("รายละเอียดรายวัน")
    detail = []
    for _, r in df_rec.iterrows():
        emp = df_emp[df_emp["emp_id"] == r["emp_id"]].iloc[0]
        detail.append({
            "วันที่": r["date"].strftime("%d/%m/%y"),
            "รหัสพนักงาน": r["emp_id"],
            "ชื่อพนักงาน": emp["name"],
            "ชื่อเล่น": emp["nickname"],
            "ตำแหน่ง": emp["position"],
            "สถานะ": r["status"],
            "เวลาเข้า": r["time_in"],
            "เวลาออก": r["time_out"],
            "ชม.ปกติ": r["normal_hr"],
            "OT 1.5 (ชั่วโมง)": r["ot15"],
            "OT 1 (ชั่วโมง)": r["ot1"],
            "มาสาย (ชั่วโมง)": r["late_hr"],
            "มาสาย (นาที)": int(r["late_min"]),
            "หมายเหตุ": r["note"]
        })
    st.dataframe(pd.DataFrame(detail), use_container_width=True)

# ==================================================
# 5. 📤 หน้าสรุปส่ง HR
# ==================================================
elif choice == "📤 หน้าสรุปส่ง HR":
    st.header("หน้าสรุปส่ง HR")
    df_emp = load_emp()
    df_rec = load_rec()

    c1, c2 = st.columns(2)
    start_sel = c1.date_input("วันที่เริ่มต้น", value=datetime(2026, 9, 26))
    end_sel = c2.date_input("วันที่สิ้นสุด", value=datetime(2026, 10, 25))
    start_dt = pd.Timestamp(start_sel)
    end_dt = pd.Timestamp(end_sel)

    df_rec = df_rec[(df_rec["date"] >= start_dt) & (df_rec["date"] <= end_dt)]

    # สร้างคอลัมน์วันที่
    date_range = pd.date_range(start=start_dt, end=end_dt)
    date_cols = [d.strftime("%d/%m/%y") for d in date_range]

    hr_data = []
    for _, emp in df_emp.iterrows():
        r = df_rec[df_rec["emp_id"] == emp["emp_id"]]
        row = {
            "รหัสพนักงาน": emp["emp_id"],
            "ชื่อพนักงาน": emp["name"],
            "ชื่อเล่น": emp["nickname"],
            "ตำแหน่ง": emp["position"]
        }
        # ใส่ 1 ตรงวันที่มาปกติ
        for d in date_range:
            d_str = d.strftime("%d/%m/%y")
            day_rec = r[r["date"] == d]
            row[d_str] = 1 if (len(day_rec) > 0 and day_rec.iloc[0]["status"] == "✅ มาปกติ") else ""
        # สรุปท้ายแถว
        row.update({
            "มาปกติ (วัน)": len(r[r["status"] == "✅ มาปกติ"]),
            "ลาป่วย (วัน)": len(r[r["status"] == "🤒 ลาป่วย"]),
            "WOP (วัน)": len(r[r["status"] == "⏸️ WOP"]),
            "ลากิจไม่รับเงิน (ชั่วโมง)": round(r["leave_hrs"].sum(), 2),
            "ขาดงาน (วัน)": len(r[r["status"] == "⚪ ขาดงาน"]),
            "OT 1.5 (ชั่วโมง)": round(r["ot15"].sum(), 2),
            "OT 1 (ชั่วโมง)": round(r["ot1"].sum(), 2),
            "มาสายรวม (ชั่วโมง)": round(r["late_hr"].sum(), 2),
            "มาสายรวม (นาที)": int(r["late_min"].sum())
        })
        hr_data.append(row)

    df_hr = pd.DataFrame(hr_data)
    st.dataframe(df_hr, use_container_width=True)

    # ส่งออก Excel
    from io import BytesIO
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_hr.to_excel(writer, sheet_name="หน้าสรุปส่ง HR", index=False)
    output.seek(0)

    st.download_button(
        "📥 ดาวน์โหลดไฟล์ Excel",
        data=output,
        file_name="หน้าสรุปส่ง_HR.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
