"""Message endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger

from src.api.dependencies import get_repository, get_job_queue
from src.api.schemas import (
    MessageSubmitResponse,
    JobStatusResponse,
    MessageResponse,
)
from src.config.json_config import app_config
from src.database import ConversationRepository
from src.pdf.processor import PDFProcessor
from src.redis import JobQueue

MAX_PDF_SIZE = 10 * 1024 * 1024  # 10 MB

router = APIRouter()


@router.get(
    "/conversations/{conv_id}/messages",
    response_model=list[MessageResponse]
)
async def get_messages(
    conv_id: UUID,
    repo: ConversationRepository = Depends(get_repository),
):
    """
    Get all messages for a conversation.

    Args:
        conv_id: Conversation UUID
        repo: Conversation repository

    Returns:
        List of messages

    Raises:
        HTTPException: If conversation not found
    """
    logger.info(f"Getting messages for conversation {conv_id}")

    # Check if conversation exists
    conversation = await repo.get_conversation(conv_id)
    if not conversation:
        logger.warning(f"Conversation {conv_id} not found")
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get messages
    messages = await repo.get_messages(conv_id)

    response = [
        MessageResponse(
            mess_id=msg.mess_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
        )
        for msg in messages
    ]

    logger.info(f"Retrieved {len(messages)} messages for conversation {conv_id}")
    return response


@router.post(
    "/conversations/{conv_id}/messages",
    response_model=MessageSubmitResponse,
    status_code=202
)
async def send_message(
    conv_id: UUID,
    content: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    repo: ConversationRepository = Depends(get_repository),
    job_queue: JobQueue = Depends(get_job_queue),
):
    """
    Send a message to a conversation, optionally with PDF attachments.

    Accepts multipart/form-data with text content and optional PDF files.
    Each PDF is validated (type, size) and chunked for later indexing.

    Args:
        conv_id: Conversation UUID
        content: Message text
        files: Optional PDF file uploads (max 10 MB each)
        repo: Conversation repository
        job_queue: Job queue

    Returns:
        Message ID and job ID for status tracking
    """
    logger.info(f"Sending message to conversation {conv_id}")

    # Validate uploaded files
    for f in files:
        if f.content_type != "application/pdf":
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' is not a PDF",
            )
        file_bytes = await f.read()
        if len(file_bytes) > MAX_PDF_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' exceeds 10 MB limit",
            )
        await f.seek(0)

    # Process PDFs into chunks
    pdf_chunks: list[dict] | None = None
    if files:
        processor = PDFProcessor(chunker_config=app_config.pdf.chunker)
        pdf_chunks = []
        for f in files:
            file_bytes = await f.read()
            chunks = processor.process_pdf(file_bytes)
            pdf_chunks.extend(
                {"text": chunk, "filename": f.filename} for chunk in chunks
            )
            logger.info(f"Processed '{f.filename}': {len(chunks)} chunks")

    # Check if conversation exists, create if not
    conversation = await repo.get_conversation(conv_id)
    if not conversation:
        logger.info(f"Creating new conversation {conv_id}")
        conversation = await repo.create_conversation(conv_id=conv_id)

    # Save user message to database
    user_message = await repo.add_message(
        conv_id,
        role="User",
        content=content,
    )
    logger.info(f"Saved user message {user_message.mess_id} to database")

    # Create job in Redis
    job_id = await job_queue.create_job(conv_id, content, pdf_chunks=pdf_chunks)
    logger.info(f"Created job {job_id} in Redis")

    return MessageSubmitResponse(
        mess_id=user_message.mess_id,
        job_id=job_id,
        status="Pending"
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    job_queue: JobQueue = Depends(get_job_queue),
):
    """
    Get job processing status.

    Args:
        job_id: Job identifier
        job_queue: Job queue

    Returns:
        Job status information

    Raises:
        HTTPException: If job not found
    """
    logger.debug(f"Checking status for job {job_id}")

    # Get job status from Redis
    job_data = await job_queue.get_job_status(job_id)

    if not job_data:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job_id,
        conversation_id=job_data["conversation_id"],
        status=job_data["status"],
        result=job_data.get("result"),
        query=job_data.get("query"),
    )
