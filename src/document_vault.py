import json
import os
import secrets
import shutil
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class DocumentVaultError(RuntimeError):
    """Raised when the document vault cannot complete an operation."""


@dataclass(frozen=True)
class DocumentVaultRecord:
    id: str
    token_hash: str
    filename: str
    stored_path: str
    mime_type: str
    file_size: int
    expires_at: datetime
    created_at: datetime | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DocumentVaultRecord":
        return cls(
            id=str(payload["id"]),
            token_hash=str(payload["token_hash"]),
            filename=str(payload["filename"]),
            stored_path=str(payload["stored_path"]),
            mime_type=str(payload.get("mime_type") or "application/pdf"),
            file_size=int(payload.get("file_size") or 0),
            expires_at=_parse_datetime(str(payload["expires_at"])),
            created_at=_parse_datetime(str(payload["created_at"]))
            if payload.get("created_at")
            else None,
        )

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(timezone.utc)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass(frozen=True)
class DocumentVaultRegistration:
    token: str
    record: DocumentVaultRecord


@dataclass(frozen=True)
class DocumentVaultLookup:
    status: str
    record: DocumentVaultRecord | None = None


class SupabaseDocumentVaultRepository:
    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        table_name: str = "document_vault",
        timeout: int = 20,
    ):
        self.supabase_url = _normalize_supabase_url(supabase_url)
        self.service_role_key = service_role_key
        self.table_name = _normalize_table_name(table_name)
        self.timeout = timeout

    def create(self, payload: dict[str, Any]) -> DocumentVaultRecord:
        rows = self._request(
            "POST",
            self.table_name,
            payload=payload,
            extra_headers={"Prefer": "return=representation"},
        )
        if not rows:
            raise DocumentVaultError("O Supabase nao retornou o documento criado.")
        return DocumentVaultRecord.from_payload(rows[0])

    def find_by_token_hash(self, token_hash: str) -> DocumentVaultRecord | None:
        query = urlencode(
            {
                "token_hash": f"eq.{token_hash}",
                "select": "*",
                "limit": "1",
            }
        )
        rows = self._request("GET", f"{self.table_name}?{query}")
        if not rows:
            return None
        return DocumentVaultRecord.from_payload(rows[0])

    def list_expired(self, now: datetime) -> list[DocumentVaultRecord]:
        query = urlencode(
            {
                "expires_at": f"lt.{now.isoformat()}",
                "select": "*",
            }
        )
        rows = self._request("GET", f"{self.table_name}?{query}")
        return [DocumentVaultRecord.from_payload(row) for row in rows]

    def delete_by_id(self, document_id: str) -> None:
        query = urlencode({"id": f"eq.{document_id}"})
        self._request("DELETE", f"{self.table_name}?{query}")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.supabase_url}/rest/v1/{path}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        headers.update(extra_headers or {})

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise DocumentVaultError(
                f"Nao foi possivel acessar o cofre de documentos: {detail}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise DocumentVaultError(
                "Nao foi possivel acessar o cofre de documentos."
            ) from error

        if not content:
            return []

        try:
            return json.loads(content.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise DocumentVaultError(
                "O Supabase retornou uma resposta invalida."
            ) from error


class DocumentVaultService:
    def __init__(
        self,
        repository: SupabaseDocumentVaultRepository,
        storage_dir: Path,
        ttl_hours: int = 24,
    ):
        self.repository = repository
        self.storage_dir = storage_dir
        self.ttl_hours = ttl_hours
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls, storage_dir: Path) -> "DocumentVaultService":
        supabase_url = os.environ.get("SUPABASE_URL")
        service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not service_role_key:
            raise DocumentVaultError(
                "Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY."
            )

        ttl_hours = int(os.environ.get("DOCUMENT_VAULT_TTL_HOURS", "24"))
        table_name = os.environ.get("SUPABASE_DOCUMENT_TABLE", "document_vault")
        repository = SupabaseDocumentVaultRepository(
            supabase_url=supabase_url,
            service_role_key=service_role_key,
            table_name=table_name,
        )
        return cls(repository=repository, storage_dir=storage_dir, ttl_hours=ttl_hours)

    def store_pdf(
        self,
        source_path: Path,
        original_filename: str,
    ) -> DocumentVaultRegistration:
        if source_path.suffix.lower() != ".pdf":
            raise DocumentVaultError("Apenas arquivos PDF podem ser registrados.")

        token = self._generate_token()
        token_hash = hash_token(token)
        stored_path = self.storage_dir / f"{token_hash}.pdf"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.ttl_hours)

        try:
            shutil.copy2(source_path, stored_path)
            record = self.repository.create(
                {
                    "token_hash": token_hash,
                    "filename": _safe_pdf_filename(original_filename),
                    "stored_path": str(stored_path),
                    "mime_type": "application/pdf",
                    "file_size": stored_path.stat().st_size,
                    "expires_at": expires_at.isoformat(),
                }
            )
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise

        return DocumentVaultRegistration(token=token, record=record)

    def lookup(self, token: str) -> DocumentVaultLookup:
        token_hash = hash_token(token)
        record = self.repository.find_by_token_hash(token_hash)

        if record is None:
            return DocumentVaultLookup(status="expired")

        file_path = Path(record.stored_path)
        if record.is_expired or not file_path.exists():
            self.remove(record)
            return DocumentVaultLookup(status="expired")

        return DocumentVaultLookup(status="available", record=record)

    def remove(self, record: DocumentVaultRecord) -> None:
        Path(record.stored_path).unlink(missing_ok=True)
        self.repository.delete_by_id(record.id)

    def cleanup_expired_documents(self) -> int:
        expired_records = self.repository.list_expired(datetime.now(timezone.utc))
        for record in expired_records:
            self.remove(record)
        return len(expired_records)

    def _generate_token(self) -> str:
        return secrets.token_urlsafe(9)


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def start_document_cleanup_scheduler(app: Any) -> None:
    if app.extensions.get("document_cleanup_scheduler_started"):
        return

    app.extensions["document_cleanup_scheduler_started"] = True
    interval_seconds = int(os.environ.get("DOCUMENT_CLEANUP_INTERVAL_SECONDS", "86400"))
    initial_delay_seconds = int(
        os.environ.get("DOCUMENT_CLEANUP_INITIAL_DELAY_SECONDS", "60")
    )

    def run() -> None:
        time.sleep(initial_delay_seconds)
        while True:
            try:
                service = app.extensions.get("document_vault")
                if service is None:
                    service = DocumentVaultService.from_env(
                        Path(app.config["DOCUMENT_VAULT_DIR"])
                    )
                    app.extensions["document_vault"] = service
                service.cleanup_expired_documents()
            except Exception as error:
                app.logger.warning("Falha ao limpar documentos expirados: %s", error)
            time.sleep(interval_seconds)

    thread = threading.Thread(target=run, name="document-vault-cleanup", daemon=True)
    thread.start()


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_supabase_url(value: str) -> str:
    url = value.strip().strip("\"'").rstrip("/")
    rest_path = "/rest/v1"
    if rest_path in url:
        url = url.split(rest_path, 1)[0]
    return url.rstrip("/")


def _normalize_table_name(value: str) -> str:
    table_name = value.strip().strip("\"'").strip("/")
    if table_name.startswith("public."):
        table_name = table_name.removeprefix("public.")

    if not table_name or "/" in table_name or "?" in table_name:
        raise DocumentVaultError(
            "Configure SUPABASE_DOCUMENT_TABLE apenas com o nome da tabela."
        )

    return table_name


def _safe_pdf_filename(filename: str) -> str:
    name = Path(filename).name or "documento.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{Path(name).stem}.pdf"
    return quote(name, safe=" ._-()")
