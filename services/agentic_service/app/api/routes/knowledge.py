"""
Per-project domain knowledge document routes.

These let a human upload/list/delete/download domain knowledge files (PDF/DOCX/TXT/MD) for one
project, so Domain Agent can either retrieve them via normal similarity search or have a specific
one pinned by document_id when a human references it directly in chat (see
domain_schema.py's referenced_document_ids).
"""

from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from app.schemas.knowledge_schema import KnowledgeDocumentResponse
from app.services.in_memory_store import store
from app.services.knowledge_document_service import knowledge_document_service

router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["Knowledge"])


def _validate_project(project_id: str):
    project = store.projects.get(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.post("/documents", response_model=KnowledgeDocumentResponse)
async def upload_knowledge_document(project_id: str, file: UploadFile = File(...)):
    """
    Upload one domain knowledge document (PDF/DOCX/TXT/MD) for this project.

    Extracts, chunks, embeds, and stores it in the Domain Agent's vector store, tagged with this
    project's ID so it can be retrieved (or pinned by document_id) for this project's features
    only -- never leaked into another project's retrieval.
    """
    _validate_project(project_id)

    file_bytes = await file.read()

    try:
        return knowledge_document_service.upload_document(
            project_id=project_id,
            file_bytes=file_bytes,
            filename=file.filename,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
def list_knowledge_documents(project_id: str):
    """
    List every domain knowledge document uploaded for this project.
    """
    _validate_project(project_id)
    return knowledge_document_service.list_documents(project_id)


@router.delete("/documents/{document_id}", status_code=204)
def delete_knowledge_document(project_id: str, document_id: str):
    """
    Delete an uploaded domain knowledge document -- its vector chunks, raw file, and metadata
    record.
    """
    _validate_project(project_id)
    document = knowledge_document_service.get_document(document_id)

    if not document or document.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Knowledge document not found")

    knowledge_document_service.delete_document(document_id)


@router.get("/documents/{document_id}/download")
def download_knowledge_document(project_id: str, document_id: str):
    """
    Download an uploaded document's original raw file, exactly as uploaded.
    """
    _validate_project(project_id)
    document = knowledge_document_service.get_document(document_id)

    if not document or document.get("project_id") != project_id:
        raise HTTPException(status_code=404, detail="Knowledge document not found")

    try:
        body = knowledge_document_service.read_document_bytes(document_id)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Knowledge document file not found on disk")

    filename = document["original_filename"]

    return Response(
        content=body,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
