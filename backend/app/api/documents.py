"""Document Upload and Management API routes."""

import os
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db, get_current_user
from app.db.models import User, Document
from app.db.database import async_session_factory
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.document_service import process_document
from app.services.vector_service import get_qdrant_client, delete_document_vectors

router = APIRouter(tags=["Documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def run_document_processing(document_id: UUID, file_path: str):
    """Wrapper function to handle background session creation for document parsing."""
    async with async_session_factory() as session:
        try:
            await process_document(document_id, file_path, session)
        except Exception as e:
            print(f"Background task failed for document {document_id}: {e}")


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a PDF or CSV document. Schedules chunking, embedding, and indexing in the background.
    """
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in (".pdf", ".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and CSV files are supported at this time."
        )

    # Create document record
    doc_id = uuid4()
    safe_filename = f"{doc_id}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Read and save file content
    try:
        content = await file.read()
        file_size = len(content)
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}"
        )

    # Save initial pending record in DB
    new_doc = Document(
        id=doc_id,
        user_id=current_user.id,
        filename=file.filename,
        file_type=file_ext[1:],  # "pdf" or "csv"
        file_size=file_size,
        upload_status="pending",
        chunk_count=0
    )
    
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)

    # Start background task for text extraction and indexing
    background_tasks.add_task(run_document_processing, doc_id, file_path)

    return new_doc


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all documents uploaded by the authenticated user."""
    result = await db.execute(
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return {"documents": docs}


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete document metadata, physical file, and corresponding vectors from Qdrant."""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.user_id == current_user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # 1. Delete physical file
    file_path = os.path.join(UPLOAD_DIR, f"{doc.id}.{doc.file_type}")
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Failed to delete file {file_path}: {e}")

    # 2. Delete vectors from Qdrant
    try:
        qdrant = get_qdrant_client()
        delete_document_vectors(qdrant, doc.id)
    except Exception as e:
        print(f"Failed to delete vectors for document {doc.id}: {e}")

    # 3. Delete from DB (cascade deletes DocumentChunks)
    await db.delete(doc)
    await db.commit()
    
    return
