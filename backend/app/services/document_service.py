"""Document service for PDF parsing, text extraction, vision fallback, and embedding indexing."""

import base64
import os
import uuid
from typing import Any, Optional
from uuid import UUID

import fitz  # PyMuPDF
from fastapi import HTTPException
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.db.models import Document, DocumentChunk
from app.services.vector_service import get_qdrant_client, upsert_document_chunks

settings = get_settings()


async def extract_page_via_vision(page_image_bytes: bytes) -> str:
    """Render page as image and run GPT-4o vision to extract text and tables."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    base64_image = base64.b64encode(page_image_bytes).decode("utf-8")
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all textual and tabular content from this PDF page image. "
                            "Format tables in clean Markdown format. "
                            "Do not include any greeting, intro, or wrapping markdown code blocks (e.g. do not wrap in ```markdown)."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        temperature=0.0,
    )
    return response.choices[0].message.content or ""


async def process_document(document_id: UUID, file_path: str, db: AsyncSession) -> None:
    """
    Parse document, extract pages (with vision fallback for tables/scans),
    generate chunks, embed, and index in PostgreSQL + Qdrant.
    """
    # 1. Fetch document from DB
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document record not found")

    # 2. Update status to processing
    doc.upload_status = "processing"
    await db.commit()

    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at {file_path}")

        # 3. Extract text page by page / row by row
        extracted_pages = []
        
        if doc.file_type == "csv":
            import csv
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            formatted_text_parts = []
            for idx, row in enumerate(rows):
                row_desc = f"Row {idx+1}: " + ", ".join(f"{k}: {v}" for k, v in row.items() if v is not None)
                formatted_text_parts.append(row_desc)
                
            # Pack 20 rows per chunk page
            rows_per_page = 20
            for start_idx in range(0, len(formatted_text_parts), rows_per_page):
                page_num = (start_idx // rows_per_page) + 1
                page_text = "\n".join(formatted_text_parts[start_idx:start_idx+rows_per_page])
                extracted_pages.append({
                    "page_number": page_num,
                    "content": page_text,
                    "chunk_type": "csv_table"
                })
        else:
            pdf_doc = fitz.open(file_path)
            for page_idx in range(len(pdf_doc)):
                page = pdf_doc[page_idx]
                page_num = page_idx + 1
                raw_text = page.get_text()
                
                # Check if vision fallback is needed (has tables or is scanned/image-based)
                has_tables = len(page.find_tables().tables) > 0
                is_scanned = len(raw_text.strip()) < 150
                
                if has_tables or is_scanned:
                    # Render page to PNG bytes
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    page_text = await extract_page_via_vision(img_bytes)
                    chunk_type = "table" if has_tables else "image"
                else:
                    page_text = raw_text
                    chunk_type = "text"
                
                extracted_pages.append({
                    "page_number": page_num,
                    "content": page_text,
                    "chunk_type": chunk_type
                })
            
            pdf_doc.close()

        # 4. Chunk the content
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        
        chunks_to_insert = []
        qdrant_chunks = []
        chunk_idx = 0
        
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=settings.openai_api_key
        )

        for page_data in extracted_pages:
            splits = text_splitter.split_text(page_data["content"])
            for split in splits:
                if not split.strip():
                    continue
                
                chunk_id = uuid.uuid4()
                # Generate embedding
                vector = await embeddings_model.aembed_query(split)
                
                # DB Chunk Object
                db_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_idx,
                    content=split,
                    page_number=page_data["page_number"],
                    chunk_type=page_data["chunk_type"],
                    metadata_json={"source": doc.filename}
                )
                chunks_to_insert.append(db_chunk)
                
                # Qdrant Payload
                qdrant_chunks.append({
                    "id": chunk_id,
                    "vector": vector,
                    "document_id": document_id,
                    "content": split,
                    "page_number": page_data["page_number"],
                    "chunk_type": page_data["chunk_type"],
                    "metadata": {"source": doc.filename}
                })
                
                chunk_idx += 1

        # 5. Insert to DB
        db.add_all(chunks_to_insert)
        
        # 6. Upsert to Qdrant
        qdrant_client = get_qdrant_client()
        upsert_document_chunks(qdrant_client, qdrant_chunks)
        
        # 7. Update status to completed
        doc.upload_status = "completed"
        doc.chunk_count = len(chunks_to_insert)
        await db.commit()
        print(f"Document {doc.filename} processed successfully. Indexed {doc.chunk_count} chunks.")

    except Exception as e:
        # Failed status
        await db.rollback()
        # Refetch inside error block to ensure session has it
        try:
            result = await db.execute(select(Document).where(Document.id == document_id))
            doc_err = result.scalar_one_or_none()
            if doc_err:
                doc_err.upload_status = "failed"
                await db.commit()
        except Exception as inner_e:
            print(f"Failed to set document status to failed: {inner_e}")
            
        print(f"Error processing document {document_id}: {e}")
        raise e
