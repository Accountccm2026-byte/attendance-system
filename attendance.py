import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
import io

# --- การตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="ระบบบันทึกเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน")

# --- ชื่อไฟล์ข้อมูล ---
EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

# --- สร้างไฟล์เฉพาะเมื่อยังไม่มี หรือไฟล์ว่าง — ป้องกันข้อมูลหาย ---
if not os.path.exists(EMP_FILE) or os.path.getsize(EMP_FILE) == 0:
    pd.DataFrame(columns=["รหัสพนักงาน", "ชื่อพนักงาน", "ชื่อเล่น", "ตำแหน่ง"]).to_csv(EMP_FILE, index=False)

if not os.path.exists(REC_FILE) or os.path.getsize(REC_FILE) == 0:
    pd.DataFrame(columns=[
        "รหัสพนักงาน", "ชื่อพนักงาน", "วันที่", "สถานะ",
        "เวลาเข้า", "เวลาออก", "จำนวนชั่วโมง", "หมายเหตุ",
        "รูปเช็คอิน", "รูปเช็คเอาท์"
    ]).to_csv(REC_FILE, index=False)

# --- เมนูหลัก ---
menu = st.sidebar.selectbox("เมนูหลัก", [
    "จัดการรายชื่อพนักงาน",
    "บันทึกการเข้างาน/ลา",
    "ดูสรุปทั้งหมด",
    "หน้าสรุปส่ง HR",
    "📥 สำรองข้อมูล"
])

# ==========================================
# 1. จัดการรายชื่อพนักงาน
# ==========================================
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

# ==========================================
# 2. บันทึกการเข้างาน/ลา — แสดงและเก็บรูปได้จริง
# ==========================================
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
    pic_in_b64 = pic_out_b64 = ""
    
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
        
        # แปลงรูปเป็นข้อมูลเพื่อเก็บและแสดงได้
        if pic_in_file:
            st.image(pic_in_file, caption="รูปเช็คอิน", width=250)
            pic_in_b64 = f"data:image/jpeg;base64,{base64.b64encode(pic_in_file.read()).decode()}"
        
        if pic_out_file:
            st.image(pic_out_file, caption="รูปเช็คเอาท์", width=250)
            pic_out_b64 = f"data:image/jpeg;base64,{base64.b64encode(pic_out_file.read()).decode()}"
    else:
        note = st.text_area("หมายเหตุ / เหตุผล")
    
    if st.button("บันทึกข้อมูล", type="primary"):
        df_rec = pd.read_csv(REC_FILE)
        
        # คำนวณชั่วโมง
        hours = "-"
        if time_in and time_out:
            try:
                t1 = datetime.strptime(time_in, "%H:%M")
                t2 = datetime.strptime(time_out, "%H:%M")
                hours = f"{(t2 - t1).seconds / 3600:.1f}"
            except:
                pass
        
        new_rec = pd.DataFrame([[
            emp_id_sel, emp_name_sel, date_sel, status_sel,
            time_in or "-", time_out or "-", hours, note or "-",
            pic_in_b64, pic_out_b64
        ]], columns=[
            "รหัสพนักงาน", "ชื่อพนักงาน", "วันที่", "สถานะ",
            "เวลาเข้า", "เวลาออก", "จำนวนชั่วโมง", "หมายเหตุ",
            "รูปเช็คอิน", "รูปเช็คเอาท์"
        ])
        
        df_rec = pd.concat([df_rec, new_rec], ignore_index=True)
        df_rec.to_csv(REC_FILE, index=False)
        st.success("บันทึกสำเร็จ ✅")
        st.balloons()

# ==========================================
# 3. ดูสรุปทั้งหมด — แสดงรูปในตาราง
# ==========================================
elif menu == "ดูสรุปทั้งหมด":
    st.header("สรุปการทำงานทั้งหมด")
    df_rec = pd.read_csv(REC_FILE)
    
    if df_rec.empty:
        st.info("ยังไม่มีข้อมูล")
        st.stop()
    
    # ฟังก์ชันแสดงรูป
    def show_image_cell(val):
        val = str(val)
        if val.startswith("data:image"):
            return f'<img src="{val}" width="90" />'
        return val if val and val != "nan" else "-"
    
    # สร้างตารางพร้อมรูป
    df_display = df_rec.copy()
    df_display["รูปเช็คอิน"] = df_display["รูปเช็คอิน"].apply(show_image_cell)
    df_display["รูปเช็คเอาท์"] = df_display["รูปเช็คเอาท์"].apply(show_image_cell)
    
    st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
    st.subheader(f"รวมทั้งหมด {len(df_rec)} รายการ")

