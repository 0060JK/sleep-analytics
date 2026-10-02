-- ฟีเจอร์เสริม: เวลาการนอนที่ผู้ใช้ตั้งไว้ (รันหลัง schema.sql · ถ้าเลิกใช้ฟีเจอร์ ลบตารางนี้ได้เลย ไม่กระทบตารางอื่น)

create table if not exists public.sleep_schedule (
  user_id        uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  weekday_wake   time not null default '07:00',   -- เวลาตื่นวันจันทร์–ศุกร์
  weekend_wake   time not null default '08:30',   -- เวลาตื่นวันเสาร์–อาทิตย์
  target_hours   numeric(3,1) not null default 8 check (target_hours between 4 and 12),
  remind_before  smallint not null default 30 check (remind_before between 0 and 180),
  updated_at     timestamptz not null default now()
);

alter table public.sleep_schedule enable row level security;

drop policy if exists "own schedule" on public.sleep_schedule;
create policy "own schedule" on public.sleep_schedule for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
