-- Schema สำหรับโปรเจกต์ Steel Tech (BOQ & Workmen Diary)
-- รันสคริปต์นี้ใน Supabase SQL Editor: https://supabase.com/dashboard/project/_/sql

-- 1. ตารางเก็บประวัติงานถอดแบบ (BOQ Projects)
create table if not exists public.boq_projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  title text not null,
  file_name text,
  file_size_bytes bigint,
  total_members integer default 0,
  total_weight_kg numeric(12, 2) default 0,
  structural_pages integer[] default '{}',
  created_at timestamptz default timezone('utc'::text, now()) not null,
  updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- 2. ตารางรายการเหล็กที่ถอดได้ (BOQ Items)
create table if not exists public.boq_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.boq_projects(id) on delete cascade not null,
  member_id text,
  section text not null,
  length_mm numeric(10, 2),
  quantity numeric(10, 2),
  unit_weight_kg_m numeric(10, 2),
  total_weight_kg numeric(12, 2),
  source_page integer,
  sheet_no text,
  notes text,
  created_at timestamptz default timezone('utc'::text, now()) not null
);

-- 3. ตารางวิเคราะห์หน้าเอกสาร (Page Analysis)
create table if not exists public.boq_page_analysis (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.boq_projects(id) on delete cascade not null,
  page_number integer not null,
  sheet_no text,
  sheet_name text,
  is_structural boolean default false,
  category text,
  summary text,
  created_at timestamptz default timezone('utc'::text, now()) not null
);

-- 4. ตารางประวัติการตรวจสอบและฟีดแบ็ก (Feedback Loop สำหรับเทรน AI)
create table if not exists public.boq_feedback (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.boq_projects(id) on delete set null,
  drawing_id text,
  page_no integer,
  member_id text,
  field_path text not null,
  ai_value text,
  ai_confidence numeric(5, 4),
  human_value text,
  action text not null check (action in ('confirmed', 'corrected', 'marked_unreadable')),
  training_status text default 'pending' check (training_status in ('pending', 'approved', 'rejected', 'used')),
  user_role text default 'user',
  consent boolean default false,
  created_at timestamptz default timezone('utc'::text, now()) not null
);

-- 5. ตารางบันทึกรายงานช่าง (Workmen Diary) รองรับ workmen_diary.html
create table if not exists public.workmen_diary_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete set null,
  entry_date date not null default current_date,
  site_name text not null,
  supervisor_name text,
  worker_count integer default 0,
  weather text,
  work_description text,
  problems text,
  photos text[] default '{}',
  created_at timestamptz default timezone('utc'::text, now()) not null,
  updated_at timestamptz default timezone('utc'::text, now()) not null
);

-- เปิดใช้งาน Row Level Security (RLS)
alter table public.boq_projects enable row level security;
alter table public.boq_items enable row level security;
alter table public.boq_page_analysis enable row level security;
alter table public.boq_feedback enable row level security;
alter table public.workmen_diary_entries enable row level security;

-- Policies สำหรับ boq_projects (อนุญาตให้ผู้ใช้ทั่วไป/anon อ่านและเขียนได้ หรือผูกกับ User ID เมื่อล็อกอิน)
create policy "Allow all read access for boq_projects" 
  on public.boq_projects for select using (true);

create policy "Allow insert access for boq_projects" 
  on public.boq_projects for insert with check (true);

create policy "Allow update for own project" 
  on public.boq_projects for update using (
    auth.uid() is null or auth.uid() = user_id
  );

create policy "Allow delete for own project" 
  on public.boq_projects for delete using (
    auth.uid() is null or auth.uid() = user_id
  );

-- Policies สำหรับ boq_items
create policy "Allow all access for boq_items" 
  on public.boq_items for all using (true);

-- Policies สำหรับ boq_page_analysis
create policy "Allow all access for boq_page_analysis" 
  on public.boq_page_analysis for all using (true);

-- Policies สำหรับ boq_feedback
create policy "Allow all access for boq_feedback" 
  on public.boq_feedback for all using (true);

-- Policies สำหรับ workmen_diary_entries
create policy "Allow all access for workmen_diary_entries" 
  on public.workmen_diary_entries for all using (true);

-- Index ช่วยเพิ่มประสิทธิภาพในการค้นหา
create index if not exists idx_boq_items_project_id on public.boq_items(project_id);
create index if not exists idx_boq_page_analysis_project_id on public.boq_page_analysis(project_id);
create index if not exists idx_boq_projects_created_at on public.boq_projects(created_at desc);
create index if not exists idx_workmen_diary_date on public.workmen_diary_entries(entry_date desc);
