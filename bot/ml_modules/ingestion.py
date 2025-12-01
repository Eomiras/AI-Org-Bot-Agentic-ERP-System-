import re
import os
import logging
import json
import redis.asyncio as redis
from pypdf import PdfReader
from bot.core.knowledge.ingest import add_document
from bot.core.config import settings

logger = logging.getLogger(__name__)

# --- PII PATTERNS ---
EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_PATTERN = r'\+?[0-9]{1,4}?[-.\s]?\(?[0-9]{1,3}?\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}'
# Simple name guard (very basic, looks for "Name: X")
NAME_PATTERN = r'(Name|Nom):\s*[A-Z][a-z]+'

def sanitize_text(text: str) -> tuple[str, int]:
    """
    Removes PII from text.
    Returns: (cleaned_text, pii_count)
    """
    pii_count = 0

    # Redact Emails
    emails = re.findall(EMAIL_PATTERN, text)
    pii_count += len(emails)
    text = re.sub(EMAIL_PATTERN, "[REDACTED_EMAIL]", text)

    # Redact Phones
    phones = re.findall(PHONE_PATTERN, text)
    # Simple heuristic to avoid false positives on dates/numbers: require at least 8 digits total
    real_phones = [p for p in phones if sum(c.isdigit() for c in p) > 7]
    pii_count += len(real_phones)
    for p in real_phones:
        text = text.replace(p, "[REDACTED_PHONE]")

    return text, pii_count

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text

async def ingest_task(ctx, file_path: str, metadata: dict):
    """
    Arq Task: Processes a document and ingests it into Qdrant.
    """
    logger.info(f"Starting ingestion for {file_path}")

    if not os.path.exists(file_path):
        return {"status": "FAILED", "reason": "File not found"}

    try:
        # 1. Parsing
        text = ""
        if file_path.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            return {"status": "FAILED", "reason": "Unsupported format"}

        if not text.strip():
            return {"status": "FAILED", "reason": "Empty document"}

        # 2. PII Sanitization
        cleaned_text, pii_hits = sanitize_text(text)

        # PII Guard: If too many hits, abort (as per Shield Operator design)
        if pii_hits > 3:
            logger.warning(f"PII Contamination detected: {pii_hits} hits.")
            return {
                "status": "PII_CONTAMINATION",
                "reason": f"Detected {pii_hits} PII instances. Ingestion aborted.",
                "pii_count": pii_hits
            }

        # 3. Vectorization & Ingestion
        # add_document is synchronous (uses LangChain), but Arq runs in a thread/process usually?
        # Arq tasks are async. add_document might block the loop if it does heavy CPU work.
        # However, for this implementation, we'll run it directly.
        # In a high-load env, we'd run_in_executor.

        num_chunks = add_document(cleaned_text, metadata)

        # Cleanup
        try:
            os.remove(file_path)
        except:
            pass

        result = {
            "status": "SUCCESS",
            "chunks": num_chunks,
            "pii_redacted": pii_hits,
            "filename": metadata.get("source", "Unknown"),
            "channel_id": metadata.get("channel_id"),
            "user_id": metadata.get("author_id")
        }

        # Publish Event to Redis for Bot to pick up
        try:
            r = redis.Redis.from_url(settings.redis_url)
            await r.publish("ingestion_events", json.dumps(result))
            await r.aclose()
        except Exception as pub_err:
            logger.error(f"Redis Publish Error: {pub_err}")

        return result

    except Exception as e:
        logger.error(f"Ingestion Error: {e}")
        # Publish Failure
        try:
            r = redis.Redis.from_url(settings.redis_url)
            fail_msg = {
                "status": "FAILED",
                "reason": str(e),
                "filename": metadata.get("source", "Unknown"),
                "channel_id": metadata.get("channel_id")
            }
            await r.publish("ingestion_events", json.dumps(fail_msg))
            await r.aclose()
        except:
            pass

        return {"status": "FAILED", "reason": str(e)}
