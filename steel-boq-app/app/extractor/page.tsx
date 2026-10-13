"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { extractBOQ } from "@/lib/extract-client";
import {
  Upload,
  FileText,
  Cpu,
  Download,
  Clock,
  Users,
  Package,
  Weight,
  Eye,
  X,
  Loader2,
  Info,
  ArrowLeft,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Key,
  CheckCircle2,
} from "lucide-react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/ui/navbar";

// ─── Types ───────────────────────────────────────────────
interface BOQRow {
  member_id: string;
  section: string;
  length_mm: number | null;
  quantity: number | null;
  unit_weight_kg_m: number | null;
  notes: string;
}

interface ExtractionResult {
  latency_s: number;
  log_file: string;
  model: string;
  pages: number[];
  dpi: number;
  rows: BOQRow[];
}

// ─── Demo Data ───────────────────────────────────────────
const DEMO_ROWS: BOQRow[] = [
  { member_id: "B1",    section: "H-300x150x6.5x9",  length_mm: 6000, quantity: 8,  unit_weight_kg_m: 36.7,  notes: "" },
  { member_id: "B2",    section: "H-400x200x8x13",   length_mm: 7500, quantity: 4,  unit_weight_kg_m: 66.7,  notes: "" },
  { member_id: "B3",    section: "H-250x125x6x9",    length_mm: 4500, quantity: 6,  unit_weight_kg_m: 29.5,  notes: "" },
  { member_id: "GB-01", section: "H-500x200x10x16",  length_mm: 9000, quantity: 2,  unit_weight_kg_m: 100.2, notes: "GRADE BEAM" },
  { member_id: "C1",    section: "H-300x300x10x15",  length_mm: 3600, quantity: 6,  unit_weight_kg_m: 92.4,  notes: "" },
  { member_id: "C2",    section: "H-250x250x9x14",   length_mm: 3600, quantity: 4,  unit_weight_kg_m: 72.4,  notes: "" },
  { member_id: "CH-1",  section: "[200x80x7.5x11",   length_mm: 3000, quantity: 10, unit_weight_kg_m: null,  notes: "PURLIN; วงเล็บปิดหาย" },
  { member_id: "CH-2",  section: "[250x90x9x13",     length_mm: null, quantity: 6,  unit_weight_kg_m: null,  notes: "LENGTH TBC; วงเล็บปิดหาย" },
  { member_id: "BR-1",  section: "L90x90x7",         length_mm: 4243, quantity: 8,  unit_weight_kg_m: null,  notes: "BRACE" },
  { member_id: "P1",    section: "W12x26",            length_mm: 4200, quantity: 3,  unit_weight_kg_m: 38.7,  notes: "IMPERIAL" },
  { member_id: "B4",    section: "H-350x175x7x11",   length_mm: null, quantity: 2,  unit_weight_kg_m: 49.9,  notes: "length 'SEE PLAN'" },
  { member_id: "X1",    section: "H-200x100x5.5x8",  length_mm: 2800, quantity: 1,  unit_weight_kg_m: 21.9,  notes: "แถวตัวอักษรเล็กจางในต้นฉบับ" },
];

const DEMO_RESULT: ExtractionResult = {
  latency_s: 6.4,
  log_file: "20260909_120000.json",
  model: "gemini-3.8-flash",
  pages: [0, 1],
  dpi: 220,
  rows: DEMO_ROWS,
};

// ─── Helpers ─────────────────────────────────────────────
function calcStats(rows: BOQRow[]) {
  const distinctMembers = new Set(rows.map((r) => r.member_id)).size;
  const totalQty = rows.reduce((s, r) => s + (r.quantity ?? 0), 0);
  const totalWeightKg = rows.reduce((s, r) => {
    if (r.quantity && r.length_mm && r.unit_weight_kg_m)
      return s + (r.quantity * r.length_mm * r.unit_weight_kg_m) / 1000;
    return s;
  }, 0);
  const needsReview = rows.filter(
    (r) => r.length_mm === null || r.unit_weight_kg_m === null || r.section.startsWith("[")
  ).length;
  return { distinctMembers, totalQty, totalWeightKg, needsReview };
}

