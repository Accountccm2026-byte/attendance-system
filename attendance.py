import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import base64

st.set_page_config(page_title="ระบบบันทึกเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน")

EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

# สร้างไฟล์เฉพาะเมื่อไม่มีหรือว่าง — ป้องกันข้อมูลหาย
if not os.path.exists(EMP_FILE) or os.path.getsize(EMP_FILE) == 0:
    pd.DataFrame(columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"]).to_csv(EMP_FILE, index=False)
if not os.path.exists(REC_FILE) or os.path.getsize(REC_FILE) == 0:
    pd.DataFrame(columns=[
        "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
        "วันที่", "สถานะ", "เวลาเข้า", "เวลาออก",
        "จำนวนชั่วโมง", "หมายเหตุ", "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]).to_csv(REC_FILE, index=False)

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

# ==========================================
# 1. จัดการรายชื่อพนักงาน — มีแก้ไข + ลบ ✅
# ==========================================
if menu == "จัดการรายชื่อพนักงาน":
    st.header("จัดการรายชื่อพนักงาน")
    df_emp = pd.read_csv(EMP_FILE)

    # === ฟอร์มเพิ่มพนักงาน ===
    c1, c2, c3, c4 = st.columns(4)
    with c1: eid = st.text_input("รหัสพนักงาน")
    with c2: enam = st.text_input("ชื่อพนักงาน")
    with c3: enick = st.text_input("ชื่อเล่น")
    with c4: epos = st.text_input("ตำแหน่ง")

    if st.button("เพิ่มพนักงาน") and eid and enam:
        if "รหัสพนักงาน" in df_emp.columns:
            exists = eid in df_emp["รหัสพนักงาน"].astype(str).values
        else:
            exists = eid in df_emp.iloc[:, 0].astype(str).values
        
        if not exists:
            new = pd.DataFrame([[eid, enam, enick, epos]],
                columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"])
            df_emp = pd.concat([df_emp, new], ignore_index=True)
            df_emp.to_csv(EMP_FILE, index=False)
            st.success("เพิ่มสำเร็จ ✅")
            st.rerun()
        else:
            st.warning("มีรหัสนี้อยู่แล้ว ⚠️")

    # === รายชื่อพร้อมปุ่มแก้ไข / ลบ ===
    st.subheader("รายชื่อทั้งหมด")
    if df_emp.empty:
        st.info("ยังไม่มีข้อมูล")
    else:
        # เก็บสถานะแก้ไข
        if "edit_idx" not in st.session_state:
            st.session_state.edit_idx = None

        for idx, row in df_emp.iterrows():
            eid_row = row["รหัสพนักงาน"]
            name_row = row["ชื่อพนักงาน"]
            nick_row = row["ชื่อเล่น"]
            pos_row = row["ตำแหน่ง"]

            if st.session_state.edit_idx == idx:
                # === โหมดแก้ไข ===
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
                            df_emp.to_csv(EMP_FILE, index=False)
                            st.session_state.edit_idx = None
                            st.rerun()
                    with cl:
                        if st.form_submit_button("❌ ยกเลิก"):
                            st.session_state.edit_idx = None
                            st.rerun()
            else:
                # === แสดงปกติ + ปุ่ม ===
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

                # === ยืนยันการลบ ===
                if f"confirm_del_{idx}" in st.session_state and st.session_state[f"confirm_del_{idx}"]:
                    st.warning(f"ต้องการลบ {name_row} ใช่หรือไม่?")
                    y, n = st.columns(2)
                    if y.button("✅ ยืนยันลบ", key=f"del_ok_{idx}"):
                        df_emp = df_emp.drop(idx).reset_index(drop=True)
                        df_emp.to_csv(EMP_FILE, index=False)
                        del st.session_state[f"confirm_del_{idx}"]
                        st.success("ลบสำเร็จ ✅")
                        st.rerun()
                    if n.button("❌ ยกเลิก", key=f"del_no_{idx}"):
                        del st.session_state[f"confirm_del_{idx}"]
                        st.rerun()
                        
# ==========================================
# 2. บันทึกการเข้างาน/ลา — แยกเช็คอิน/เช็คเอาท์ได้ ✅
# ==========================================
elif menu == "บันทึกการเข้างาน/ลา":
    st.header("บันทึกการเข้างาน/ลา")
    df_emp = pd.read_csv(EMP_FILE)
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

    df_rec = pd.read_csv(REC_FILE)
    today_mask = (
        (df_rec["รหัสพนักงาน"].astype(str) == str(eid)) &
        (pd.to_datetime(df_rec["วันที่"], errors="coerce").dt.date == dt)
    )
    existing = df_rec.loc[today_mask]

    tin = tout = pin = pout = note = ""
    if not existing.empty:
        rec = existing.iloc[0]
        tin = str(rec["เวลาเข้า"]) if pd.notna(rec["เวลาเข้า"]) and rec["เวลาเข้า"] != "-" else ""
        tout = str(rec["เวลาออก"]) if pd.notna(rec["เวลาออก"]) and rec["เวลาออก"] != "-" else ""
        pin = str(rec["รูปเช็คอิน"]) if pd.notna(rec["รูปเช็คอิน"]) and rec["รูปเช็คอิน"] != "-" else ""
        pout = str(rec["รูปเช็คเอาท์"]) if pd.notna(rec["รูปเช็คเอาท์"]) and rec["รูปเช็คเอาท์"] != "-" else ""
        note = str(rec["หมายเหตุ"]) if pd.notna(rec["หมายเหตุ"]) and rec["หมายเหตุ"] != "-" else ""
        st.info(f"📋 มีบันทึกของวันนี้แล้ว | เวลาเข้า: {tin or '—'} | เวลาออก: {tout or '—'}")

    if stt in ["มาปกติ", "ทำงานล่วงเวลา"]:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🕘 เช็คอินเวลาเข้า")
            tin_new = st.time_input("เวลาเข้า", datetime.strptime(tin, "%H:%M") if tin else datetime.strptime("08:00", "%H:%M")).strftime("%H:%M")
            st.write("แนบรูปเช็คอิน")
            fin = st.file_uploader("อัปโหลดรูปเช็คอิน", type=["jpg", "jpeg", "png"], key="pin_upload")
            pin_new = f"data:image/jpeg;base64,{base64.b64encode(fin.read()).decode()}" if fin else pin
            if st.button("✅ บันทึกเวลาเข้า", type="primary"):
                hrs = "-"
                if tout:
                    try:
                        t1 = datetime.strptime(tin_new, "%H:%M")
                        t2 = datetime.strptime(tout, "%H:%M")
                        hrs = f"{(t2 - t1).seconds / 3600:.1f}"
                    except: pass
                if existing.empty:
                    new_rec = pd.DataFrame([[eid, enam, enick, epos, dt, stt, tin_new, tout, hrs, "-", pin_new, pout]], columns=df_rec.columns)
                    df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
                else:
                    idx = existing.index[0]
                    df_rec.at[idx, "เวลาเข้า"] = tin_new
                    df_rec.at[idx, "รูปเช็คอิน"] = pin_new
                    if hrs != "-": df_rec.at[idx, "จำนวนชั่วโมง"] = hrs
                df_rec.to_csv(REC_FILE, index=False)
                st.success("บันทึกเวลาเข้าสำเร็จ ✅")
                st.rerun()
        with col2:
            st.subheader("🕕 เช็คเอาท์เวลาออก")
            tout_new = st.time_input("เวลาออก", datetime.strptime(tout, "%H:%M") if tout else datetime.strptime("17:00", "%H:%M")).strftime("%H:%M")
            st.write("แนบรูปเช็คเอาท์")
            fout = st.file_uploader("อัปโหลดรูปเช็คเอาท์", type=["jpg", "jpeg", "png"], key="pout_upload")
            pout_new = f"data:image/jpeg;base64,{base64.b64encode(fout.read()).decode()}" if fout else pout
            if st.button("✅ บันทึกเวลาออก", type="primary"):
                hrs = "-"
                if tin or tin_new:
                    try:
                        t1 = datetime.strptime(tin or tin_new, "%H:%M")
                        t2 = datetime.strptime(tout_new, "%H:%M")
                        hrs = f"{(t2 - t1).seconds / 3600:.1f}"
                    except: pass
                if existing.empty:
                    new_rec = pd.DataFrame([[eid, enam, enick, epos, dt, stt, tin, tout_new, hrs, "-", pin, pout_new]], columns=df_rec.columns)
                    df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
                else:
                    idx = existing.index[0]
                    df_rec.at[idx, "เวลาออก"] = tout_new
                    df_rec.at[idx, "รูปเช็คเอาท์"] = pout_new
                    df_rec.at[idx, "จำนวนชั่วโมง"] = hrs
                df_rec.to_csv(REC_FILE, index=False)
                st.success("บันทึกเวลาออกสำเร็จ ✅")
                st.rerun()
    else:
        note = st.text_area("หมายเหตุ / เหตุผล", value=note)
        if st.button("✅ บันทึกข้อมูล", type="primary"):
            if existing.empty:
                new_rec = pd.DataFrame([[eid, enam, enick, epos, dt, stt, "-", "-", "-", note, "-", "-"]], columns=df_rec.columns)
                df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
            else:
                idx = existing.index[0]
                df_rec.at[idx, "สถานะ"] = stt
                df_rec.at[idx, "หมายเหตุ"] = note
            df_rec.to_csv(REC_FILE, index=False)
            st.success("บันทึกสำเร็จ ✅")
            st.rerun()

# ==========================================
# 3. หน้าสรุปภาพรวม
# ==========================================
elif menu == "หน้าสรุปภาพรวม":
    st.header("สรุปภาพรวม")
    df_rec = pd.read_csv(REC_FILE)
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()

    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    df_rec["มาปกติ(วัน)"] = (df_rec["สถานะ"] == "มาปกติ").astype(int)
    df_rec["ลาป่วย(วัน)"] = (df_rec["สถานะ"] == "ลาป่วย").astype(int)
    df_rec["ลากิจ(วัน)"] = (df_rec["สถานะ"] == "ลากิจ").astype(int)
    df_rec["ลาพักร้อน(วัน)"] = (df_rec["สถานะ"] == "ลาพักร้อน").astype(int)
    df_rec["ขาดงาน(วัน)"] = (df_rec["สถานะ"] == "ขาดงาน").astype(int)
    df_rec["OT(ครั้ง)"] = df_rec["สถานะ"].apply(lambda x: 1 if "ล่วงเวลา" in str(x) else 0)

    summary = df_rec.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    )[["มาปกติ(วัน)","ลาป่วย(วัน)","ลากิจ(วัน)","ลาพักร้อน(วัน)","ขาดงาน(วัน)","OT(ครั้ง)"]].sum().reset_index()

    st.dataframe(summary, use_container_width=True)

# ==========================================
# 4. รายงานรายชื่อ+วันทำงาน — มีรูปเช็คอิน/เช็คเอาท์
# ==========================================
elif menu == "รายงานรายชื่อ+วันทำงาน":
    st.header("รายงานรายชื่อ+วันทำงาน")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("วันที่เริ่ม", datetime(2026, 9, 26))
    end_d = c2.date_input("วันที่สิ้นสุด", datetime(2026, 10, 25))
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")

    df_rec = pd.read_csv(REC_FILE)
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    mask = (df_rec["วันที่"] >= pd.to_datetime(start_d)) & (df_rec["วันที่"] <= pd.to_datetime(end_d))
    df = df_rec.loc[mask].copy()
    
    if df.empty:
        st.info("ไม่มีข้อมูลในช่วงวันที่ที่เลือก")
        st.stop()

    # สรุปรวม
    st.subheader("สรุปรวม")
    df["มาปกติ(วัน)"] = (df["สถานะ"] == "มาปกติ").astype(int)
    df["ลาป่วย(วัน)"] = (df["สถานะ"] == "ลาป่วย").astype(int)
    df["WOP(วัน)"] = 0
    df["ลากิจไม่รับเงิน(ชม.)"] = 0
    df["ขาดงาน(วัน)"] = (df["สถานะ"] == "ขาดงาน").astype(int)
    
    sum_df = df.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    )[["มาปกติ(วัน)","ลาป่วย(วัน)","WOP(วัน)","ลากิจไม่รับเงิน(ชม.)","ขาดงาน(วัน)"]].sum().reset_index()
    st.dataframe(sum_df, use_container_width=True)

    # รายละเอียดรายวัน — มีรูปเช็คอิน/เช็คเอาท์ ✅
    st.subheader("รายละเอียดรายวัน")
    day_df = df.copy()
    day_df["วันที่"] = day_df["วันที่"].dt.strftime("%d/%m/%y")
    day_df["ชม.ปกติ"] = day_df["จำนวนชั่วโมง"]
    day_df["OT 1.5(ชม.)"] = 0
    day_df["OT 1(ชม.)"] = 0
    day_df["สถานะ"] = day_df["สถานะ"].apply(lambda x: f"✅ {x}" if x == "มาปกติ" else x)
    
    day_df["รูปเช็คอิน"] = day_df["รูปเช็คอิน"].apply(img_cell)
    day_df["รูปเช็คเอาท์"] = day_df["รูปเช็คเอาท์"].apply(img_cell)
    
    day_cols = [
        "วันที่", "รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง",
        "สถานะ", "เวลาเข้า", "เวลาออก", "ชม.ปกติ", "OT 1.5(ชม.)", "OT 1(ชม.)",
        "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]
    
    st.write(day_df[day_cols].to_html(escape=False, index=False), unsafe_allow_html=True)

    # ดาวน์โหลด Excel
    day_xl = day_df[day_cols].copy()
    day_xl["รูปเช็คอิน"] = day_xl["รูปเช็คอิน"].apply(lambda x: "มีรูป" if str(x).startswith("<img") else "-")
    day_xl["รูปเช็คเอาท์"] = day_xl["รูปเช็คเอาท์"].apply(lambda x: "มีรูป" if str(x).startswith("<img") else "-")
    
    out_file = f"รายงาน_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(out_file, engine="openpyxl") as w:
        sum_df.to_excel(w, sheet_name="สรุปรวม", index=False)
        day_xl.to_excel(w, sheet_name="รายละเอียด", index=False)
    with open(out_file, "rb") as f:
        st.download_button("📥 ดาวน์โหลดรายงาน Excel", f, out_file)

# ==========================================
# 5. หน้าสรุปส่ง HR — ตรงรูปแบบเป๊ะๆ ✅
# ==========================================
elif menu == "หน้าสรุปส่ง HR":
    st.header("หน้าสรุปส่ง HR")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("วันที่เริ่มต้น", datetime(2026, 9, 26))
    end_d = c2.date_input("วันที่สิ้นสุด", datetime(2026, 10, 25))
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")

    df_rec = pd.read_csv(REC_FILE)
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"], errors="coerce")
    mask = (df_rec["วันที่"] >= pd.to_datetime(start_d)) & (df_rec["วันที่"] <= pd.to_datetime(end_d))
    df = df_rec.loc[mask].copy()
    
    if df.empty:
        st.info("ไม่มีข้อมูลในช่วงนี้")
        st.stop()

    # เตรียมข้อมูล
    df["วันที่_str"] = df["วันที่"].dt.strftime("%d/%m/%y")
    df["ค่า"] = df["สถานะ"].apply(lambda x: 1 if x == "มาปกติ" else "")
    
    # สร้าง Pivot: พนักงาน x วันที่
    pivot = df.pivot_table(
        index=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"],
        columns="วันที่_str",
        values="ค่า",
        aggfunc="first",
        fill_value=""
    ).reset_index()

    # คำนวณสรุปต่อท้าย
    emp_summary = df.groupby(
        ["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"], dropna=False
    ).apply(lambda g: pd.Series({
        "มาปกติ(วัน)": (g["สถานะ"] == "มาปกติ").sum(),
        "ลาป่วย(วัน)": (g["สถานะ"] == "ลาป่วย").sum(),
        "WOP(วัน)": 0,
        "ลากิจไม่รับเงิน(ชม.)": 0,
        "ขาดงาน(วัน)": (g["สถานะ"] == "ขาดงาน").sum(),
        "OT 1.5(ชม.)": 0,
        "OT 1(ชม.)": 0,
        "มาสายรวม(ชม.)": 0,
        "มาสายรวม(นาที)": 0
    })).reset_index()

    # รวมคอลัมน์วันที่ + สรุป ติดกันเป็นแถวเดียว ✅
    final_df = pd.merge(pivot, emp_summary,
                        on=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"])

    # แสดงผล
    st.dataframe(final_df, use_container_width=True)

    # ดาวน์โหลด Excel
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
        pd.read_csv(up_emp).to_csv(EMP_FILE, index=False)
        st.success("กู้คืนรายชื่อสำเร็จ ✅")
        st.rerun()

    if up_rec and st.button("✅ บันทึกข้อมูลบันทึกเวลา"):
        pd.read_csv(up_rec).to_csv(REC_FILE, index=False)
        st.success("กู้คืนข้อมูลสำเร็จ ✅")
        st.rerun()
