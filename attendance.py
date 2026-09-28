import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64

st.set_page_config(page_title="ระบบบันทึกเวลาทำงาน", layout="wide")
st.title("📋 ระบบบันทึกเวลาทำงาน")

EMP_FILE = "employees.csv"
REC_FILE = "records.csv"

# สร้างเฉพาะเมื่อไม่มีหรือว่าง
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
    return f'<img src="{s}" width="70" />' if s.startswith("data:image") else "-"

# ===========================================
# 1. จัดการรายชื่อพนักงาน
# ==========================================
if menu == "จัดการรายชื่อพนักงาน":
    st.header("จัดการรายชื่อพนักงาน")
    df_emp = pd.read_csv(EMP_FILE)
    c1,c2,c3,c4 = st.columns(4)
    with c1: eid = st.text_input("รหัสพนักงาน")
    with c2: enam = st.text_input("ชื่อพนักงาน")
    with c3: enick = st.text_input("ชื่อเล่น")
    with c4: epos = st.text_input("ตำแหน่ง")
    if st.button("เพิ่มพนักงาน") and eid and enam:
        exists = eid in df_emp["รหัสพนักงาน"].astype(str).values if "รหัสพนักงาน" in df_emp.columns else eid in df_emp.iloc[:,0].astype(str).values
        if not exists:
            new = pd.DataFrame([[eid,enam,enick,epos]],
                columns=["รหัสพนักงาน","ชื่อพนักงาน","ชื่อเล่น","ตำแหน่ง"])
            df_emp = pd.concat([df_emp, new], ignore_index=True)
            df_emp.to_csv(EMP_FILE, index=False)
            st.success("เพิ่มสำเร็จ ✅")
            st.rerun()
        else:
            st.warning("มีรหัสนี้แล้ว ⚠️")
    st.subheader("รายชื่อทั้งหมด")
    st.dataframe(df_emp, use_container_width=True) if not df_emp.empty else st.info("ยังไม่มีข้อมูล")

# ==========================================
# 2. บันทึกการเข้างาน/ลา
# ==========================================
elif menu == "บันทึกการเข้างาน/ลา":
    st.header("บันทึกการเข้างาน/ลา")
    df_emp = pd.read_csv(EMP_FILE)
    if df_emp.empty: st.warning("เพิ่มรายชื่อก่อน ⚠️"); st.stop()
    sel = st.selectbox("เลือกพนักงาน", [f"{r['รหัสพนักงาน']} | {r['ชื่อพนักงาน']} — {r['ตำแหน่ง']}" for _,r in df_emp.iterrows()])
    eid = sel.split(" | ")[0]; enam = sel.split(" | ")[1].split(" — ")[0]
    emp_row = df_emp[df_emp["รหัสพนักงาน"].astype(str)==eid].iloc[0]
    enick = emp_row["ชื่อเล่น"]; epos = emp_row["ตำแหน่ง"]
    dt = st.date_input("วันที่", datetime.now())
    stt = st.selectbox("สถานะ", ["มาปกติ","ลาป่วย","ลากิจ","ลาพักร้อน","ขาดงาน","ทำงานล่วงเวลา"])
    tin=tout=note=""; pin=pout=""
    if stt in ["มาปกติ","ทำงานล่วงเวลา"]:
        a,b=st.columns(2)
        with a: tin=st.time_input("เวลาเข้า",datetime.strptime("08:00","%H:%M")).strftime("%H:%M")
        with b: tout=st.time_input("เวลาออก",datetime.strptime("17:00","%H:%M")).strftime("%H:%M")
        st.subheader("แนบรูป")
        fin=st.file_uploader("รูปเช็คอิน",type=["jpg","jpeg","png"])
        fout=st.file_uploader("รูปเช็คเอาท์",type=["jpg","jpeg","png"])
        if fin: st.image(fin,width=200); pin=f"data:image/jpeg;base64,{base64.b64encode(fin.read()).decode()}"
        if fout: st.image(fout,width=200); pout=f"data:image/jpeg;base64,{base64.b64encode(fout.read()).decode()}"
    else: note=st.text_area("หมายเหตุ/เหตุผล")
    if st.button("บันทึก",type="primary"):
        hrs="-"
        if tin and tout:
            try: hrs=f"{(datetime.strptime(tout,'%H:%M')-datetime.strptime(tin,'%H:%M')).seconds/3600:.1f}"
            except: pass
        df_rec=pd.read_csv(REC_FILE)
        new_rec=pd.DataFrame([[eid,enam,enick,epos,dt,stt,tin,tout,hrs,note or "-",pin,pout]],
            columns=["รหัสพนักงาน","ชื่อพนักงาน","ชื่อเล่น","ตำแหน่ง","วันที่","สถานะ","เวลาเข้า","เวลาออก","จำนวนชั่วโมง","หมายเหตุ","รูปเช็คอิน","รูปเช็คเอาท์"])
        df_rec=pd.concat([df_rec,new_rec],ignore_index=True)
        df_rec.to_csv(REC_FILE,index=False)
        st.success("บันทึกสำเร็จ ✅"); st.balloons()

