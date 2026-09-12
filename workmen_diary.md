# Workmen Diary

บันทึกประจำวันว่าทำอะไรไปบ้างในโปรเจกต์ Steel-Tech-Project

---

## 2026-09-09

- ตั้งค่า Gemini API key: สร้างไฟล์ `steel_boq_mvp/.env` จาก `.env.example` และใส่คีย์จริง
- ทดสอบเรียก Gemini API โดยตรงกับ `samples/sample_schedule.pdf` — สกัดข้อมูลเหล็ก 12 รายการสำเร็จ ยืนยันว่าคีย์ใช้งานได้จริง
- รันแอป Streamlit (`app.py`) และยืนยันว่าตอบสนอง (HTTP 200) ที่ `http://localhost:8501`
- เริ่ม brainstorm ฟีเจอร์ใหม่ "3D viewer" สำหรับดูโครงสร้างเหล็กและแต่ละชิ้นส่วนแบบ 3 มิติ:
  - สรุปว่าข้อมูลที่สกัดได้ตอนนี้ (`member_id, section, length_mm, quantity`) ไม่มีพิกัดตำแหน่งจริง
  - ตกลงแนวทางเฟส 1: schematic auto-layout (ไม่ใช่ตำแหน่งจริงจากแบบ) ใช้ Plotly 3D mesh extrude ตามหน้าตัดจริง
  - ยังไม่ได้อนุมัติ design สุดท้าย — ค้างรอต่อ
- เริ่มทำ workmen diary (ไฟล์นี้) สำหรับบันทึกงานประจำวัน
