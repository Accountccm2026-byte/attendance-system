import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="ระบบบันทึกเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน")

EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

if not os.path.exists(EMP_FILE):
    pd.DataFrame(columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"]).to_csv(EMP_FILE, index=False)
if not os.path.exists(REC_FILE):
    pd.DataFrame(columns=[
        "รหัสพนักงาน", "ชื่อพนักงาน", "วันที่", "สถานะ",
        "เวลาเข้า", "เวลาออก", "จำนวนชั่วโมง", "หมายเหตุ",
        "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]).to_csv(REC_FILE, index=False)

menu = st.sidebar.selectbox("เมนูหลัก", [
    "จัดการรายชื่อพนักงาน",
    "บันทึกการเข้างาน/ลา",
    "ดูสรุปทั้งหมด",
    "หน้าสรุปส่ง HR"
])

if menu == "จัดการรายชื่อพนักงาน":
    st.header("จัดการรายชื่อพนักงาน")
    df_emp = pd.read_csv(EMP_FILE)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: emp_id = st.text_input("รหัสพนักงาน")
    with col2: emp_name = st.text_input("ชื่อพนักงาน")
    with col3: emp_nick = st.text_input("ชื่อเล่น")
    with col4: emp_pos = st.text_input("ตำแหน่ง")
    
    if st.button("เพิ่มพนักงาน"):
        if emp_id and emp_name:
            # เช็ครหัสซ้ำ ปลอดภัยแน่นอน
            if "รหัสพนักงาน" in df_emp.columns:
                exists = emp_id in df_emp["รหัสพนักงาน"].astype(str).values
            else:
                exists = emp_id in df_emp.iloc[:, 0].astype(str).values
            
            if not exists:
                new_row = pd.DataFrame([[emp_id, emp_name, emp_nick, emp_pos]],
                                      columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"])
                df_emp = pd.concat([df_emp, new_row], ignore_index=True)
                df_emp.to_csv(EMP_FILE, index=False)
                st.success(f"เพิ่ม {emp_name} สำเร็จ ✅")
                st.rerun()
            else:
                st.warning("มีรหัสนี้อยู่แล้ว ⚠️")
        else:
            st.error("กรุณากรอกรหัสและชื่อ")
    
    st.subheader("รายชื่อทั้งหมด")
    if not df_emp.empty:
        st.dataframe(df_emp, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลพนักงาน")

elif menu == "บันทึกการเข้างาน/ลา":
    st.header("บันทึกการเข้างาน/ลา")
    df_emp = pd.read_csv(EMP_FILE)
    if df_emp.empty:
        st.warning("กรุณาเพิ่มรายชื่อพนักงานก่อน ⚠️")
        st.stop()
    
    emp_sel = st.selectbox("เลือกพนักงาน", [
        f"{row['รหัสพนักงาน']} | {row['ชื่อพนักงาน']} — {row['ตำแหน่ง']}"
        for _, row in df_emp.iterrows()
    ])
    emp_id_sel = emp_sel.split(" | ")[0]
    emp_name_sel = emp_sel.split(" | ")[1].split(" — ")[0]
    
    date_sel = st.date_input("วันที่", datetime.now())
    status_sel = st.selectbox("สถานะ", [
        "มาปกติ", "ลาป่วย", "ลากิจ", "ลาพักร้อน", "ขาดงาน", "ทำงานล่วงเวลา"
    ])
    
    time_in = time_out = note = None
    pic_in_file = pic_out_file = None
    
    if status_sel == "มาปกติ":
        col_a, col_b = st.columns(2)
        with col_a:
            t_in = st.time_input("เวลาเข้า", value=datetime.strptime("08:00", "%H:%M").time())
            time_in = t_in.strftime("%H:%M")
        with col_b:
            t_out = st.time_input("เวลาออก", value=datetime.strptime("17:00", "%H:%M").time())
            time_out = t_out.strftime("%H:%M")
        
        st.subheader("แนบรูปภาพ")
        pic_in_file = st.file_uploader("แนบรูปเช็คอิน", type=["jpg", "jpeg", "png"])
        pic_out_file = st.file_uploader("แนบรูปเช็คเอาท์", type=["jpg", "jpeg", "png"])
        
        if pic_in_file is not None:
            st.image(pic_in_file, caption="รูปเช็คอิน", width=250)
        if pic_out_file is not None:
            st.image(pic_out_file, caption="รูปเช็คเอาท์", width=250)
    else:
        note = st.text_area("หมายเหตุ / เหตุผล")
    
    if st.button("บันทึกข้อมูล", type="primary"):
        df_rec = pd.read_csv(REC_FILE)
        hours = ""
        if time_in and time_out:
            try:
                t1 = datetime.strptime(time_in, "%H:%M")
                t2 = datetime.strptime(time_out, "%H:%M")
                hours = f"{(t2-t1).seconds/3600:.1f}"
            except:
                hours = "-"
        
        pic_in_name = pic_in_file.name if pic_in_file else ""
        pic_out_name = pic_out_file.name if pic_out_file else ""
        
        new_rec = pd.DataFrame([[
            emp_id_sel, emp_name_sel, date_sel, status_sel,
            time_in or "-", time_out or "-", hours, note or "-",
            pic_in_name, pic_out_name
        ]], columns=[
            "รหัสพนักงาน", "ชื่อพนักงาน", "วันที่", "สถานะ",
            "เวลาเข้า", "เวลาออก", "จำนวนชั่วโมง", "หมายเหตุ",
            "รูปเช็คอิน", "รูปเช็คเอาท์"
        ])
        
        df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
        df_rec.to_csv(REC_FILE, index=False)
        st.success("บันทึกสำเร็จ ✅")
        st.balloons()

elif menu == "ดูสรุปทั้งหมด":
    st.header("สรุปการทำงานทั้งหมด")
    df_rec = pd.read_csv(REC_FILE)
    if not df_rec.empty:
        st.dataframe(df_rec, use_container_width=True)
        st.subheader(f"รวมทั้งหมด {len(df_rec)} รายการ")
    else:
        st.info("ยังไม่มีข้อมูล")

elif menu == "หน้าสรุปส่ง HR":
    st.header("หน้าสรุปส่ง HR")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_d = st.date_input("วันที่เริ่มต้น", datetime(2026, 9, 26))
    with col_d2:
        end_d = st.date_input("วันที่สิ้นสุด", datetime(2026, 10, 25))
    
    df_rec = pd.read_csv(REC_FILE)
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูลสำหรับส่ง HR")
        st.stop()
    
    df_rec["วันที่"] = pd.to_datetime(df_rec["วันที่"])
    mask = (df_rec["วันที่"] >= pd.to_datetime(start_d)) & (df_rec["วันที่"] <= pd.to_datetime(end_d))
    df_filtered = df_rec.loc[mask]
    
    st.subheader(f"ข้อมูลช่วง {start_d.strftime('%Y/%m/%d')} ถึง {end_d.strftime('%Y/%m/%d')}")
    st.dataframe(df_filtered, use_container_width=True)
    
    if not df_filtered.empty:
        output_file = f"สรุปเวลาทำงาน_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df_filtered.to_excel(writer, index=False, sheet_name="สรุป")
        
        with open(output_file, "rb") as f:
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ Excel",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.info("ไม่มีข้อมูลในช่วงเวลาที่เลือก")
