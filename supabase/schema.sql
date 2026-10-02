-- Step 4: คัดลอกทั้งไฟล์นี้ไปวางใน Supabase → SQL Editor → กด Run (ทำครั้งเดียว)

create table if not exists public.sleep_logs (
  id                          bigint generated always as identity primary key,
  user_id                     uuid not null default auth.uid() references auth.users (id) on delete cascade,
  date                        date not null,                 -- วันที่ของเช้าที่ตื่น
  bedtime                     time not null,
  waketime                    time not null,
  hours                       numeric(4,1) not null check (hours between 0 and 24),
  sleep_latency_minutes       smallint,                      -- null = ผู้ใช้ไม่ได้ตอบ
  number_of_night_wakeups     smallint,
  bedtime_screen_time_minutes smallint,
  stress_score                smallint check (stress_score between 1 and 10),
  doomscroller                text check (doomscroller in ('Yes', 'No')),
  created_at                  timestamptz not null default now(),
  updated_at                  timestamptz not null default now(),
  unique (user_id, date)                                     -- 1 คน 1 บันทึกต่อวัน (บันทึกซ้ำ = แก้ไข)
);

-- Row Level Security: แต่ละคนเห็นและแก้ได้เฉพาะข้อมูลของตัวเอง
alter table public.sleep_logs enable row level security;

drop policy if exists "read own logs"   on public.sleep_logs;
drop policy if exists "insert own logs" on public.sleep_logs;
drop policy if exists "update own logs" on public.sleep_logs;
drop policy if exists "delete own logs" on public.sleep_logs;

create policy "read own logs"   on public.sleep_logs for select to authenticated using ((select auth.uid()) = user_id);
create policy "insert own logs" on public.sleep_logs for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "update own logs" on public.sleep_logs for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "delete own logs" on public.sleep_logs for delete to authenticated using ((select auth.uid()) = user_id);
