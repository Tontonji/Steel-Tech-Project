"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { extractBOQ, getPDFPageCount, PageAnalysis, ExtractedBOQItem } from "@/lib/extract-client";
import { calculateUnitWeight, inferMissingLengths } from "@/lib/boq-calc";
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
  Filter,
  Layers,
  CheckSquare,
  Square,
} from "lucide-react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/ui/navbar";

// ─── Types ───────────────────────────────────────────────
export interface BOQRow {
  member_id: string;
  section: string;
  length_mm: number | null;
  quantity: number | null;
  unit_weight_kg_m: number | null;
  source_page?: number | null;
  sheet_no?: string | null;
  notes: string;
}

interface ExtractionResult {
  latency_s: number;
  log_file: string;
  model: string;
  pages: number[];
  dpi: number;
  rows: BOQRow[];
  page_analysis?: PageAnalysis[];
  structural_pages?: number[];
}

// ─── Demo Data ───────────────────────────────────────────
const DEMO_PAGE_ANALYSIS: PageAnalysis[] = [
  { page_number: 1, sheet_no: "A-01", sheet_name: "ผังบริเวณและสารบัญแบบ", is_structural: false, category: "ARCHITECTURAL", summary: "สารบัญแบบและแผนที่ตั้ง (ไม่ใช่แบบโครงสร้าง)" },
  { page_number: 2, sheet_no: "A-02", sheet_name: "แปลนพื้นสถาปัตยกรรม", is_structural: false, category: "ARCHITECTURAL", summary: "แปลนสถาปัตย์แสดงห้องและระยะผนัง (ไม่ใช่แบบโครงสร้าง)" },
  { page_number: 3, sheet_no: "A-03", sheet_name: "รูปด้านและรูปตัด", is_structural: false, category: "ARCHITECTURAL", summary: "รูปด้านอาคาร (ไม่ใช่แบบโครงสร้าง)" },
  { page_number: 4, sheet_no: "S-01", sheet_name: "แปลนฐานรากและคานคอดิน", is_structural: true, category: "STRUCTURAL", summary: "แปลนคานคอดิน GB และเสาตอม่อ C" },
  { page_number: 5, sheet_no: "S-02", sheet_name: "แปลนคานชั้น 2", is_structural: true, category: "STRUCTURAL", summary: "แปลนโครงสร้างคานเหล็ก H-Beam B1, B2" },
  { page_number: 6, sheet_no: "S-03", sheet_name: "แปลนโครงสร้างหลังคาเหล็ก", is_structural: true, category: "STRUCTURAL", summary: "แปลนจันทัน แป C-Channel และโครงถักหลังคา" },
  { page_number: 7, sheet_no: "S-04", sheet_name: "ตารางรายการเหล็กโครงสร้าง", is_structural: true, category: "STRUCTURAL", summary: "Member Schedule ตารางรายการเหล็กรูปพรรณและสเปกชิ้นส่วน" },
];

