import { supabase, isSupabaseConfigured } from "@/lib/supabase";
import { ExtractedBOQItem, PageAnalysis } from "@/lib/extract-client";

export interface SaveBOQPayload {
  title: string;
  fileName?: string;
  fileSizeBytes?: number;
  items: ExtractedBOQItem[];
  pageAnalysis?: PageAnalysis[];
  structuralPages?: number[];
}

export async function saveBOQProject(payload: SaveBOQPayload) {
  if (!isSupabaseConfigured) {
    throw new Error("Supabase ยังไม่ได้ตั้งค่า URL หรือ Anon Key กรุณาตรวจสอบ .env.local");
  }

  const totalWeight = payload.items.reduce((sum, item) => {
    if (item.length_mm && item.quantity && item.unit_weight_kg_m) {
      return sum + (item.length_mm / 1000) * item.quantity * item.unit_weight_kg_m;
    }
    return sum;
  }, 0);

  // 1. บันทึกลงตาราง boq_projects
  const { data: project, error: projErr } = await supabase
    .from("boq_projects")
    .insert({
      title: payload.title || "แบบถอดโครงสร้างเหล็ก",
      file_name: payload.fileName || null,
      file_size_bytes: payload.fileSizeBytes || null,
      total_members: payload.items.length,
      total_weight_kg: Math.round(totalWeight * 100) / 100,
      structural_pages: payload.structuralPages || [],
    })
    .select("id")
    .single();

  if (projErr || !project) {
    throw new Error(projErr?.message || "บันทึกข้อมูลโปรเจกต์ไม่สำเร็จ");
  }

  const projectId = project.id;

  // 2. บันทึกรายการ boq_items
  if (payload.items.length > 0) {
    const itemRows = payload.items.map((item) => {
      const totalWeightKg =
        item.length_mm && item.quantity && item.unit_weight_kg_m
          ? Math.round(((item.length_mm / 1000) * item.quantity * item.unit_weight_kg_m) * 100) / 100
          : null;

      return {
        project_id: projectId,
        member_id: item.member_id || null,
        section: item.section || "-",
        length_mm: item.length_mm,
        quantity: item.quantity,
        unit_weight_kg_m: item.unit_weight_kg_m,
        total_weight_kg: totalWeightKg,
        source_page: item.source_page || null,
        sheet_no: item.sheet_no || null,
        notes: item.notes || null,
      };
    });

    const { error: itemsErr } = await supabase.from("boq_items").insert(itemRows);
    if (itemsErr) {
      console.warn("ไม่สามารถบันทึก boq_items ได้:", itemsErr);
    }
  }

  // 3. บันทึกการวิเคราะห์หน้า (page analysis)
  if (payload.pageAnalysis && payload.pageAnalysis.length > 0) {
    const pageRows = payload.pageAnalysis.map((p) => ({
      project_id: projectId,
      page_number: p.page_number,
      sheet_no: p.sheet_no || null,
      sheet_name: p.sheet_name || null,
      is_structural: Boolean(p.is_structural),
      category: p.category || null,
      summary: p.summary || null,
    }));

    const { error: pagesErr } = await supabase.from("boq_page_analysis").insert(pageRows);
    if (pagesErr) {
      console.warn("ไม่สามารถบันทึก boq_page_analysis ได้:", pagesErr);
    }
  }

  return { projectId, success: true };
}

export async function fetchBOQProjects() {
  if (!isSupabaseConfigured) return [];
  const { data, error } = await supabase
    .from("boq_projects")
    .select("id, title, file_name, total_members, total_weight_kg, created_at")
    .order("created_at", { ascending: false });

  if (error) {
    console.error("fetchBOQProjects error:", error);
    return [];
  }
  return data || [];
}

export async function fetchBOQProjectDetail(projectId: string) {
  if (!isSupabaseConfigured) return null;

  const [projectRes, itemsRes, pagesRes] = await Promise.all([
    supabase.from("boq_projects").select("*").eq("id", projectId).single(),
    supabase.from("boq_items").select("*").eq("project_id", projectId),
    supabase.from("boq_page_analysis").select("*").eq("project_id", projectId).order("page_number"),
  ]);

  if (projectRes.error) {
    throw new Error(projectRes.error.message);
  }

  return {
    project: projectRes.data,
    items: itemsRes.data || [],
    pages: pagesRes.data || [],
  };
}
