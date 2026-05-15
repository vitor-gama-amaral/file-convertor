import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class VirusTotalError(RuntimeError):
    """Raised when VirusTotal cannot return a usable response."""


@dataclass(frozen=True)
class VirusTotalResult:
    status: str
    message: str
    sha256: str
    stats: dict[str, int]
    analysis_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "sha256": self.sha256,
            "stats": self.stats,
            "analysis_id": self.analysis_id,
        }


class VirusTotalClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.virustotal.com/api/v3",
        timeout: int = 20,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def scan_file(self, content: bytes, filename: str) -> VirusTotalResult:
        sha256 = hashlib.sha256(content).hexdigest()

        try:
            return self._get_file_report(sha256)
        except FileNotFoundError:
            analysis_id = self._upload_file(content, filename)
            return self.get_analysis_result(analysis_id, sha256)

    def scan_file_hash(self, content: bytes) -> VirusTotalResult:
        sha256 = hashlib.sha256(content).hexdigest()
        return self._get_file_report(sha256)

    def _get_file_report(self, sha256: str) -> VirusTotalResult:
        url = f"{self.base_url}/files/{sha256}"
        request = Request(url, headers={"x-apikey": self.api_key})

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                raise FileNotFoundError from error
            raise VirusTotalError("Nao foi possivel consultar a VirusTotal.") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise VirusTotalError("Nao foi possivel consultar a VirusTotal.") from error

        attributes = payload.get("data", {}).get("attributes", {})
        return self._build_result(sha256, attributes.get("last_analysis_stats", {}))

    def _upload_file(self, content: bytes, filename: str) -> str:
        boundary = f"----FileConvertor{uuid.uuid4().hex}"
        body = self._build_multipart_body(boundary, content, filename)
        request = Request(
            f"{self.base_url}/files",
            data=body,
            headers={
                "x-apikey": self.api_key,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise VirusTotalError(
                "Nao foi possivel enviar o arquivo para analise."
            ) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise VirusTotalError(
                "Nao foi possivel enviar o arquivo para analise."
            ) from error

        analysis_id = payload.get("data", {}).get("id")
        if not analysis_id:
            raise VirusTotalError("A VirusTotal nao retornou o codigo da analise.")
        return str(analysis_id)

    def get_analysis_result(self, analysis_id: str, sha256: str) -> VirusTotalResult:
        url = f"{self.base_url}/analyses/{analysis_id}"
        request = Request(url, headers={"x-apikey": self.api_key})

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise VirusTotalError("Nao foi possivel consultar a analise.") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise VirusTotalError("Nao foi possivel consultar a analise.") from error

        attributes = payload.get("data", {}).get("attributes", {})
        if attributes.get("status") == "completed":
            return self._build_result(sha256, attributes.get("stats", {}))

        return VirusTotalResult(
            status="queued",
            message=(
                "Arquivo enviado para analise. A VirusTotal ainda esta processando "
                "o resultado."
            ),
            sha256=sha256,
            stats={},
            analysis_id=analysis_id,
        )

    def _build_result(self, sha256: str, stats: dict[str, Any]) -> VirusTotalResult:
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))

        if malicious > 0:
            status = "malicious"
            message = "A VirusTotal identificou possiveis ameacas neste arquivo."
        elif suspicious > 0:
            status = "suspicious"
            message = "A VirusTotal marcou o arquivo como suspeito."
        else:
            status = "safe"
            message = "Nenhuma ameaca foi encontrada na ultima analise conhecida."

        return VirusTotalResult(
            status=status,
            message=message,
            sha256=sha256,
            stats={
                "harmless": int(stats.get("harmless", 0)),
                "malicious": malicious,
                "suspicious": suspicious,
                "undetected": int(stats.get("undetected", 0)),
            },
        )

    def _build_multipart_body(
        self,
        boundary: str,
        content: bytes,
        filename: str,
    ) -> bytes:
        safe_filename = filename.replace('"', "")
        header = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; '
            f'filename="{safe_filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
        return header + content + footer