# ==========================================
# 3. หน้าสรุปภาพรวม — แก้ไขแล้ว
# ==========================================
elif menu == "หน้าสรุปภาพรวม":
    st.header("สรุปภาพรวม")
    df_rec = pd.read_csv(REC_FILE)
    if df_rec.empty: st.info("ยังไม่มีข้อมูล"); st.stop()

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
# 4. รายงานรายชื่อ+วันทำงาน
# ==========================================
elif menu == "รายงานรายชื่อ+วันทำงาน":
    st.header("รายงานรายชื่อ+วันทำงาน")
    c1,c2=st.columns(2)
    start_d=c1.date_input("เริ่ม",datetime(2026,9,26))
    end_d=c2.date_input("สิ้นสุด",datetime(2026,10,25))
    st.subheader(f"รอบ {start_d.strftime('%d/%m/%y')} - {end_d.strftime('%d/%m/%y')}")

    df_rec=pd.read_csv(REC_FILE)
    if df_rec.empty: st.info("ไม่มีข้อมูล"); st.stop()
    df_rec["วันที่"]=pd.to_datetime(df_rec["วันที่"],errors="coerce")
    mask=(df_rec["วันที่"]>=pd.to_datetime(start_d))&(df_rec["วันที่"]<=pd.to_datetime(end_d))
    df=df_rec.loc[mask].copy()
    if df.empty: st.info("ไม่มีข้อมูลในช่วงนี้"); st.stop()

    # สรุปรวม
    st.subheader("สรุปรวม")
    df["มาปกติ(วัน)"]=(df["สถานะ"]=="มาปกติ").astype(int)
    df["ลาป่วย(วัน)"]=(df["สถานะ"]=="ลาป่วย").astype(int)
    df["WOP(วัน)"]=0
    df["ลากิจไม่รับเงิน(ชม.)"]=0
    df["ขาดงาน(วัน)"]=(df["สถานะ"]=="ขาดงาน").astype(int)
    sum_df=df.groupby(["รหัสพนักงาน","ชื่อพนักงาน","ชื่อเล่น","ตำแหน่ง"],dropna=False)[
        ["มาปกติ(วัน)","ลาป่วย(วัน)","WOP(วัน)","ลากิจไม่รับเงิน(ชม.)","ขาดงาน(วัน)"]
    ].sum().reset_index()
    st.dataframe(sum_df, use_container_width=True)

    # รายละเอียดรายวัน
    st.subheader("รายละเอียดรายวัน")
    day_df=df.copy()
    day_df["วันที่"]=day_df["วันที่"].dt.strftime("%d/%m/%y")
    day_df["ชม.ปกติ"]=day_df["จำนวนชั่วโมง"]
    day_df["OT 1.5(ชม.)"]=0
    day_df["OT 1(ชม.)"]=0
    day_df["สถานะ"]=day_df["สถานะ"].apply(lambda x:f"✅ {x}" if x=="มาปกติ" else x)
    day_cols=["วันที่","รหัสพนักงาน","ชื่อพนักงาน","ชื่อเล่น","ตำแหน่ง","สถานะ","เวลาเข้า","เวลาออก","ชม.ปกติ","OT 1.5(ชม.)","OT 1(ชม.)"]
    st.dataframe(day_df[day_cols], use_container_width=True)

    # ดาวน์โหลด
    out=f"รายงาน_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(out,engine="openpyxl") as w:
        sum_df.to_excel(w,sheet_name="สรุปรวม",index=False)
        day_df[day_cols].to_excel(w,sheet_name="รายละเอียด",index=False)
    with open(out,"rb") as f: st.download_button("📥 ดาวน์โหลด Excel",f,out)

