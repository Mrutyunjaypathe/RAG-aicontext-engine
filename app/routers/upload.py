"""
/upload router — accepts PDF, TXT, DOCX files,
runs the ingestion pipeline, and builds the FAISS index.
"""
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import UploadResponse
from app.models.store import add_document
from app.services.ingestion import ingest_document
from app.services.retrieval import build_index

router = APIRouter(prefix="/upload", tags=["Document Upload"])
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(settings.upload_dir)


@router.post(
    "/",
    response_model=UploadResponse,
    summary="Upload a document",
    description="Upload a PDF, TXT, or DOCX file to add it to the knowledge base.",
)
async def upload_document(file: UploadFile = File(...)):
    # ── Validate file ─────────────────────────────────────────────────────────
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower().lstrip(".")

    if ext not in settings.allowed_ext_list:
        raise HTTPException(
            status_code=400,
            detail=f"File type '.{ext}' not supported. Allowed: {settings.allowed_ext_list}",
        )

    # ── Read & size-check ─────────────────────────────────────────────────────
    content = await file.read()
    size_bytes = len(content)
    max_bytes = settings.max_upload_size_mb * 1024 * 1024

    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_bytes/1024/1024:.1f} MB). Max: {settings.max_upload_size_mb} MB",
        )

    # ── Save to disk ──────────────────────────────────────────────────────────
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / filename

    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved upload: {filename} ({size_bytes} bytes)")

    # ── Ingest & index ────────────────────────────────────────────────────────
    try:
        doc_id, chunks = ingest_document(save_path)
        build_index(doc_id, filename, chunks)
        add_document(doc_id, filename, len(chunks), size_bytes)
    except Exception as e:
        # Clean up saved file on failure
        save_path.unlink(missing_ok=True)
        logger.error(f"Ingestion failed for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return UploadResponse(
        document_id=doc_id,
        filename=filename,
        chunks_created=len(chunks),
        message=f"✅ Document '{filename}' ingested successfully with {len(chunks)} chunks.",
    )


@router.get("/documents", summary="List all uploaded documents")
async def list_documents():
    """Return metadata for all documents in the knowledge base."""
    from app.models.store import get_all_documents
    docs = get_all_documents()
    return {"documents": docs, "total": len(docs)}


@router.delete("/{doc_id}", summary="Delete a document")
async def delete_document(doc_id: str):
    from app.models.store import get_document, remove_document
    from app.services.retrieval import _indexes
    
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 1. Remove the original file
    file_path = UPLOAD_DIR / doc["filename"]
    file_path.unlink(missing_ok=True)
    
    # 2. Remove FAISS vector index files
    from app.config import settings
    vector_dir = Path(settings.vector_dir)
    (vector_dir / f"{doc_id}.faiss").unlink(missing_ok=True)
    (vector_dir / f"{doc_id}_chunks.pkl").unlink(missing_ok=True)
    
    # 3. Remove from memory if currently loaded
    if doc_id in _indexes:
        del _indexes[doc_id]
        
    # 4. Remove from metadata store
    remove_document(doc_id)
    
    logger.info(f"Deleted document and vectors for {doc['filename']} ({doc_id})")
    return {"message": f"Document '{doc['filename']}' deleted successfully"}