const DEMO_ROWS: BOQRow[] = [
  { member_id: "B1",    section: "H-300x150x6.5x9",  length_mm: 6000, quantity: 8,  unit_weight_kg_m: 36.7,  source_page: 5, sheet_no: "S-02", notes: "แปลนคานชั้น 2" },
  { member_id: "B2",    section: "H-400x200x8x13",   length_mm: 7500, quantity: 4,  unit_weight_kg_m: 66.7,  source_page: 5, sheet_no: "S-02", notes: "แปลนคานชั้น 2" },
  { member_id: "B3",    section: "H-250x125x6x9",    length_mm: 4500, quantity: 6,  unit_weight_kg_m: 29.5,  source_page: 6, sheet_no: "S-03", notes: "แปลนโครงหลังคา" },
  { member_id: "GB-01", section: "H-500x200x10x16",  length_mm: 9000, quantity: 2,  unit_weight_kg_m: 100.2, source_page: 4, sheet_no: "S-01", notes: "GRADE BEAM" },
  { member_id: "C1",    section: "H-300x300x10x15",  length_mm: 3600, quantity: 6,  unit_weight_kg_m: 92.4,  source_page: 7, sheet_no: "S-04", notes: "ตารางเสาโครงสร้าง" },
  { member_id: "C2",    section: "H-250x250x9x14",   length_mm: 3600, quantity: 4,  unit_weight_kg_m: 72.4,  source_page: 7, sheet_no: "S-04", notes: "ตารางเสาโครงสร้าง" },
  { member_id: "CH-1",  section: "[200x80x7.5x11",   length_mm: 3000, quantity: 10, unit_weight_kg_m: 24.6,  source_page: 6, sheet_no: "S-03", notes: "แปหลังคา PURLIN" },
  { member_id: "CH-2",  section: "[250x90x9x13",     length_mm: 3000, quantity: 6,  unit_weight_kg_m: 34.6,  source_page: 6, sheet_no: "S-03", notes: "[ยืมความยาวจาก CH-1 (3,000 mm)]" },
  { member_id: "BR-1",  section: "L90x90x7",         length_mm: 4243, quantity: 8,  unit_weight_kg_m: 9.5,   source_page: 6, sheet_no: "S-03", notes: "ค้ำยันหลังคา BRACE" },
  { member_id: "P1",    section: "W12x26",            length_mm: 4200, quantity: 3,  unit_weight_kg_m: 38.7,  source_page: 7, sheet_no: "S-04", notes: "IMPERIAL SECTION" },
  { member_id: "B4",    section: "H-350x175x7x11",   length_mm: 6000, quantity: 2,  unit_weight_kg_m: 49.9,  source_page: 5, sheet_no: "S-02", notes: "[ยืมความยาวจาก B1 (6,000 mm)]" },
  { member_id: "X1",    section: "H-200x100x5.5x8",  length_mm: 2800, quantity: 1,  unit_weight_kg_m: 21.9,  source_page: 6, sheet_no: "S-03", notes: "แถวตัวอักษรเล็กจางในต้นฉบับ" },
];