# ==========================================
# 5. หน้าสรุปส่ง HR
# ==========================================
elif menu == "หน้าสรุปส่ง HR":
    st.header("หน้าสรุปส่ง HR")
    c1,c2=st.columns(2)
    start_d=c1.date_input("เริ่ม",datetime(2026,9,26))
    end_d=c2.date_input("สิ้นสุด",datetime(2026,10,25))
    df_rec=pd.read_csv(REC_FILE)
    if df_rec.empty: st.info("ไม่มีข้อมูล"); st.stop()
    df_rec["วันที่"]=pd.to_datetime(df_rec["วันที่"],errors="coerce")
    mask=(df_rec["วันที่"]>=pd.to_datetime(start_d))&(df_rec["วันที่"]<=pd.to_datetime(end_d))
    df=df_rec.loc[mask].copy()
    if df.empty: st.info("ไม่มีข้อมูลในช่วงนี้"); st.stop()
    st.subheader(f"ช่วง {start_d.strftime('%Y/%m/%d')} - {end_d.strftime('%Y/%m/%d')}")

    df["รูปเช็คอิน"]=df["รูปเช็คอิน"].apply(img_cell)
    df["รูปเช็คเอาท์"]=df["รูปเช็คเอาท์"].apply(img_cell)
    st.write(df.to_html(escape=False,index=False), unsafe_allow_html=True)

    df_xl=df.copy()
    df_xl["รูปเช็คอิน"]=df_xl["รูปเช็คอิน"].apply(lambda x:"มีรูป" if str(x).startswith("<img") else "-")
    df_xl["รูปเช็คเอาท์"]=df_xl["รูปเช็คเอาท์"].apply(lambda x:"มีรูป" if str(x).startswith("<img") else "-")
    fn=f"สรุปส่งHR_{start_d.strftime('%Y%m%d')}_{end_d.strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(fn,engine="openpyxl") as w: df_xl.to_excel(w,index=False)
    with open(fn,"rb") as f: st.download_button("📥 ดาวน์โหลด",f,fn)
    st.info("💡 ดูรูปจริงในหน้าเว็บ")

# ==========================================
# 6. สำรองข้อมูล
# ==========================================
elif menu == "📥 สำรองข้อมูล":
    st.header("สำรองข้อมูล")
    if os.path.exists(EMP_FILE):
        with open(EMP_FILE,"rb") as f: st.download_button("📥 รายชื่อพนักงาน.csv",f,"รายชื่อพนักงาน.csv")
    if os.path.exists(REC_FILE):
        with open(REC_FILE,"rb") as f: st.download_button("📥 ข้อมูลบันทึกเวลา.csv",f,"ข้อมูลบันทึกเวลา.csv")
    st.info("ดาวน์โหลดเก็บไว้ก่อนแก้ไขโค้ด")

    st.subheader("กู้คืนข้อมูล")
    up_emp=st.file_uploader("อัปโหลดรายชื่อ",type="csv")
    up_rec=st.file_uploader("อัปโหลดข้อมูลเวลา",type="csv")
    if up_emp and st.button("บันทึกรายชื่อ"): pd.read_csv(up_emp).to_csv(EMP_FILE,index=False); st.success("สำเร็จ ✅"); st.rerun()
    if up_rec and st.button("บันทึกข้อมูลเวลา"): pd.read_csv(up_rec).to_csv(REC_FILE,index=False); st.success("สำเร็จ ✅"); st.rerun()