# ==========================================
# 4. หน้าสรุปส่ง HR
# ==========================================
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
    df_filtered = df_rec.loc[mask].copy()
    
    st.subheader(f"ข้อมูลช่วง {start_d.strftime('%Y/%m/%d')} ถึง {end_d.strftime('%Y/%m/%d')}")
    
    # แสดงพร้อมรูป
    def show_image_cell(val):
        val = str(val)
        if val.startswith("data:image"):
            return f'<img src="{val}" width="90" />'
        return val if val and val != "nan" else "-"
    
    df_filtered["รูปเช็คอิน"] = df_filtered["รูปเช็คอิน"].apply(show_image_cell)
    df_filtered["รูปเช็คเอาท์"] = df_filtered["รูปเช็คเอาท์"].apply(show_image_cell)
    st.write(df_filtered.to_html(escape=False, index=False), unsafe_allow_html=True)
    
    # --- ดาวน์โหลด Excel ---
    if not df_filtered.empty:
        # สำหรับ Excel เก็บเฉพาะชื่อไม่เก็บรูป (ข้อจำกัดไฟล์)
        df_excel = df_rec.loc[mask].copy()
        df_excel["รูปเช็คอิน"] = df_excel["รูปเช็คอิน"].apply(
            lambda x: "มีรูปแนบ" if str(x).startswith("data:image") else "-"
        )
        df_excel["รูปเช็คเอาท์"] = df_excel["รูปเช็คเอาท์"].apply(
            lambda x: "มีรูปแนบ" if str(x).startswith("data:image") else "-"
        )
        
        output_file = f"สรุปเวลาทำงาน_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
        with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
            df_excel.to_excel(writer, index=False, sheet_name="สรุป")
        
        with open(output_file, "rb") as f:
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์ Excel",
                data=f,
                file_name=output_file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        st.info("💡 ในไฟล์ Excel จะแสดงคำว่า 'มีรูปแนบ' — ดูรูปจริงได้ในหน้าเว็บระบบครับ")
    else:
        st.info("ไม่มีข้อมูลในช่วงเวลาที่เลือก")

# ==========================================
# 5. สำรองข้อมูล — ป้องกันข้อมูลหาย
# ==========================================
elif menu == "📥 สำรองข้อมูล":
    st.header("สำรองข้อมูล")
    
    # ดาวน์โหลดไฟล์พนักงาน
    if os.path.exists(EMP_FILE):
        with open(EMP_FILE, "rb") as f:
            st.download_button(
                label="📥 ดาวน์โหลด: รายชื่อพนักงาน.csv",
                data=f,
                file_name="รายชื่อพนักงาน.csv"
            )
    
    # ดาวน์โหลดไฟล์บันทึกเวลา
    if os.path.exists(REC_FILE):
        with open(REC_FILE, "rb") as f:
            st.download_button(
                label="📥 ดาวน์โหลด: ข้อมูลบันทึกเวลา.csv",
                data=f,
                file_name="ข้อมูลบันทึกเวลา.csv"
            )
    
    st.info("💡 คำแนะนำ: ดาวน์โหลดเก็บไว้ทุกครั้งที่มีการแก้ไขโค้ด เพื่อป้องกันข้อมูลหายครับ")
    
    # --- ส่วนกู้คืนข้อมูล ---
    st.subheader("กู้คืนข้อมูล (อัปโหลดไฟล์ที่สำรองไว้)")
    up_emp = st.file_uploader("อัปโหลด: รายชื่อพนักงาน.csv", type="csv")
    up_rec = st.file_uploader("อัปโหลด: ข้อมูลบันทึกเวลา.csv", type="csv")
    
    if up_emp and st.button("✅ บันทึกรายชื่อพนักงาน"):
        pd.read_csv(up_emp).to_csv(EMP_FILE, index=False)
        st.success("กู้คืนรายชื่อพนักงานสำเร็จ ✅")
        st.rerun()
    
    if up_rec and st.button("✅ บันทึกข้อมูลบันทึกเวลา"):
        pd.read_csv(up_rec).to_csv(REC_FILE, index=False)
        st.success("กู้คืนข้อมูลบันทึกเวลาสำเร็จ ✅")
        st.rerun()
