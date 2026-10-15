// Steel section unit weight calculation, parsing, and length borrowing heuristics
// Compatible with steel_boq_mvp/boq_utils.py

const STEEL_DENSITY_KG_M3 = 7850.0;
const LB_FT_TO_KG_M = 1.48816;

const SECTION_TABLE: Record<string, number> = {
  // JIS Channels
  "C200X80X7.5X11": 24.6,
  "C250X90X9X13": 34.6,
  "C300X90X9X13": 38.1,
  "C150X75X6.5X10": 18.6,
  "C100X50X5X7.5": 9.36,
  // JIS H-Beams
  "H200X200X8X12": 49.9,
  "H250X250X9X14": 72.4,
  "H300X300X10X15": 94.0,
  "H350X350X12X19": 137.0,
  "H400X400X13X21": 172.0,
  "H250X125X6X9": 29.6,
  "H300X150X6.5X9": 36.7,
  "H350X175X7X11": 49.6,
  "H400X200X8X13": 66.0,
  "H500X200X10X16": 89.6,
};

const H_RE = /^(?:H|HN|HW|HM|HP|UB|UC|IPE|HE[ABM]?)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;
const C_RE = /^(?:\[|C|PFC|U)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;
const I_RE = /^I\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;
const L_RE = /^(?:L|∠)\s*-?\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;
const W_RE = /^W\s*(\d+)\s*[xX×]\s*(\d+(?:\.\d+)?)$/;

function norm(section: string): string {
  return section.replace(/\s+/g, "").toUpperCase().replace(/×/g, "X");
}

/**
 * Calculates unit weight (kg/m) for various structural steel shapes:
 * 1. Explicit annotations (e.g. "Steel 90mm, 7.76 kg/m", "12.1 kg/m", "4.52 kg/m")
 * 2. H/I/Channel/Angle standard rolled sections
 * 3. Square and Rectangular Tubes (both metric e.g. 100x50x3.2 and imperial e.g. 2"x4"x2mm)
 * 4. Round Bars / Anchor Bolts (Dia 25mm, RB25, DB25)
 * 5. Round Pipes / CHS (Pipe 100 dia x 3.2)
 * 6. Steel Plates (Plate 25mm, Base Plate, Stiffener Plate)
 */
export function calculateUnitWeight(
  sectionStr: string | null | undefined,
  memberId?: string | null,
  lengthMm?: number | null
): number | null {
  if (!sectionStr || typeof sectionStr !== "string") return null;

  const raw = sectionStr.trim();

  // 1. Check for explicit weight specified directly in the drawing text
  // e.g. "Steel 90mm, 7.76 kg/m", "TRUSS 1 12.1 kg/m", "4.52 kg/m", "49.9 kg/m"
  const mExplicit = raw.match(
    /(?:^|[,\s\(/@])([0-9]+(?:\.[0-9]+)?)\s*(?:kg\/m|กก\.\/ม|kg\.m|kg-m|kg\/m2|กก\.\/ตร\.ม\.)/i
  );
  if (mExplicit) {
    return parseFloat(mExplicit[1]);
  }

  const s = norm(raw);

  // 2. Check catalogue table (JIS Channels & H-Beams)
  const key = s.replace(/^\[/, "C").replace(/^H-/, "H");
  if (SECTION_TABLE[key] !== undefined) {
    return SECTION_TABLE[key];
  }
  if (SECTION_TABLE[s] !== undefined) {
    return SECTION_TABLE[s];
  }

  // 3. Round bar / Anchor Bolt / Deformed bar (e.g. "Dia 25mm", "Dia 25", "RB25", "DB25", "Ø25")
  const mRoundBar = raw.match(
    /(?:DIA\.?|DIAMETER|Ø|RB|DB|ANCHOR\s*BOLT|BOLT)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?/i
  );
  if (mRoundBar) {
    const d = parseFloat(mRoundBar[1]);
    // Formula: (pi/4) * d^2 * 7850 / 1e6 ~= 0.006165 * d^2
    const w = 0.006165 * d * d;
    return Math.round(w * 100) / 100;
  }

  // 4. Square & Rectangular Tubes - Imperial inches (e.g. 'Square Tube 2"x4"x2mm', '2"x4"x2mm', '2"x2"x2.3')
  const mInchTube = raw.match(
    /(?:SQUARE|RECTANGULAR|STEEL)?\s*(?:TUBE|SHS|RHS|กล่องเหลี่ยม|ท่อเหลี่ยม)?\s*(\d+(?:\.\d+)?)\s*(?:"|IN|นิ้ว)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:"|IN|นิ้ว)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?/i
  );
  if (mInchTube) {
    const a = parseFloat(mInchTube[1]) * 25.4; // convert inches to mm
    const b = parseFloat(mInchTube[2]) * 25.4;
    const t = parseFloat(mInchTube[3]);
    const area_mm2 = 2 * (a + b - 2 * t) * t;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 5. Square & Rectangular Tubes - Metric (e.g. "Square Tube 100x50x3.2", "SHS 100x100x3.2", "RHS 150x100x4.5")
  const mMetricTube = raw.match(
    /(?:SQUARE|RECTANGULAR|STEEL)?\s*(?:TUBE|SHS|RHS|กล่องเหลี่ยม|ท่อเหลี่ยม)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?/i
  );
  if (mMetricTube) {
    const a = parseFloat(mMetricTube[1]);
    const b = parseFloat(mMetricTube[2]);
    const t = parseFloat(mMetricTube[3]);
    const area_mm2 = 2 * (a + b - 2 * t) * t;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 6. Round Pipe / Circular Hollow Section (e.g. "Pipe 100 dia x 3.2", "CHS 114.3x4.5", "ท่อกลม 2 นิ้ว")
  const mPipe = raw.match(/(?:PIPE|CHS|ท่อกลม)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:DIA|Ø)?\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?/i);
  if (mPipe) {
    const od = parseFloat(mPipe[1]);
    const t = parseFloat(mPipe[2]);
    const area_mm2 = Math.PI * (od - t) * t;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 7. Check H/UB/UC/IPE shapes (H-200x200x8x12)
  const mH = s.match(H_RE);
  if (mH) {
    const h = parseFloat(mH[1]);
    const b = parseFloat(mH[2]);
    const tw = parseFloat(mH[3]);
    const tf = parseFloat(mH[4]);
    const area_mm2 = 2 * b * tf + (h - 2 * tf) * tw;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 8. Check Channel shapes (C200x80x7.5x11, [200x80x7.5x11)
  const mC = s.match(C_RE);
  if (mC) {
    const h = parseFloat(mC[1]);
    const b = parseFloat(mC[2]);
    const tw = parseFloat(mC[3]);
    const tf = parseFloat(mC[4]);
    const area_mm2 = 2 * b * tf + (h - 2 * tf) * tw;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 9. Check I-Beam shapes
  const mI = s.match(I_RE);
  if (mI) {
    const h = parseFloat(mI[1]);
    const b = parseFloat(mI[2]);
    const tw = parseFloat(mI[3]);
    const tf = parseFloat(mI[4]);
    const area_mm2 = 2 * b * tf + (h - 2 * tf) * tw;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e5) / 10;
  }

  // 10. Check Angle L shapes (L a x b x t)
  const mL = s.match(L_RE);
  if (mL) {
    const a = parseFloat(mL[1]);
    const b = parseFloat(mL[2]);
    const t = parseFloat(mL[3]);
    const area_mm2 = (a + b - t) * t;
    return Math.round((STEEL_DENSITY_KG_M3 * area_mm2) / 1e4) / 100;
  }

  // 11. Check Imperial Wide Flange W shapes (W12x26)
  const mW = s.match(W_RE);
  if (mW) {
    const lb_ft = parseFloat(mW[2]);
    return Math.round(lb_ft * LB_FT_TO_KG_M * 10) / 10;
  }

  // 12. Steel Plates (e.g. "Plate 25mm", "Plate 12mm", "PL 25x300", "Base Plate", "Stiffener Plate")
  const mPlateDim = raw.match(/(?:PLATE|PL|แผ่นเพลท)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?\s*[xX×*]\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?/i);
  if (mPlateDim) {
    const t = parseFloat(mPlateDim[1]);
    const w = parseFloat(mPlateDim[2]);
    // kg/m = (t * w * 7850) / 1e6
    return Math.round((t * w * STEEL_DENSITY_KG_M3) / 1e5) / 10;
  }

  const mPlateThick = raw.match(/(?:PLATE|PL|แผ่นเพลท)\s*[-:]?\s*(\d+(?:\.\d+)?)\s*(?:MM|มม)?/i);
  if (mPlateThick) {
    const t = parseFloat(mPlateThick[1]);
    const mid = (memberId || "").toLowerCase();

    // If Base Plate and length is known (e.g. 300 mm), assume square base plate (300x300)
    if (mid.includes("base") && lengthMm && lengthMm > 0) {
      // Area = length * length, weight per linear meter of length = length * t * 7850 / 1e6
      return Math.round(((lengthMm * t * STEEL_DENSITY_KG_M3) / 1e6) * 10) / 10;
    }
    // For stiffener plate, typical width matches column/beam flange ~200mm
    if (mid.includes("stiffener")) {
      const assumedWidth = 200;
      return Math.round(((assumedWidth * t * STEEL_DENSITY_KG_M3) / 1e6) * 10) / 10;
    }
    // Generic plate assuming standard 250mm connection width
    const defaultWidth = 250;
    return Math.round(((defaultWidth * t * STEEL_DENSITY_KG_M3) / 1e6) * 10) / 10;
  }

  return null;
}

/**
 * Heuristic length borrowing algorithm:
 * For any member whose length_mm is null, automatically borrows length from
 * confident/known members in the drawing having similar dimensions, structural group, or role.
 */
export function inferMissingLengths<
  T extends {
    member_id: string;
    section: string;
    length_mm: number | null;
    notes?: string | null;
  }
>(rows: T[]): T[] {
  const knownRows = rows.filter((r) => r.length_mm != null && r.length_mm > 0);
  if (knownRows.length === 0) return rows;

  return rows.map((row) => {
    if (row.length_mm != null && row.length_mm > 0) {
      return row;
    }

    const mid = (row.member_id || "").toLowerCase();
    const sec = (row.section || "").toLowerCase();
    const existingNotes = (row.notes || "").trim();

    let borrowedLength: number | null = null;
    let borrowSource = "";

    // 1. Truss members borrowing from other truss chords/members (e.g. TRUSS 2 borrows from TRUSS 1)
    if (mid.includes("truss") || sec.includes("truss")) {
      const otherTruss = knownRows.find(
        (k) =>
          (k.member_id.toLowerCase().includes("truss") || k.section.toLowerCase().includes("truss")) &&
          k.length_mm != null &&
          k.length_mm > 0
      );
      if (otherTruss && otherTruss.length_mm) {
        borrowedLength = otherTruss.length_mm;
        borrowSource = `ยืมความยาวจาก ${otherTruss.member_id} (${otherTruss.length_mm.toLocaleString()} mm)`;
      }
    }

    // 2. Stiffener Plate or Gusset Plate:
    // Derives from attached Column/Beam dimensions (e.g. H-200x200 flange 200mm) or Base Plate length (e.g. 300mm)
    if (
      !borrowedLength &&
      (mid.includes("stiffener") ||
        sec.includes("stiffener") ||
        (mid.includes("plate") && !mid.includes("base")))
    ) {
      // Find H-beam / Column dimension
      const hBeam = rows.find((r) => /H\s*-?\s*(\d+)\s*[xX×]/i.test(r.section));
      if (hBeam) {
        const m = hBeam.section.match(/H\s*-?\s*(\d+)\s*[xX×]/i);
        if (m) {
          const dim = parseFloat(m[1]);
          borrowedLength = dim;
          borrowSource = `ยืมมิติจากหน้าตัด ${hBeam.member_id || hBeam.section} (${dim} mm)`;
        }
      }
      if (!borrowedLength) {
        const basePlate = knownRows.find(
          (k) => k.member_id.toLowerCase().includes("base") || k.member_id.toLowerCase().includes("plate")
        );
        if (basePlate && basePlate.length_mm) {
          borrowedLength = basePlate.length_mm;
          borrowSource = `ยืมความยาวจาก ${basePlate.member_id} (${basePlate.length_mm.toLocaleString()} mm)`;
        }
      }
    }

    // 3. Column (เสา):
    // Borrow from other columns or typical floor height / bay spacing (e.g. 3000, 3500, 4000, 6000 mm)
    if (!borrowedLength && (mid.includes("column") || mid.includes("เสา") || (mid.startsWith("c") && /\d/.test(mid)))) {
      const otherCol = knownRows.find(
        (k) =>
          (k.member_id.toLowerCase().includes("column") ||
            k.member_id.toLowerCase().includes("เสา") ||
            (k.member_id.toLowerCase().startsWith("c") && /\d/.test(k.member_id))) &&
          k.length_mm != null
      );
      if (otherCol && otherCol.length_mm) {
        borrowedLength = otherCol.length_mm;
        borrowSource = `ยืมความยาวจาก ${otherCol.member_id} (${otherCol.length_mm.toLocaleString()} mm)`;
      } else {
        // Check if there is a known bay span like 6000mm or typical storey height
        const standardHeight = knownRows.find((k) => k.length_mm === 6000 || k.length_mm === 3000 || k.length_mm === 4000);
        if (standardHeight && standardHeight.length_mm) {
          borrowedLength = standardHeight.length_mm;
          borrowSource = `ยืมความยาวจากระยะช่วงเสา ${standardHeight.member_id} (${standardHeight.length_mm.toLocaleString()} mm)`;
        } else {
          borrowedLength = 4000;
          borrowSource = `assume ความสูงเสามาตรฐาน 4,000 mm`;
        }
      }
    }

    // 4. Match exact or similar section dimension
    if (!borrowedLength) {
      const sameSec = knownRows.find(
        (k) => norm(k.section) === norm(row.section) && k.length_mm != null
      );
      if (sameSec && sameSec.length_mm) {
        borrowedLength = sameSec.length_mm;
        borrowSource = `ยืมความยาวจาก ${sameSec.member_id} (หน้าตัดเดียวกัน)`;
      }
    }

    // 5. Match member prefix (e.g. B1, B2, P1, P2)
    if (!borrowedLength) {
      const prefix = mid.replace(/[^a-z]/g, "").slice(0, 3);
      if (prefix.length >= 2) {
        const similar = knownRows.find(
          (k) => k.member_id.toLowerCase().includes(prefix) && k.length_mm != null
        );
        if (similar && similar.length_mm) {
          borrowedLength = similar.length_mm;
          borrowSource = `ยืมความยาวจาก ${similar.member_id}`;
        }
      }
    }

    // 6. Closest confident member in the drawing
    if (!borrowedLength && knownRows.length > 0) {
      const currentIndex = rows.indexOf(row);
      let closestRow = knownRows[0];
      let minDistance = 999999;
      for (const k of knownRows) {
        const kIndex = rows.indexOf(k);
        const dist = Math.abs(kIndex - currentIndex);
        if (dist < minDistance) {
          minDistance = dist;
          closestRow = k;
        }
      }
      if (closestRow && closestRow.length_mm) {
        borrowedLength = closestRow.length_mm;
        borrowSource = `ยืมความยาวจาก ${closestRow.member_id} (${closestRow.length_mm.toLocaleString()} mm)`;
      }
    }

    if (borrowedLength != null) {
      const updatedNotes = existingNotes
        ? `${existingNotes} [${borrowSource}]`
        : `[${borrowSource}]`;
      return {
        ...row,
        length_mm: borrowedLength,
        notes: updatedNotes,
      };
    }

    return row;
  });
}
