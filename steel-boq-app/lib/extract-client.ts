import { calculateUnitWeight } from "@/lib/boq-calc";

const EXTRACTION_PROMPT = `You are reading a structural steel drawing (framing plan or member schedule).
Extract every distinct steel member you can identify. For each member, return:
- member_id: the label/tag shown on the drawing (e.g. B1, C2, GB-01)
- section: the section designation (e.g. H-300x300x10x15, W12x26)
- length_mm: member length in millimeters if shown or derivable from dimensions
- quantity: number of instances of this member type
- notes: anything ambiguous, illegible, or inferred rather than directly read

Return ONLY a JSON array of objects with these exact keys. No prose, no markdown
fences, no explanation. If a value cannot be determined, use null for that field
and explain briefly in notes.`;

interface RawBOQItem {
  member_id?: string | null;
  section?: string | null;
  length_mm?: number | string | null;
  quantity?: number | string | null;
  unit_weight_kg_m?: number | string | null;
  notes?: string | null;
}

function toBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

/**
 * Client-side extraction (static hosting such as GitHub Pages has no server).
 * Calls the Gemini API directly from the browser using the user's own key.
 */
export async function extractBOQ(file: File, apiKey: string, requestedModel = "gemini-3.8-flash") {
  const startTime = Date.now();
  const base64Data = toBase64(await file.arrayBuffer());

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
      responseText = data?.candidates?.[0]?.content?.parts?.[0]?.text || "[]";
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

  let items: RawBOQItem[] = [];
  try {
    items = JSON.parse(clean);
    if (!Array.isArray(items)) items = [];
  } catch {
    throw new Error("โมเดลส่งผลลัพธ์ที่แปลงเป็น JSON ไม่สมบูรณ์ กรุณาลองใหม่อีกครั้ง");
  }

  const rows = items.map((item) => {
    const section = String(item.section || "").trim();
    const length_mm =
      item.length_mm != null && !isNaN(Number(item.length_mm)) ? Number(item.length_mm) : null;
    const quantity =
      item.quantity != null && !isNaN(Number(item.quantity)) ? Number(item.quantity) : null;
    const unit_weight_kg_m =
      item.unit_weight_kg_m != null && !isNaN(Number(item.unit_weight_kg_m))
        ? Number(item.unit_weight_kg_m)
        : calculateUnitWeight(section);
    return {
      member_id: String(item.member_id || "").trim() || "—",
      section: section || "—",
      length_mm,
      quantity,
      unit_weight_kg_m,
      notes: String(item.notes || "").trim(),
    };
  });

  return {
    success: true as const,
    rows,
    model: successfulModel,
    latency_s: Math.round(((Date.now() - startTime) / 1000) * 10) / 10,
    count: rows.length,
  };
}
