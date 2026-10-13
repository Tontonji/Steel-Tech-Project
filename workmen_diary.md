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

---

## 2026-09-28

- **Redesign UX/UI Next.js Web App (`steel-boq-app`)**:
  - พัฒนาเว็บแอปพลิเคชัน Next.js 16 + React 19 + TypeScript + Tailwind CSS โทนสี Dark Modern & Glassmorphism พร้อมลูกเล่น Dynamic Shader (`@paper-design/shaders-react` Warp)
  - Redesign หน้า `/extractor` ให้มีธีมและดีไซน์เข้าชุดกับหน้าแรก:
    - PDF Dropzone ลากวางไฟล์และเลือกหน้าอิสระ พร้อมตัวปรับ DPI (100–300)
    - macOS-style interactive BOQ Table รองรับ Inline Editable Cells (คลิกแก้ไขข้อมูลได้ทุกช่องและกด Enter เพื่อบันทึก)
    - Stat Tiles คำนวณสรุปผลอัตโนมัติ (Distinct Members, Total Pieces, Total Weight kg/ton, Needs Review)
    - ปุ่ม Export CSV สำหรับดาวน์โหลดข้อมูลที่แก้ไขแล้ว
- **แก้ไข Error & ปรับปรุง Navigation Links**:
  - แก้ไข JSX error ใน `components/ui/navbar.tsx`
  - ปรับลิงก์ GitHub บนหน้าเว็บทั้งหมด (Navbar, Hero "View Source", Footer) ให้ชี้ตรงไปยัง Repository ของโปรเจกต์: `https://github.com/Tontonji/Steel-Tech-Project`
- **อัปเกรด AI Model เป็น Gemini 3.8 Flash**:
  - อัปเดต `DEFAULT_MODEL` เป็น `"gemini-3.8-flash"` ใน `steel_boq_mvp/gemini_client.py`, `.env.example`, และเอกสาร README
  - ปรับ Badge, Config และคำอธิบายหน้าเว็บทั้งหมดให้เป็น Gemini 3.8 Flash
- **เชื่อมต่อ Gemini Vision API จริงใน Web App**:
  - สร้าง API Route `app/api/extract/route.ts` รับไฟล์ PDF แปลงเป็น base64 และส่งตรงไปยัง Gemini 3.8 Flash Vision API พร้อม Defensive JSON Parsing
  - สร้างโมดูลคำนวณน้ำหนักเหล็ก `lib/boq-calc.ts` (รองรับหน้าตัด H, C, W ตามสูตรของ `boq_utils.py`)
  - เพิ่มแถบตั้งค่า Gemini API Key ในหน้า `/extractor` บันทึกลง `localStorage` ในเบราว์เซอร์อัตโนมัติ
  - เพิ่มกฎใน `.gitignore` ป้องกันไม่ให้ไฟล์ `.env*` และข้อมูลความลับหลุดขึ้น Git
- **กู้คืน Dev Server หลังรีสตาร์ท**:
  - ตรวจสอบสถานะการเชื่อมต่อและเปิดรัน Next.js Turbopack dev server ใหม่บนพอร์ต 3000 พร้อมเปิดเบราว์เซอร์ใช้งานต่อเนื่อง

