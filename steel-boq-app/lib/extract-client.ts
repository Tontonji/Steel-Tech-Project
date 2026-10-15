import { calculateUnitWeight } from "@/lib/boq-calc";
import { PDFDocument } from "pdf-lib";

export interface PageAnalysis {
  page_number: number;
  sheet_no?: string;
  sheet_name?: string;
  is_structural: boolean;
  category?: "STRUCTURAL" | "ARCHITECTURAL" | "MEP" | "COVER_OR_OTHER" | string;
  summary?: string;
}

export interface ExtractedBOQItem {
  member_id: string;
  section: string;
  length_mm: number | null;
  quantity: number | null;
  unit_weight_kg_m: number | null;
  source_page?: number | null;
  sheet_no?: string | null;
  notes: string;
}

const EXTRACTION_PROMPT = `You are an expert structural engineer and BIM/construction drawing takeoff specialist.
You are analyzing an engineering/architectural drawing set (CAD-exported or scanned PDF).

YOUR GOALS:
1. EXAMINE EVERY PAGE IN THIS PDF DOCUMENT:
   - Carefully inspect each page's title block, drawing title, notes, and visual content.
   - CLASSIFY every page:
     * IS IT A STRUCTURAL DRAWING? (is_structural = true):
       Examples: Foundation/Footing plans (แบบแปลนฐานราก-เสาเข็ม), Column/Pedestal layout, Ground/Floor beam framing plans (แปลนคานคอดิน, แปลนคานชั้นต่างๆ), Steel roof framing plan (แปลนโครงสร้างหลังคาเหล็ก, แปลนจันทัน-แป), Structural member schedules (ตารางเหล็กรูปพรรณ, ตารางคาน, ตารางเสา), Truss details (แบบขยายโครงถักเหล็ก), Connection details, Base plate details.
     * IS IT NON-STRUCTURAL? (is_structural = false):
       Examples: Architectural floor plans (แปลนพื้นสถาปัตย์), Elevations (รูปด้าน), Building sections (รูปตัดสถาปัตย์), Site/Location plan (ผังบริเวณ), Door/Window schedules (ตารางประตูหน้าต่าง), Electrical/Lighting/Power plans (แบบไฟฟ้า), Sanitary/Plumbing plans (สุขาภิบาล, ท่อน้ำ), Cover sheets, Perspectives/3D.

2. DETECT & EXTRACT STRUCTURAL STEEL MEMBERS ONLY:
   - Extract distinct structural steel members (H-Beam, I-Beam, Wide-Flange, Channel [ / C-Purlin, Lip Channel, Equal Angle L, Steel Tubes/Pipes, Sag Rods, Tie Rods, Base Plates, Gusset Plates) identified on the STRUCTURAL pages or member schedules.
   - DO NOT extract non-structural architectural elements (timber, aluminium door frames, plumbing pipes, glass).
   - For each member:
     * member_id: Tag/Mark shown on the drawing (e.g. B1, B2, 2B1, C1, RB1, P1, TR-1, etc.)
     * section: Standard steel section designation (e.g. H-300x150x6.5x9, 2C-150x50x20x3.2, L-50x50x4, Pipe 100 dia, Plate 10mm)
     * length_mm: Length in millimeters if dimensioned or derived from grid lines; null if not indicated
     * quantity: Count of this member instance
     * source_page: The 1-based page number where this member or its schedule was found
     * sheet_no: Drawing sheet number (e.g. S-01, S-02, ST-05) if visible in title block
     * notes: Brief context (e.g. "From Roof Framing Plan", "Found in beam schedule", or grid coordinate)

3. OUTPUT FORMAT:
Return a JSON object with this EXACT schema:
{
  "page_analysis": [
    {
      "page_number": 1,
      "sheet_no": "A-01",
      "sheet_name": "แปลนพื้นชั้น 1",
      "is_structural": false,
      "category": "ARCHITECTURAL",
      "summary": "Architectural floor plan showing room layouts and doors/windows"
    },
    {
      "page_number": 5,
      "sheet_no": "S-03",
      "sheet_name": "แปลนโครงสร้างหลังคาเหล็ก",
      "is_structural": true,
      "category": "STRUCTURAL",
      "summary": "Roof framing plan showing steel rafters, purlins C-150, sag rods and truss tags"
    }
  ],
  "structural_pages": [5],
  "items": [
    {
      "member_id": "RB-1",
      "section": "H-250x125x6x9",
      "length_mm": 6000,
      "quantity": 8,
      "source_page": 5,
      "sheet_no": "S-03",
      "notes": "Main roof beam"
    }
  ]
}

Only return valid JSON without extra text or markdown formatting outside JSON.`;

interface RawBOQItem {
  member_id?: string | null;
  section?: string | null;
  length_mm?: number | string | null;
  quantity?: number | string | null;
  unit_weight_kg_m?: number | string | null;
  source_page?: number | null;
  sheet_no?: string | null;
  notes?: string | null;
}

function toBase64(buf: Uint8Array | ArrayBuffer): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

/**
 * Accurately reads page count from PDF using pdf-lib (with regex fallback).
 */
