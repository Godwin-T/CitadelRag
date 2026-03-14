from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: str
    title: str
    status: str
    source_type: str


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str


class DocumentPreviewOut(BaseModel):
    document_id: str
    title: str
    status: str
    source_type: str
    preview_text: str