// ─── Main page ───────────────────────────────────────────
export default function ExtractorPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [pages, setPages] = useState(3);
  const [selectedPages, setSelectedPages] = useState([true, true, false]);
  const [dpi, setDpi] = useState(220);

  const [status, setStatus] = useState<"idle" | "extracting" | "done" | "demo">("idle");
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [rows, setRows] = useState<BOQRow[]>([]);
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null);

  // Gemini API Key state
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractStep, setExtractStep] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("gemini_api_key");
    if (saved) setApiKey(saved);
  }, []);

  const handleSaveApiKey = (val: string) => {
    setApiKey(val);
    if (val.trim()) {
      localStorage.setItem("gemini_api_key", val.trim());
    } else {
      localStorage.removeItem("gemini_api_key");
    }
  };

  const handleFile = (f: File) => {
    setFile(f);
    setStatus("idle");
    setResult(null);
    setRows([]);
    setExtractError(null);
    setPages(3);
    setSelectedPages([true, true, false]);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") handleFile(f);
  }, []);

  const togglePage = (i: number) =>
    setSelectedPages((prev) => prev.map((v, idx) => (idx === i ? !v : v)));

  const handleExtract = async () => {
    if (!file) return;
    setExtractError(null);

    // If no key entered, prompt or fallback to demo
    if (!apiKey.trim()) {
      setStatus("extracting");
      setExtractStep("จำลองการวิเคราะห์ (ไม่มี API Key — กำลังโหลด Mock Data)...");
      await new Promise((r) => setTimeout(r, 1400));
      setStatus("demo");
      setResult(DEMO_RESULT);
      setRows(DEMO_ROWS);
      return;
    }

    try {
      setStatus("extracting");
      setExtractStep("กำลังส่งแบบแปลน PDF ไปยัง Gemini 3.8 Flash...");

      const data = await extractBOQ(file, apiKey.trim(), "gemini-3.8-flash");

      setResult({
        latency_s: data.latency_s,
        log_file: `${Date.now()}.json`,
        model: data.model,
        pages: selectedPages.map((s, idx) => (s ? idx : -1)).filter((idx) => idx >= 0),
        dpi,
        rows: data.rows,
      });
      setRows(data.rows);
      setStatus("done");
    } catch (err: any) {
      console.error("Extraction error:", err);
      setExtractError(err.message || "เกิดข้อผิดพลาดในการวิเคราะห์แบบด้วย Gemini");
      setStatus("idle");
    }
  };

  const updateCell = (rowIdx: number, col: keyof BOQRow, value: string) => {
    setRows((prev) =>
      prev.map((r, i) => {
        if (i !== rowIdx) return r;
        const numCols = ["length_mm", "quantity", "unit_weight_kg_m"] as const;
        if ((numCols as readonly string[]).includes(col)) {
          const parsed = value === "" || value === "—" ? null : parseFloat(value);
          return { ...r, [col]: isNaN(parsed as number) ? null : parsed };
        }
        return { ...r, [col]: value };
      })
    );
  };

  const handleDownloadCSV = () => {
    const header = "member_id,section,length_mm,quantity,unit_weight_kg_m,notes";
    const csvRows = rows.map((r) =>
      [r.member_id, r.section, r.length_mm ?? "", r.quantity ?? "", r.unit_weight_kg_m ?? "", `"${r.notes}"`].join(",")
    );
    const blob = new Blob([[header, ...csvRows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `boq_${file?.name.replace(".pdf", "") ?? "export"}_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const stats = rows.length > 0 ? calcStats(rows) : null;
  const selectedCount = selectedPages.filter(Boolean).length;

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <Navbar />

      {/* ── Page hero band ── */}
      <div className="relative pt-24 pb-12 px-6 overflow-hidden border-b border-white/5">
        {/* Grid bg — same as home hero */}
        <div
          className="absolute inset-0 opacity-15 pointer-events-none"
          style={{
            backgroundImage: `
              linear-gradient(rgba(88,166,255,0.08) 1px, transparent 1px),
              linear-gradient(90deg, rgba(88,166,255,0.08) 1px, transparent 1px)
            `,
            backgroundSize: "48px 48px",
          }}
        />
        {/* Radial glow */}
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] opacity-10 pointer-events-none"
          style={{
            background: "radial-gradient(circle, hsl(210,100%,55%) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />

        <div className="relative max-w-5xl mx-auto">
          {/* Breadcrumb */}
          <button
            onClick={() => router.push("/")}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-400 transition-colors mb-6"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to home
          </button>

          <div className="flex items-start justify-between gap-6 flex-wrap">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-xs font-medium mb-4">
                <Sparkles className="w-3 h-3" />
                Gemini 2.5 Flash Vision
              </div>
              <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-2">
                BOQ Extractor
              </h1>
              <p className="text-gray-400 text-sm max-w-xl leading-relaxed">
                อัปโหลดแบบเหล็กโครงสร้าง (CAD-exported PDF) — Gemini Vision จะสกัดรายการชิ้นส่วนทั้งหมด
                ออกมาเป็นตาราง BOQ ที่แก้ไขได้ทันที
              </p>
            </div>

            {rows.length > 0 && (
              <button
                onClick={handleDownloadCSV}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 hover:-translate-y-0.5"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Main content ── */}
      <main className="max-w-5xl mx-auto px-6 py-10 space-y-8">

        {/* ── Upload + Options ── */}
        <div className="grid grid-cols-1 md:grid-cols-[1.3fr_0.7fr] gap-5">

          {/* Drop zone — glass card */}
          <div
            className={`rounded-2xl border bg-white/3 backdrop-blur-sm transition-all cursor-pointer group ${
              file
                ? "border-blue-500/30 hover:border-blue-500/50"
                : "border-dashed border-white/12 hover:border-blue-500/40 hover:bg-blue-500/5"
            }`}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />

            <div className="p-6">
              {file ? (
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-blue-500/15 border border-blue-500/25 flex items-center justify-center shrink-0">
                    <FileText className="w-6 h-6 text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-sm text-white truncate">{file.name}</div>
                    <div className="text-xs text-gray-500 font-mono mt-0.5">
                      {pages} หน้า · {(file.size / 1024).toFixed(0)} KB · อัปโหลดแล้ว
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null); setStatus("idle"); setRows([]); setResult(null); }}
                    className="p-1.5 rounded-lg hover:bg-white/10 text-gray-600 hover:text-gray-300 transition-all shrink-0"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-center gap-3">
                  <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:border-blue-500/30 group-hover:bg-blue-500/8 transition-all">
                    <Upload className="w-7 h-7 text-gray-600 group-hover:text-blue-400 transition-colors" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
                      วาง PDF ที่นี่ หรือ <span className="text-blue-400">คลิกเพื่อเลือกไฟล์</span>
                    </p>
                    <p className="text-xs text-gray-600 mt-1">CAD-exported PDF เท่านั้น · สูงสุด 10 หน้า</p>
                  </div>
                </div>
              )}
            </div>

            {/* Page selector */}
            {file && (
              <div className="px-6 pb-6">
                <p className="text-[10px] font-mono uppercase tracking-wider text-gray-600 mb-3">เลือกหน้าที่จะสกัด</p>
                <div className="flex gap-2 flex-wrap">
                  {Array.from({ length: pages }).map((_, i) => (
                    <button
                      key={i}
                      onClick={(e) => { e.stopPropagation(); togglePage(i); }}
                      className={`w-12 h-16 rounded-xl border text-xs font-mono flex flex-col items-center justify-center gap-1 transition-all ${
                        selectedPages[i]
                          ? "border-blue-400 text-blue-300 bg-blue-500/15 shadow-[0_0_0_1px_rgba(88,166,255,0.3)]"
                          : "border-white/8 text-gray-600 hover:border-white/20 hover:text-gray-400"
                      }`}
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>p{i + 1}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Options panel — glass card */}
          <div className="rounded-2xl border border-white/8 bg-white/3 backdrop-blur-sm p-6 flex flex-col gap-5">
            <div>
              <p className="text-[10px] font-mono uppercase tracking-wider text-gray-600 mb-3">การตั้งค่า</p>
              <div className="space-y-4">
                {/* Gemini API Key */}
                <div className="space-y-1.5">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-400 flex items-center gap-1.5 font-medium">
                      <Key className="w-3.5 h-3.5 text-blue-400" />
                      Gemini API Key
                    </span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center gap-1 ${
                        apiKey.trim()
                          ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/25"
                          : "text-amber-400 bg-amber-500/10 border border-amber-500/25"
                      }`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${apiKey.trim() ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
                      {apiKey.trim() ? "พร้อมใช้งาน" : "ใช้ Demo"}
                    </span>
                  </div>
                  <div className="relative">
                    <input
                      type={showKey ? "text" : "password"}
                      value={apiKey}
                      onChange={(e) => handleSaveApiKey(e.target.value)}
                      placeholder="AIzaSy... (คีย์ของคุณ)"
                      className="w-full bg-white/5 border border-white/10 focus:border-blue-500/50 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-600 outline-none pr-9 font-mono transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                      title={showKey ? "ซ่อนคีย์" : "แสดงคีย์"}
                    >
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <p className="text-[10px] text-gray-600">
                    {apiKey.trim() ? "✓ บันทึกในเบราว์เซอร์อัตโนมัติ" : "ใส่ Key เพื่อเชื่อมต่อ AI จริง หรือกด Extract เพื่อทดสอบ Demo"}
                  </p>
                </div>

                <div className="flex justify-between items-center pt-1 border-t border-white/5">
                  <span className="text-xs text-gray-500">โมเดล AI</span>
                  <span className="text-xs font-mono text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-md">
                    gemini-3.8-flash
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">DPI เรนเดอร์</span>
                    <span className="text-xs font-mono text-white">{dpi}</span>
                  </div>
                  <input
                    type="range" min={100} max={300} step={20} value={dpi}
                    onChange={(e) => setDpi(Number(e.target.value))}
                    className="w-full h-1.5 rounded-full accent-blue-500 cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-gray-600">
                    <span>100 (เร็ว)</span>
                    <span>300 (คมชัด)</span>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">หน้าที่เลือก</span>
                  <span className="text-xs font-mono text-white">{selectedCount} / {pages}</span>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-2 space-y-2">
              <button
                onClick={handleExtract}
                disabled={!file || status === "extracting"}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 hover:-translate-y-0.5 disabled:hover:translate-y-0"
              >
                {status === "extracting" ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />กำลังวิเคราะห์แบบ...</>
                ) : (
                  <><Cpu className="w-4 h-4" />{apiKey.trim() ? "Extract with Gemini" : "Extract BOQ (Demo)"}</>
                )}
              </button>
              {status === "extracting" && extractStep && (
                <p className="text-center text-xs text-blue-400 animate-pulse">{extractStep}</p>
              )}
              {!file && status !== "extracting" && (
                <p className="text-center text-[10px] text-gray-600">อัปโหลด PDF ก่อนเริ่มสกัด</p>
              )}
            </div>
          </div>
        </div>

        {/* ── Error banner ── */}
        {extractError && (
          <div className="flex items-start gap-3 p-4 rounded-xl border border-red-500/25 bg-red-500/10 backdrop-blur-sm">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="text-sm flex-1">
              <span className="font-semibold text-red-300">เกิดข้อผิดพลาดในการดึงข้อมูล</span>
              <p className="text-red-300/80 text-xs mt-1">{extractError}</p>
              <p className="text-[11px] text-red-400/60 mt-1.5">
                ข้อแนะนำ: ตรวจสอบว่า Gemini API Key ถูกต้อง และเปิดใช้งานใน Google AI Studio เรียบร้อยแล้ว
              </p>
            </div>
            <button
              onClick={() => setExtractError(null)}
              className="text-red-400 hover:text-red-200 text-xs"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Real extraction success banner ── */}
        {status === "done" && result && (
          <div className="flex items-center gap-3 p-4 rounded-xl border border-emerald-500/25 bg-emerald-500/10 backdrop-blur-sm">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div className="text-sm flex-1">
              <span className="font-semibold text-emerald-300">วิเคราะห์แบบสำเร็จด้วย Gemini API จริง!</span>
              <span className="text-emerald-400/80 ml-2 text-xs">
                โมเดล: {result.model} · เวลาประมวลผล: {result.latency_s} วินาที · สกัดได้ {rows.length} รายการ
              </span>
            </div>
          </div>
        )}

        {/* ── Demo mode banner ── */}
        {status === "demo" && (
          <div className="flex items-start gap-3 p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5 backdrop-blur-sm">
            <Info className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
            <div className="text-sm flex-1">
              <span className="font-semibold text-yellow-300">Demo Mode</span>
              <span className="text-yellow-400/70 ml-2 text-xs">
                กำลังแสดงผลด้วยข้อมูลตัวอย่าง (หากต้องการใช้ AI ถอดจากแบบจริง ให้ใส่ Gemini API Key ในช่องด้านบน)
              </span>
            </div>
          </div>
        )}

        {/* ── Empty state ── */}
        {status === "idle" && !file && (
          <div className="rounded-2xl border border-dashed border-white/8 bg-white/2 p-16 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/8 flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-gray-700" />
            </div>
            <p className="text-gray-500 text-sm font-medium mb-1">ยังไม่มีไฟล์</p>
            <p className="text-gray-700 text-xs">อัปโหลด PDF แบบเหล็กเพื่อเริ่มสกัด BOQ</p>
          </div>
        )}

        {status === "idle" && file && !result && (
          <div className="rounded-2xl border border-dashed border-blue-500/15 bg-blue-500/3 p-16 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4">
              <Cpu className="w-8 h-8 text-blue-500/50" />
            </div>
            <p className="text-gray-400 text-sm font-medium mb-1">พร้อมสกัด</p>
            <p className="text-gray-600 text-xs">
              กด <span className="text-blue-400 font-semibold">Extract BOQ</span> เพื่อให้ Gemini Vision วิเคราะห์แบบ
            </p>
          </div>
        )}

        {/* ── Results ── */}
        {result && (
          <div className="space-y-6">
            {/* Results header */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <h2 className="text-lg font-bold text-white">ผลการสกัดข้อมูล</h2>
                <p className="text-xs text-gray-500 mt-0.5">แก้ไขค่าในตารางได้โดยตรงก่อน export</p>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono text-gray-600">
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-blue-500/60" />
                  {result.latency_s}s
                </span>
                <span className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-blue-500/60" />
                  {result.log_file}
                </span>
              </div>
            </div>

            {/* ── Stat tiles — same glass style as home ── */}
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  {
                    label: "Distinct Members",
                    value: stats.distinctMembers,
                    unit: "",
                    icon: <Users className="w-4 h-4" />,
                    color: "from-blue-600 to-blue-400",
                    textColor: "text-blue-400",
                    borderColor: "border-blue-500/20",
                    bgColor: "bg-blue-500/8",
                  },
                  {
                    label: "Total Quantity",
                    value: stats.totalQty,
                    unit: "pcs",
                    icon: <Package className="w-4 h-4" />,
                    color: "from-cyan-600 to-cyan-400",
                    textColor: "text-cyan-400",
                    borderColor: "border-cyan-500/20",
                    bgColor: "bg-cyan-500/8",
                  },
                  {
                    label: "Total Weight",
                    value: `${(stats.totalWeightKg / 1000).toFixed(2)}`,
                    unit: "t",
                    icon: <Weight className="w-4 h-4" />,
                    color: "from-green-600 to-green-400",
                    textColor: "text-green-400",
                    borderColor: "border-green-500/20",
                    bgColor: "bg-green-500/8",
                  },
                  {
                    label: "Needs Review",
                    value: stats.needsReview,
                    unit: "",
                    icon: <AlertCircle className="w-4 h-4" />,
                    color: stats.needsReview > 0 ? "from-yellow-600 to-yellow-400" : "from-gray-600 to-gray-400",
                    textColor: stats.needsReview > 0 ? "text-yellow-400" : "text-gray-500",
                    borderColor: stats.needsReview > 0 ? "border-yellow-500/20" : "border-white/8",
                    bgColor: stats.needsReview > 0 ? "bg-yellow-500/8" : "bg-white/3",
                  },
                ].map((s) => (
                  <div
                    key={s.label}
                    className={`rounded-2xl border ${s.borderColor} ${s.bgColor} backdrop-blur-sm p-5`}
                  >
                    <div className={`flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider mb-3 ${s.textColor}`}>
                      {s.icon}
                      <span className="text-gray-600">{s.label}</span>
                    </div>
                    <div className={`text-3xl font-bold tabular-nums ${s.textColor}`}>
                      {s.value}
                      {s.unit && (
                        <span className="text-base font-normal text-gray-600 ml-1">{s.unit}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* ── BOQ Table — glass style ── */}
            <div className="rounded-2xl border border-white/8 overflow-hidden bg-[#0d1117]">
              {/* Table header bar */}
              <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/8 bg-white/2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500/60" />
                  <div className="w-2 h-2 rounded-full bg-yellow-500/60" />
                  <div className="w-2 h-2 rounded-full bg-green-500/60" />
                  <span className="ml-3 text-xs font-mono text-gray-600">boq_result · {rows.length} rows</span>
                </div>
                <span className="text-[10px] text-gray-600 font-mono">คลิก cell เพื่อแก้ไข</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[700px]">
                  <thead>
                    <tr className="border-b border-white/5 bg-white/2">
                      {[
                        { label: "Member ID", align: "left" },
                        { label: "Section", align: "left" },
                        { label: "Length (mm)", align: "right" },
                        { label: "Qty", align: "right" },
                        { label: "Unit wt (kg/m)", align: "right" },
                        { label: "Notes", align: "left" },
                      ].map((h) => (
                        <th
                          key={h.label}
                          className={`px-5 py-3 text-[10px] font-mono uppercase tracking-wider text-gray-600 font-medium ${
                            h.align === "right" ? "text-right" : "text-left"
                          }`}
                        >
                          {h.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, ri) => {
                      const flagged =
                        row.length_mm === null ||
                        row.unit_weight_kg_m === null ||
                        row.section.startsWith("[");
                      return (
                        <tr
                          key={ri}
                          className={`border-b border-white/4 transition-colors hover:bg-white/2 ${
                            flagged ? "bg-yellow-500/2" : ""
                          }`}
                        >
                          <EditableCell
                            value={row.member_id}
                            isEditing={editingCell?.row === ri && editingCell?.col === "member_id"}
                            onClick={() => setEditingCell({ row: ri, col: "member_id" })}
                            onBlur={(v) => { updateCell(ri, "member_id", v); setEditingCell(null); }}
                            className="font-bold text-blue-400 font-mono text-xs"
                          />
                          <EditableCell
                            value={row.section}
                            isEditing={editingCell?.row === ri && editingCell?.col === "section"}
                            onClick={() => setEditingCell({ row: ri, col: "section" })}
                            onBlur={(v) => { updateCell(ri, "section", v); setEditingCell(null); }}
                            className={`font-mono text-xs ${row.section.startsWith("[") ? "text-yellow-400" : "text-gray-300"}`}
                          />
                          <EditableCell
                            value={row.length_mm !== null ? row.length_mm.toLocaleString() : ""}
                            isEditing={editingCell?.row === ri && editingCell?.col === "length_mm"}
                            onClick={() => setEditingCell({ row: ri, col: "length_mm" })}
                            onBlur={(v) => { updateCell(ri, "length_mm", v); setEditingCell(null); }}
                            className="text-right font-mono text-xs tabular-nums text-gray-300"
                            isNull={row.length_mm === null}
                            align="right"
                          />
                          <EditableCell
                            value={row.quantity !== null ? String(row.quantity) : ""}
                            isEditing={editingCell?.row === ri && editingCell?.col === "quantity"}
                            onClick={() => setEditingCell({ row: ri, col: "quantity" })}
                            onBlur={(v) => { updateCell(ri, "quantity", v); setEditingCell(null); }}
                            className="text-right font-mono text-xs tabular-nums text-gray-300"
                            isNull={row.quantity === null}
                            align="right"
                          />
                          <EditableCell
                            value={row.unit_weight_kg_m !== null ? row.unit_weight_kg_m.toFixed(1) : ""}
                            isEditing={editingCell?.row === ri && editingCell?.col === "unit_weight_kg_m"}
                            onClick={() => setEditingCell({ row: ri, col: "unit_weight_kg_m" })}
                            onBlur={(v) => { updateCell(ri, "unit_weight_kg_m", v); setEditingCell(null); }}
                            className={`text-right font-mono text-xs tabular-nums ${row.unit_weight_kg_m !== null ? "text-green-400" : ""}`}
                            isNull={row.unit_weight_kg_m === null}
                            align="right"
                          />
                          <EditableCell
                            value={row.notes}
                            isEditing={editingCell?.row === ri && editingCell?.col === "notes"}
                            onClick={() => setEditingCell({ row: ri, col: "notes" })}
                            onBlur={(v) => { updateCell(ri, "notes", v); setEditingCell(null); }}
                            className="text-gray-500 text-xs max-w-[180px] truncate"
                          />
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Table footer */}
              <div className="flex items-center justify-between px-5 py-3 border-t border-white/5 bg-white/2">
                <span className="text-xs font-mono text-gray-600">
                  {stats?.distinctMembers} members · {stats?.totalQty} pcs total
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-600">
                    Extracted in {result.latency_s}s
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                </div>
              </div>
            </div>

            {/* Export CTA */}
            <div className="flex items-center justify-between p-5 rounded-2xl border border-white/8 bg-white/2">
              <div>
                <p className="text-sm font-medium text-white">พร้อม Export</p>
                <p className="text-xs text-gray-500 mt-0.5">ดาวน์โหลด BOQ ที่แก้ไขแล้วเป็นไฟล์ CSV</p>
              </div>
              <button
                onClick={handleDownloadCSV}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 hover:-translate-y-0.5"
              >
                <Download className="w-4 h-4" />
                Download CSV
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ─── Editable Cell ────────────────────────────────────────
function EditableCell({
  value,
  isEditing,
  onClick,
  onBlur,
  className = "",
  isNull = false,
  align = "left",
}: {
  value: string;
  isEditing: boolean;
  onClick: () => void;
  onBlur: (v: string) => void;
  className?: string;
  isNull?: boolean;
  align?: "left" | "right";
}) {
  return (
    <td
      className={`px-5 py-3 cursor-text ${className}`}
      onClick={onClick}
    >
      {isEditing ? (
        <input
          autoFocus
          defaultValue={value}
          onBlur={(e) => onBlur(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          className={`bg-blue-500/15 border border-blue-500/50 rounded-lg px-2 py-1 text-white text-xs font-mono outline-none w-full min-w-[60px] ${
            align === "right" ? "text-right" : "text-left"
          }`}
        />
      ) : isNull ? (
        <span className="text-gray-700 italic text-xs">null</span>
      ) : (
        <span className="hover:text-white transition-colors">{value || "—"}</span>
      )}
    </td>
  );
}
