// Steel section unit weight calculation and parsing helpers
// Compatible with steel_boq_mvp/boq_utils.py

const STEEL_DENSITY_KG_M3 = 7850.0;
const LB_FT_TO_KG_M = 1.48816;

const SECTION_TABLE: Record<string, number> = {
  "C200X80X7.5X11": 24.6,
  "C250X90X9X13": 34.6,
  "C300X90X9X13": 38.1,
  "C150X75X6.5X10": 18.6,
  "C100X50X5X7.5": 9.36,
};

const H_RE = /^(?:H|HN|HW|HM|HP|UB|UC|IPE|HE[ABM]?)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;
const C_RE = /^(?:\[|C|PFC|U)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;
const W_RE = /^W\s*(\d+)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;

function norm(section: string): string {
  return section.replace(/\s+/g, "").toUpperCase().replace(/×/g, "X");
}

export function calculateUnitWeight(sectionStr: string | null | undefined): number | null {
  if (!sectionStr || typeof sectionStr !== "string") return null;

  const s = norm(sectionStr);

  // 1. Check catalogue table
  const key = s.replace(/^\[/, "C");
  if (SECTION_TABLE[key] !== undefined) {
    return SECTION_TABLE[key];
  }

  // 2. Check H/UB/UC/IPE shapes
  const mH = s.match(H_RE);
  if (mH) {
    const h = parseFloat(mH[1]);
    const b = parseFloat(mH[2]);
    const tw = parseFloat(mH[3]);
    const tf = parseFloat(mH[4]);
    const area_mm2 = 2 * b * tf + (h - 2 * tf) * tw;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 3. Check Channel shapes
  const mC = s.match(C_RE);
  if (mC) {
    const h = parseFloat(mC[1]);
    const b = parseFloat(mC[2]);
    const tw = parseFloat(mC[3]);
    const tf = parseFloat(mC[4]);
    const area_mm2 = 2 * b * tf + (h - 2 * tf) * tw;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 4. Check Imperial Wide Flange W shapes
  const mW = s.match(W_RE);
  if (mW) {
    const lb_ft = parseFloat(mW[2]);
    return Math.round(lb_ft * LB_FT_TO_KG_M * 10) / 10;
  }

  return null;
}
