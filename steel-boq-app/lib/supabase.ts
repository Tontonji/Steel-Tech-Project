import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase = createClient(
  supabaseUrl || "https://placeholder.supabase.co",
  supabaseAnonKey || "placeholder-anon-key"
);

export interface BOQProjectRecord {
  id?: string;
  title: string;
  file_name?: string;
  file_size_bytes?: number;
  total_members: number;
  total_weight_kg: number;
  structural_pages: number[];
  created_at?: string;
}

export interface BOQItemRecord {
  id?: string;
  project_id: string;
  member_id: string;
  section: string;
  length_mm: number | null;
  quantity: number | null;
  unit_weight_kg_m: number | null;
  total_weight_kg: number | null;
  source_page?: number | null;
  sheet_no?: string | null;
  notes?: string;
}

export interface BOQPageAnalysisRecord {
  id?: string;
  project_id: string;
  page_number: number;
  sheet_no?: string;
  sheet_name?: string;
  is_structural: boolean;
  category?: string;
  summary?: string;
}
