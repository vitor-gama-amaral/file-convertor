create extension if not exists pgcrypto;

create table if not exists public.document_vault (
    id uuid primary key default gen_random_uuid(),
    token_hash text not null unique,
    filename text not null,
    stored_path text not null,
    mime_type text not null default 'application/pdf',
    file_size bigint not null check (file_size >= 0),
    expires_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_document_vault_expires_at
    on public.document_vault (expires_at);

alter table public.document_vault enable row level security;
