from fastapi import UploadFile

from app.schemas.document_schema import DocumentCreate


class DocumentIngestionService:
    def normalize_text(self, text: str) -> str:
        return "\n".join(line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip())

    async def from_upload(self, file: UploadFile) -> DocumentCreate:
        name = file.filename or "Uploaded document"
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else "txt"
        raw = await file.read()
        if extension == "pdf":
            content = self._extract_pdf(raw)
            source_type = "pdf"
        else:
            content = raw.decode("utf-8", errors="ignore")
            source_type = "markdown" if extension in {"md", "markdown"} else "text"
        return DocumentCreate(title=name, content=self.normalize_text(content), source_type=source_type)

    def _extract_pdf(self, raw: bytes) -> str:
        try:
            from io import BytesIO

            from pypdf import PdfReader

            reader = PdfReader(BytesIO(raw))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