export async function getPDFPageCount(file: File): Promise<number> {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdfDoc = await PDFDocument.load(arrayBuffer, { ignoreEncryption: true });
    return pdfDoc.getPageCount();
  } catch (err) {
    console.warn("pdf-lib page count error, using regex fallback:", err);
    try {
      const buffer = await file.arrayBuffer();
      const text = new TextDecoder("latin1").decode(buffer);
      const matches = text.match(/\/Type\s*\/Page\b/g);
      if (matches && matches.length > 0) return matches.length;
    } catch {}
    return 1;
  }
}

/**
 * Extracts a subset of pages if manual page selection is chosen.
 */
export async function extractPDFPages(file: File, pageIndices0Based: number[]): Promise<Uint8Array> {
  const arrayBuffer = await file.arrayBuffer();
  const srcDoc = await PDFDocument.load(arrayBuffer, { ignoreEncryption: true });
  const total = srcDoc.getPageCount();
  const validIndices = pageIndices0Based.filter((i) => i >= 0 && i < total);
  if (validIndices.length === 0 || validIndices.length === total) {
    return new Uint8Array(arrayBuffer);
  }
  const destDoc = await PDFDocument.create();
  const copied = await destDoc.copyPages(srcDoc, validIndices);
  copied.forEach((p) => destDoc.addPage(p));
  return await destDoc.save();
}

/**
 * Client-side extraction with AI Structural Page Classification + BOQ Takeoff.
 * Calls Gemini directly from the browser with no page restrictions.
 */
export async function extractBOQ(
  file: File,
  apiKey: string,
  selectedPages0Based?: number[],
  requestedModel = "gemini-3.8-flash"
) {
  const startTime = Date.now();

  let pdfBytes: Uint8Array;
  if (selectedPages0Based && selectedPages0Based.length > 0) {
    pdfBytes = await extractPDFPages(file, selectedPages0Based);
  } else {
    pdfBytes = new Uint8Array(await file.arrayBuffer());
  }

  const base64Data = toBase64(pdfBytes);

  const modelsToTry = [requestedModel, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"].filter(
    (m, i, arr) => arr.indexOf(m) === i
  );

  let lastError: { message?: string } | null = null;
  let responseText = "";
  let successfulModel = requestedModel;

  for (const model of modelsToTry) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [
          {
            parts: [
              { inlineData: { mimeType: "application/pdf", data: base64Data } },
              { text: EXTRACTION_PROMPT },
            ],
          },
        ],
        generationConfig: { responseMimeType: "application/json", temperature: 0.0 },
      }),
    });

    if (res.ok) {
      const data = await res.json();
      responseText = data?.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
      successfulModel = model;
      lastError = null;
      break;
    }
    const errorData = await res.json().catch(() => ({}));
    lastError = errorData?.error || { message: `HTTP ${res.status}: ${res.statusText}` };
    if (res.status === 400 || res.status === 403) {
      throw new Error(lastError?.message || "API Key ไม่ถูกต้อง หรือไม่มีสิทธิ์เข้าถึง");
    }
  }

  if (lastError && !responseText) {
    throw new Error(lastError.message || "ไม่สามารถเชื่อมต่อ Gemini Vision API ได้");
  }

  let clean = responseText.trim();
  if (clean.startsWith("```")) {
    clean = clean.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "").trim();
  }

  let parsedResponse: any = null;
  try {
    parsedResponse = JSON.parse(clean);
  } catch {
    throw new Error("โมเดลส่งผลลัพธ์ที่แปลงเป็น JSON ไม่สมบูรณ์ กรุณาลองใหม่อีกครั้ง");
  }

  // Handle both { page_analysis, items } object and direct array format
  let rawItems: RawBOQItem[] = [];
  let pageAnalysis: PageAnalysis[] = [];
  let structuralPages: number[] = [];

  if (Array.isArray(parsedResponse)) {
    rawItems = parsedResponse;
  } else if (parsedResponse && typeof parsedResponse === "object") {
    rawItems = Array.isArray(parsedResponse.items) ? parsedResponse.items : [];
    pageAnalysis = Array.isArray(parsedResponse.page_analysis) ? parsedResponse.page_analysis : [];
    structuralPages = Array.isArray(parsedResponse.structural_pages)
      ? parsedResponse.structural_pages
      : pageAnalysis.filter((p) => p.is_structural).map((p) => p.page_number);
  }

  const rows: ExtractedBOQItem[] = rawItems.map((item) => {
    const section = String(item.section || "").trim();
    const length_mm =
      item.length_mm != null && !isNaN(Number(item.length_mm)) ? Number(item.length_mm) : null;
    const quantity =
      item.quantity != null && !isNaN(Number(item.quantity)) ? Number(item.quantity) : null;
    const unit_weight_kg_m =
      item.unit_weight_kg_m != null && !isNaN(Number(item.unit_weight_kg_m))
        ? Number(item.unit_weight_kg_m)
        : calculateUnitWeight(section);

    const source_page =
      item.source_page != null && !isNaN(Number(item.source_page)) ? Number(item.source_page) : null;

    return {
      member_id: String(item.member_id || "").trim() || "—",
      section: section || "—",
      length_mm,
      quantity,
      unit_weight_kg_m,
      source_page,
      sheet_no: item.sheet_no ? String(item.sheet_no).trim() : null,
      notes: String(item.notes || "").trim(),
    };
  });

  return {
    success: true as const,
    rows,
    page_analysis: pageAnalysis,
    structural_pages: structuralPages,
    model: successfulModel,
    latency_s: Math.round(((Date.now() - startTime) / 1000) * 10) / 10,
    count: rows.length,
  };
}