const DEMO_RESULT: ExtractionResult = {
  latency_s: 6.4,
  log_file: "20260909_120000.json",
  model: "gemini-3.8-flash",
  pages: [4, 5, 6, 7],
  dpi: 220,
  rows: DEMO_ROWS,
  page_analysis: DEMO_PAGE_ANALYSIS,
  structural_pages: [4, 5, 6, 7],
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
  const [pages, setPages] = useState<number>(1);
  const [isReadingPages, setIsReadingPages] = useState(false);
  const [scanMode, setScanMode] = useState<"auto" | "manual">("auto");
  const [selectedPages, setSelectedPages] = useState<boolean[]>([]);
  const [dpi, setDpi] = useState(220);

  const [status, setStatus] = useState<"idle" | "extracting" | "done" | "demo">("idle");
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [rows, setRows] = useState<BOQRow[]>([]);
  const [editingCell, setEditingCell] = useState<{ row: number; col: string } | null>(null);
  const [filterPage, setFilterPage] = useState<number | "all">("all");

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

  const handleFile = async (f: File) => {
    setFile(f);
    setStatus("idle");
    setResult(null);
    setRows([]);
    setExtractError(null);
    setFilterPage("all");
    setIsReadingPages(true);

    try {
      const detectedPages = await getPDFPageCount(f);
      setPages(detectedPages);
      setSelectedPages(new Array(detectedPages).fill(true));
    } catch {
      setPages(1);
      setSelectedPages([true]);
    } finally {
      setIsReadingPages(false);
    }
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f?.type === "application/pdf") handleFile(f);
  }, []);

  const togglePage = (i: number) =>
    setSelectedPages((prev) => prev.map((v, idx) => (idx === i ? !v : v)));

  const selectAllPages = () => setSelectedPages(new Array(pages).fill(true));
  const deselectAllPages = () => setSelectedPages(new Array(pages).fill(false));

  const handleExtract = async () => {
    if (!file) return;
    setExtractError(null);
    setFilterPage("all");

    // If no key entered, prompt or fallback to demo
    if (!apiKey.trim()) {
      setStatus("extracting");
      setExtractStep("จำลองการวิเคราะห์ (ไม่มี API Key — กำลังโหลดข้อมูลจำลองแบบโครงสร้าง)...");
      await new Promise((r) => setTimeout(r, 1400));
      setStatus("demo");
      setResult(DEMO_RESULT);
      setRows(DEMO_ROWS);
      return;
    }

    try {
      setStatus("extracting");
      const chosenIndices =
        scanMode === "manual"
          ? selectedPages.map((s, idx) => (s ? idx : -1)).filter((idx) => idx >= 0)
          : undefined; // scan all pages

      const pageCountDesc =
        chosenIndices && chosenIndices.length > 0
          ? `${chosenIndices.length} หน้าที่เลือก`
          : `ทุกหน้า (${pages} หน้า)`;

      setExtractStep(`กำลังส่งแบบแปลน PDF (${pageCountDesc}) ไปยัง Gemini 3.8 Flash...`);

      const data = await extractBOQ(file, apiKey.trim(), chosenIndices, "gemini-3.8-flash");

      setResult({
        latency_s: data.latency_s,
        log_file: `${Date.now()}.json`,
        model: data.model,
        pages: chosenIndices || Array.from({ length: pages }, (_, i) => i),
        dpi,
        rows: data.rows,
        page_analysis: data.page_analysis,
        structural_pages: data.structural_pages,
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
        const numCols = ["length_mm", "quantity", "unit_weight_kg_m", "source_page"] as const;
        if ((numCols as readonly string[]).includes(col as any)) {
          const parsed = value === "" || value === "—" ? null : parseFloat(value);
          const updated = { ...r, [col]: isNaN(parsed as number) ? null : parsed };
          if (col === "length_mm" && updated.unit_weight_kg_m === null) {
            const rewt = calculateUnitWeight(updated.section, updated.member_id, updated.length_mm);
            if (rewt !== null) updated.unit_weight_kg_m = rewt;
          }
          return updated;
        }
        const updated = { ...r, [col]: value };
        if (col === "section") {
          const rewt = calculateUnitWeight(value, updated.member_id, updated.length_mm);
          if (rewt !== null) updated.unit_weight_kg_m = rewt;
        }
        return updated;
      })
    );
  };

  const handleDownloadCSV = () => {
    const header = "member_id,section,length_mm,quantity,unit_weight_kg_m,source_page,sheet_no,notes";
    const csvRows = rows.map((r) =>
      [
        r.member_id,
        r.section,
        r.length_mm ?? "",
        r.quantity ?? "",
        r.unit_weight_kg_m ?? "",
        r.source_page ?? "",
        `"${r.sheet_no ?? ""}"`,
        `"${r.notes}"`,
      ].join(",")
    );
    const blob = new Blob([[header, ...csvRows].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `boq_${file?.name.replace(".pdf", "") ?? "export"}_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const displayedRows =
    filterPage === "all"
      ? rows
      : rows.filter((r) => r.source_page === filterPage);

  const stats = rows.length > 0 ? calcStats(rows) : null;
  const selectedCount = selectedPages.filter(Boolean).length;
  const structuralPageList = result?.structural_pages || [];

  return (
    <div className="min-h-screen bg-[#0d1117] text-[#e6edf3]">
      <Navbar />

      {/* ── Page hero band ── */}
      <div className="relative pt-24 pb-12 px-6 overflow-hidden border-b border-white/5">
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
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] opacity-10 pointer-events-none"
          style={{
            background: "radial-gradient(circle, hsl(210,100%,55%) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />

        <div className="relative max-w-5xl mx-auto">
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
                Gemini 3.8 Flash Vision · Multi-Page Classifier
              </div>
              <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-2">
                BOQ Extractor
              </h1>
              <p className="text-gray-400 text-sm max-w-xl leading-relaxed">
                อัปโหลดชุดแบบแปลน PDF ทั้งหมด (ไม่จำกัดจำนวนหน้า) — AI จะอ่านทุกหน้า คัดแยกหน้าวิศวกรรมโครงสร้าง
                ออกจากหน้าสถาปัตย์และงานระบบโดยอัตโนมัติ แล้วสกัดชิ้นส่วนเหล็กเป็นตาราง BOQ พร้อมระบุหน้าที่พบ
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
                    <div className="text-xs text-gray-400 font-mono mt-0.5 flex items-center gap-2">
                      {isReadingPages ? (
                        <span className="flex items-center gap-1 text-blue-400">
                          <Loader2 className="w-3 h-3 animate-spin" /> กำลังนับจำนวนหน้า...
                        </span>
                      ) : (
                        <span className="text-emerald-400 font-semibold">{pages} หน้า</span>
                      )}
                      <span>·</span>
                      <span>{(file.size / 1024).toFixed(0)} KB</span>
                      <span>·</span>
                      <span className="text-gray-500">อัปโหลดแล้ว</span>
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                      setStatus("idle");
                      setRows([]);
                      setResult(null);
                    }}
                    className="p-1.5 rounded-lg hover:bg-white/10 text-gray-500 hover:text-gray-300 transition-all shrink-0"
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
                    <p className="text-xs text-gray-500 mt-1">
                      รองรับชุดแบบแปลนหลายหน้า (CAD-exported PDF) · ไม่จำกัด 3 หน้า
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Scan Mode & Page selector */}
            {file && (
              <div className="px-6 pb-6 pt-2 border-t border-white/5 space-y-4">
                {/* Mode switch */}
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <p className="text-[11px] font-mono uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-blue-400" />
                    โหมดการอ่านหน้าแบบ
                  </p>
                  <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10">
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setScanMode("auto"); }}
                      className={`px-3 py-1 text-xs rounded-lg font-medium transition-all flex items-center gap-1.5 ${
                        scanMode === "auto"
                          ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      <Sparkles className="w-3 h-3 text-amber-300" />
                      อ่านทุกหน้า (AI แยกหน้าโครงสร้างอัตโนมัติ)
                    </button>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setScanMode("manual"); }}
                      className={`px-3 py-1 text-xs rounded-lg font-medium transition-all ${
                        scanMode === "manual"
                          ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                          : "text-gray-400 hover:text-white"
                      }`}
                    >
                      เลือกหน้าเอง ({selectedCount}/{pages})
                    </button>
                  </div>
                </div>

                {scanMode === "auto" ? (
                  <div className="p-3.5 rounded-xl bg-blue-500/8 border border-blue-500/20 text-xs text-blue-300/90 leading-relaxed flex items-start gap-2.5">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold text-white">AI ตรวจหาหน้าโครงสร้างอัตโนมัติ:</span>{" "}
                      ระบบจะส่งไฟล์ทั้ง <span className="font-mono font-bold text-white">{pages} หน้า</span> ให้ Gemini
                      วิเคราะห์หน้าต่อหน้า เพื่อคัดแยกเฉพาะหน้าที่มีแบบแปลนโครงสร้างเหล็ก (เช่น แปลนคาน, เสา, โครงถักหลังคา, ตารางเหล็ก)
                      และข้ามหน้าสถาปัตยกรรมหรืองานระบบโดยอัตโนมัติ
                    </div>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400 font-mono">
                        เลือกแล้ว {selectedCount} จาก {pages} หน้า
                      </span>
                      <div className="flex items-center gap-3 text-xs">
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); selectAllPages(); }}
                          className="text-blue-400 hover:underline flex items-center gap-1"
                        >
                          <CheckSquare className="w-3 h-3" /> เลือกทั้งหมด
                        </button>
                        <button
                          type="button"
                          onClick={(e) => { e.stopPropagation(); deselectAllPages(); }}
                          className="text-gray-500 hover:text-gray-300 flex items-center gap-1"
                        >
                          <Square className="w-3 h-3" /> ล้าง
                        </button>
                      </div>
                    </div>
                    <div className="flex gap-1.5 flex-wrap max-h-48 overflow-y-auto pr-1">
                      {Array.from({ length: pages }).map((_, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={(e) => { e.stopPropagation(); togglePage(i); }}
                          className={`w-11 h-14 rounded-lg border text-xs font-mono flex flex-col items-center justify-center gap-1 transition-all ${
                            selectedPages[i]
                              ? "border-blue-400 text-blue-300 bg-blue-500/15 shadow-[0_0_0_1px_rgba(88,166,255,0.3)]"
                              : "border-white/8 text-gray-600 hover:border-white/20 hover:text-gray-400"
                          }`}
                        >
                          <FileText className="w-3 h-3" />
                          <span>p{i + 1}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
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
                    {apiKey.trim() ? "✓ บันทึกในเบราว์เซอร์อัตโนมัติ" : "ใส่ Key เพื่อเชื่อมต่อ AI จริง หรือกดเพื่อทดสอบด้วยชุดข้อมูลจำลอง"}
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
                  <span className="text-xs text-gray-500">หน้าที่กำลังสแกน</span>
                  <span className="text-xs font-mono text-emerald-400 font-semibold">
                    {scanMode === "auto" ? `ทุกหน้า (${pages} หน้า)` : `${selectedCount} / ${pages} หน้า`}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-2 space-y-2">
              <button
                onClick={handleExtract}
                disabled={!file || status === "extracting" || (scanMode === "manual" && selectedCount === 0)}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 hover:-translate-y-0.5 disabled:hover:translate-y-0"
              >
                {status === "extracting" ? (
                  <><Loader2 className="w-4 h-4 animate-spin" />กำลังวิเคราะห์และคัดแยกหน้า...</>
                ) : (
                  <><Cpu className="w-4 h-4" />{apiKey.trim() ? "Extract with Gemini" : "Extract BOQ (Demo)"}</>
                )}
              </button>
              {status === "extracting" && extractStep && (
                <p className="text-center text-xs text-blue-400 animate-pulse">{extractStep}</p>
              )}
              {!file && status !== "extracting" && (
                <p className="text-center text-[10px] text-gray-600">อัปโหลด PDF เพื่อเริ่มสกัด</p>
              )}
              {extractError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{extractError}</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Results Area ── */}
        {(status === "done" || status === "demo") && result && (
          <div className="space-y-6">

            {/* ── AI Page Classification Panel (หน้าโครงสร้างที่ตรวจพบ) ── */}
            <div className="rounded-2xl border border-white/8 bg-white/2 p-6 backdrop-blur-sm space-y-4">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                    <Layers className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-base font-semibold text-white flex items-center gap-2">
                      ผลการคัดแยกหน้าโครงสร้างโดย AI
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 font-mono border border-emerald-500/30">
                        {structuralPageList.length > 0
                          ? `พบ ${structuralPageList.length} หน้าโครงสร้าง`
                          : "สแกนแล้ว"}
                      </span>
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      AI อ่านและแยกประเภทของแต่ละหน้า — สกัดรายการเหล็กเฉพาะจากหน้าที่มีแบบวิศวกรรมโครงสร้าง
                    </p>
                  </div>
                </div>

                {/* Filter dropdown */}
                <div className="flex items-center gap-2 text-xs">
                  <Filter className="w-3.5 h-3.5 text-gray-500" />
                  <span className="text-gray-400">กรองตารางตามหน้า:</span>
                  <select
                    value={filterPage}
                    onChange={(e) => setFilterPage(e.target.value === "all" ? "all" : Number(e.target.value))}
                    className="bg-white/5 border border-white/10 rounded-lg px-2.5 py-1 text-xs text-white outline-none font-mono"
                  >
                    <option value="all">แสดงทั้งหมด ({rows.length} รายการ)</option>
                    {structuralPageList.map((pg) => {
                      const count = rows.filter((r) => r.source_page === pg).length;
                      return (
                        <option key={pg} value={pg}>
                          หน้า {pg} ({count} รายการ)
                        </option>
                      );
                    })}
                  </select>
                </div>
              </div>

              {/* Page Analysis Badges */}
              {result.page_analysis && result.page_analysis.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 pt-2">
                  {result.page_analysis.map((p, idx) => {
                    const isSelectedFilter = filterPage === p.page_number;
                    return (
                      <div
                        key={idx}
                        onClick={() => p.is_structural && setFilterPage(isSelectedFilter ? "all" : p.page_number)}
                        className={`p-3 rounded-xl border text-xs transition-all ${
                          p.is_structural
                            ? isSelectedFilter
                              ? "bg-blue-600/20 border-blue-400 text-white shadow-md shadow-blue-500/20 cursor-pointer"
                              : "bg-emerald-500/8 border-emerald-500/25 text-emerald-300 hover:border-emerald-500/50 cursor-pointer"
                            : "bg-white/1 border-white/5 text-gray-500 opacity-60"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <span className="font-mono font-bold flex items-center gap-1.5">
                            <FileText className="w-3.5 h-3.5" />
                            หน้า {p.page_number}
                            {p.sheet_no && (
                              <span className="text-[10px] px-1.5 py-0.2 rounded bg-white/10 font-normal">
                                {p.sheet_no}
                              </span>
                            )}
                          </span>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                              p.is_structural
                                ? "bg-emerald-500/20 text-emerald-400"
                                : "bg-white/5 text-gray-500"
                            }`}
                          >
                            {p.is_structural ? "✓ แบบโครงสร้าง" : "ข้าม (ไม่ใช่โครงสร้าง)"}
                          </span>
                        </div>
                        {p.sheet_name && (
                          <div className="font-medium text-gray-200 truncate mb-0.5">{p.sheet_name}</div>
                        )}
                        {p.summary && (
                          <div className="text-[11px] text-gray-400 line-clamp-2 leading-relaxed">
                            {p.summary}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-xs text-gray-500 font-mono">
                  หน้าที่สแกน: {result.pages.map((p) => `p${p + 1}`).join(", ")}
                </div>
              )}
            </div>

            {/* ── Summary Stats ── */}
            {stats && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  {
                    icon: Users,
                    label: "Distinct Members",
                    value: stats.distinctMembers,
                    sub: "เบอร์ชิ้นส่วนไม่ซ้ำ",
                    color: "text-blue-400",
                    bg: "bg-blue-500/10 border-blue-500/20",
                  },
                  {
                    icon: Package,
                    label: "Total Quantity",
                    value: stats.totalQty.toLocaleString(),
                    sub: "ชิ้นส่วนรวม (ท่อน/ชิ้น)",
                    color: "text-emerald-400",
                    bg: "bg-emerald-500/10 border-emerald-500/20",
                  },
                  {
                    icon: Weight,
                    label: "Total Weight",
                    value: stats.totalWeightKg > 0 ? `${(stats.totalWeightKg / 1000).toFixed(2)} t` : "—",
                    sub: `${stats.totalWeightKg.toLocaleString(undefined, { maximumFractionDigits: 0 })} กก.`,
                    color: "text-purple-400",
                    bg: "bg-purple-500/10 border-purple-500/20",
                  },
                  {
                    icon: AlertCircle,
                    label: "Needs Review",
                    value: stats.needsReview,
                    sub: "แถวที่ต้องตรวจสอบ",
                    color: stats.needsReview > 0 ? "text-amber-400" : "text-gray-500",
                    bg: stats.needsReview > 0 ? "bg-amber-500/10 border-amber-500/20" : "bg-white/5 border-white/10",
                  },
                ].map((s) => (
                  <div key={s.label} className="p-4 rounded-2xl border border-white/8 bg-white/2 backdrop-blur-sm">
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`w-7 h-7 rounded-lg border flex items-center justify-center ${s.bg}`}>
                        <s.icon className={`w-3.5 h-3.5 ${s.color}`} />
                      </div>
                      <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">{s.label}</span>
                    </div>
                    <div className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</div>
                    <div className="text-[11px] text-gray-500 mt-0.5">{s.sub}</div>
                  </div>
                ))}
              </div>
            )}

            {/* ── BOQ Table — glass style ── */}
            <div className="rounded-2xl border border-white/8 overflow-hidden bg-[#0d1117]">
              {/* Table header bar */}
              <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/8 bg-white/2 flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-red-500/60" />
                  <div className="w-2 h-2 rounded-full bg-yellow-500/60" />
                  <div className="w-2 h-2 rounded-full bg-green-500/60" />
                  <span className="ml-3 text-xs font-mono text-gray-400">
                    boq_result · แสดง {displayedRows.length} จาก {rows.length} รายการ
                    {filterPage !== "all" && (
                      <span className="ml-2 text-blue-400 font-semibold">(เฉพาะหน้า {filterPage})</span>
                    )}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      const filled = inferMissingLengths(rows);
                      const withWeights = filled.map((r) => {
                        if (r.unit_weight_kg_m === null) {
                          const rewt = calculateUnitWeight(r.section, r.member_id, r.length_mm);
                          if (rewt !== null) return { ...r, unit_weight_kg_m: rewt };
                        }
                        return r;
                      });
                      setRows(withWeights);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium hover:bg-emerald-500/25 transition-all shadow-sm"
                    title="ยืมความยาวจากชิ้นส่วนที่ใกล้เคียงเพื่อเติมค่า null โดยอัตโนมัติ"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    ยืมความยาวออโต้ (Auto-Borrow Lengths)
                  </button>
                  {filterPage !== "all" && (
                    <button
                      onClick={() => setFilterPage("all")}
                      className="text-xs text-blue-400 hover:underline"
                    >
                      ล้างตัวกรอง
                    </button>
                  )}
                  <span className="text-[10px] text-gray-500 font-mono">คลิก cell เพื่อแก้ไข</span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[760px]">
                  <thead>
                    <tr className="border-b border-white/5 bg-white/2">
                      {[
                        { label: "Member ID", align: "left" },
                        { label: "Section", align: "left" },
                        { label: "Length (mm)", align: "right" },
                        { label: "Qty", align: "right" },
                        { label: "Unit wt (kg/m)", align: "right" },
                        { label: "หน้าที่พบ (Page)", align: "center" },
                        { label: "Notes", align: "left" },
                      ].map((h) => (
                        <th
                          key={h.label}
                          className={`px-4 py-3 text-[10px] font-mono uppercase tracking-wider text-gray-500 font-medium ${
                            h.align === "right" ? "text-right" : h.align === "center" ? "text-center" : "text-left"
                          }`}
                        >
                          {h.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {displayedRows.map((row, ri) => {
                      const actualIdx = rows.indexOf(row);
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
                            isEditing={editingCell?.row === actualIdx && editingCell?.col === "member_id"}
                            onClick={() => setEditingCell({ row: actualIdx, col: "member_id" })}
                            onBlur={(v) => { updateCell(actualIdx, "member_id", v); setEditingCell(null); }}
                            className="font-bold text-blue-400 font-mono text-xs"
                          />
                          <EditableCell
                            value={row.section}
                            isEditing={editingCell?.row === actualIdx && editingCell?.col === "section"}
                            onClick={() => setEditingCell({ row: actualIdx, col: "section" })}
                            onBlur={(v) => { updateCell(actualIdx, "section", v); setEditingCell(null); }}
                            className={`font-mono text-xs ${row.section.startsWith("[") ? "text-yellow-400" : "text-gray-300"}`}
                          />
                          <EditableCell
                            value={row.length_mm !== null ? row.length_mm.toLocaleString() : ""}
                            isEditing={editingCell?.row === actualIdx && editingCell?.col === "length_mm"}
                            onClick={() => setEditingCell({ row: actualIdx, col: "length_mm" })}
                            onBlur={(v) => { updateCell(actualIdx, "length_mm", v); setEditingCell(null); }}
                            className="text-right font-mono text-xs tabular-nums text-gray-300"
                            isNull={row.length_mm === null}
                            align="right"
                          />
                          <EditableCell
                            value={row.quantity !== null ? String(row.quantity) : ""}
                            isEditing={editingCell?.row === actualIdx && editingCell?.col === "quantity"}
                            onClick={() => setEditingCell({ row: actualIdx, col: "quantity" })}
                            onBlur={(v) => { updateCell(actualIdx, "quantity", v); setEditingCell(null); }}
                            className="text-right font-mono text-xs tabular-nums text-gray-300"
                            isNull={row.quantity === null}
                            align="right"
                          />
                          <EditableCell
                            value={row.unit_weight_kg_m !== null ? row.unit_weight_kg_m.toFixed(1) : ""}
                            isEditing={editingCell?.row === actualIdx && editingCell?.col === "unit_weight_kg_m"}
                            onClick={() => setEditingCell({ row: actualIdx, col: "unit_weight_kg_m" })}
                            onBlur={(v) => { updateCell(actualIdx, "unit_weight_kg_m", v); setEditingCell(null); }}
                            className={`text-right font-mono text-xs tabular-nums ${row.unit_weight_kg_m !== null ? "text-green-400" : ""}`}
                            isNull={row.unit_weight_kg_m === null}
                            align="right"
                          />
                          {/* Source Page Column */}
                          <td className="px-4 py-2.5 text-center">
                            {row.source_page ? (
                              <button
                                type="button"
                                onClick={() => setFilterPage(row.source_page!)}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/25 text-blue-300 text-[11px] font-mono hover:bg-blue-500/20 transition-colors"
                              >
                                p{row.source_page}
                                {row.sheet_no && <span className="text-gray-400">({row.sheet_no})</span>}
                              </button>
                            ) : (
                              <span className="text-gray-600 text-xs">—</span>
                            )}
                          </td>
                          <EditableCell
                            value={row.notes}
                            isEditing={editingCell?.row === actualIdx && editingCell?.col === "notes"}
                            onClick={() => setEditingCell({ row: actualIdx, col: "notes" })}
                            onBlur={(v) => { updateCell(actualIdx, "notes", v); setEditingCell(null); }}
                            className="text-gray-400 text-xs max-w-[200px] truncate"
                          />
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Table footer */}
              <div className="flex items-center justify-between px-5 py-3 border-t border-white/5 bg-white/2">
                <span className="text-xs font-mono text-gray-500">
                  {stats?.distinctMembers} members · {stats?.totalQty} pcs total
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-500">
                    Extracted in {result.latency_s}s ({result.model})
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                </div>
              </div>
            </div>

            {/* Export CTA */}
            <div className="flex items-center justify-between p-5 rounded-2xl border border-white/8 bg-white/2 flex-wrap gap-4">
              <div>
                <p className="text-sm font-medium text-white">พร้อม Export BOQ</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  ดาวน์โหลด BOQ ที่ผ่านการตรวจคัดแยกหน้าโครงสร้างแล้วเป็นไฟล์ CSV
                </p>
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
  onBlur: (val: string) => void;
  className?: string;
  isNull?: boolean;
  align?: "left" | "right";
}) {
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  if (isEditing) {
    return (
      <td className="px-2 py-1">
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={() => onBlur(draft)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onBlur(draft);
            if (e.key === "Escape") setDraft(value);
          }}
          className={`w-full bg-blue-500/15 border border-blue-400 rounded px-2 py-1 text-xs text-white outline-none font-mono ${
            align === "right" ? "text-right" : "text-left"
          }`}
        />
      </td>
    );
  }

  return (
    <td
      onClick={onClick}
      className={`px-4 py-2.5 cursor-pointer hover:bg-white/5 transition-colors ${className}`}
    >
      {isNull ? (
        <span className="text-amber-400/80 font-mono text-xs flex items-center gap-1 justify-end">
          <AlertCircle className="w-3 h-3" />
          null
        </span>
      ) : (
        value || <span className="text-gray-700 font-mono">—</span>
      )}
    </td>
  );
}
