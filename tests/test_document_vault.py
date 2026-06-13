import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.document_vault import (
    DocumentVaultRecord,
    DocumentVaultService,
    SupabaseDocumentVaultRepository,
    hash_token,
)

WORKSPACE_TEST_DIR = Path(__file__).resolve().parent / "vault_test_workspace"


@pytest.fixture
def workspace_path(request):
    path = WORKSPACE_TEST_DIR / request.node.name
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


class FakeDocumentRepository:
    def __init__(self):
        self.records = {}
        self.deleted_ids = []

    def create(self, payload):
        document_id = f"doc-{len(self.records) + 1}"
        record = DocumentVaultRecord(
            id=document_id,
            token_hash=payload["token_hash"],
            filename=payload["filename"],
            stored_path=payload["stored_path"],
            mime_type=payload["mime_type"],
            file_size=payload["file_size"],
            expires_at=datetime.fromisoformat(payload["expires_at"]),
            created_at=datetime.now(timezone.utc),
        )
        self.records[document_id] = record
        return record

    def find_by_token_hash(self, token_hash):
        return next(
            (
                record
                for record in self.records.values()
                if record.token_hash == token_hash
            ),
            None,
        )

    def list_expired(self, now):
        return [
            record
            for record in self.records.values()
            if record.expires_at <= now
        ]

    def delete_by_id(self, document_id):
        self.deleted_ids.append(document_id)
        self.records.pop(document_id, None)


def test_store_pdf_copies_file_and_hashes_public_token(workspace_path, monkeypatch):
    repository = FakeDocumentRepository()
    service = DocumentVaultService(repository, workspace_path / "vault", ttl_hours=24)
    monkeypatch.setattr(service, "_generate_token", lambda: "public-token")
    source_path = workspace_path / "source.pdf"
    source_path.write_bytes(b"%PDF-1.4\nfake pdf\n")

    registration = service.store_pdf(source_path, "source.pdf")

    expected_hash = hash_token("public-token")
    stored_path = Path(registration.record.stored_path)
    assert registration.token == "public-token"
    assert registration.record.token_hash == expected_hash
    assert stored_path.name == f"{expected_hash}.pdf"
    assert stored_path.read_bytes() == b"%PDF-1.4\nfake pdf\n"


def test_lookup_removes_expired_record_and_file(workspace_path, monkeypatch):
    repository = FakeDocumentRepository()
    service = DocumentVaultService(repository, workspace_path / "vault", ttl_hours=24)
    monkeypatch.setattr(service, "_generate_token", lambda: "expired-token")
    source_path = workspace_path / "expired.pdf"
    source_path.write_bytes(b"%PDF-1.4\nfake pdf\n")
    registration = service.store_pdf(source_path, "expired.pdf")
    expired_record = DocumentVaultRecord(
        id=registration.record.id,
        token_hash=registration.record.token_hash,
        filename=registration.record.filename,
        stored_path=registration.record.stored_path,
        mime_type=registration.record.mime_type,
        file_size=registration.record.file_size,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    repository.records[registration.record.id] = expired_record

    lookup = service.lookup("expired-token")

    assert lookup.status == "expired"
    assert repository.deleted_ids == [registration.record.id]
    assert not Path(registration.record.stored_path).exists()


def test_cleanup_expired_documents_removes_only_expired_files(
    workspace_path,
    monkeypatch,
):
    repository = FakeDocumentRepository()
    service = DocumentVaultService(repository, workspace_path / "vault", ttl_hours=24)

    monkeypatch.setattr(service, "_generate_token", lambda: "expired-token")
    expired_source = workspace_path / "expired.pdf"
    expired_source.write_bytes(b"expired")
    expired_registration = service.store_pdf(expired_source, "expired.pdf")
    repository.records[expired_registration.record.id] = DocumentVaultRecord(
        id=expired_registration.record.id,
        token_hash=expired_registration.record.token_hash,
        filename=expired_registration.record.filename,
        stored_path=expired_registration.record.stored_path,
        mime_type=expired_registration.record.mime_type,
        file_size=expired_registration.record.file_size,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )

    monkeypatch.setattr(service, "_generate_token", lambda: "active-token")
    active_source = workspace_path / "active.pdf"
    active_source.write_bytes(b"active")
    active_registration = service.store_pdf(active_source, "active.pdf")

    removed = service.cleanup_expired_documents()

    assert removed == 1
    assert expired_registration.record.id in repository.deleted_ids
    assert not Path(expired_registration.record.stored_path).exists()
    assert Path(active_registration.record.stored_path).exists()


def test_supabase_repository_normalizes_common_dashboard_values():
    repository = SupabaseDocumentVaultRepository(
        supabase_url="https://example.supabase.co/rest/v1/",
        service_role_key="fake-key",
        table_name="public.document_vault",
    )

    assert repository.supabase_url == "https://example.supabase.co"
    assert repository.table_name == "document_vault"
