create table if not exists linkedin_contacts_import (
  id uuid primary key default gen_random_uuid(),
  full_name text,
  first_name text,
  last_name text,
  job_title text,
  occupation text,
  company_name text,
  normalized_company_name text,
  matched_company_id uuid,
  matched_company_name text,
  match_confidence int default 0,
  match_reason text,
  linkedin_url text,
  sales_navigator_id text,
  company_website text,
  company_linkedin_url text,
  location text,
  premium text,
  profile_status text,
  profile_picture_url text,
  decision_level text,
  contact_score int default 0,
  walaxy_ready_candidate boolean default false,
  calibration_reason text,
  import_status text default 'imported',
  promotion_status text default 'not_promoted',
  rejection_reason text,
  is_duplicate boolean default false,
  duplicate_contact_id uuid,
  source_file text,
  source_hash text unique,
  imported_at timestamptz default now(),
  calibrated_at timestamptz,
  promoted_at timestamptz
);

alter table contacts add column if not exists profile_picture_url text;
alter table contacts add column if not exists sales_navigator_id text;
alter table contacts add column if not exists linkedin_import_id uuid;
alter table contacts add column if not exists linkedin_import_score int default 0;
alter table contacts add column if not exists linkedin_import_decision_level text;

alter table companies add column if not exists linkedin_contacts_count int default 0;
alter table companies add column if not exists walaxy_ready_contacts_count int default 0;
alter table companies add column if not exists top_linkedin_contact_name text;
alter table companies add column if not exists top_linkedin_contact_role text;
alter table companies add column if not exists top_linkedin_contact_url text;

alter table programs add column if not exists image_url text;
alter table programs add column if not exists price_from numeric;
alter table programs add column if not exists delivery_date text;
alter table programs add column if not exists typology text;
alter table programs add column if not exists lots_summary text;
alter table programs add column if not exists available_lot_count int;
alter table programs add column if not exists plan_url text;
alter table programs add column if not exists brochure_url text;
alter table programs add column if not exists is_program_detail boolean default false;
alter table programs add column if not exists extraction_quality_reason text;
alter table programs add column if not exists commercial_status text default 'à qualifier';

notify pgrst, 'reload schema';
