import re
import logging

logger = logging.getLogger(__name__)

async def process_ocr(ctx, image_url: str) -> dict:
    """
    Simulates OCR processing for Loot Screenshots.
    In prod, this would download the image and run PaddleOCR.
    Here, we mock the result to return a valid aUEC amount.
    """
    logger.info(f"Processing OCR for {image_url}")

    # Mock Result: We assume the screenshot contains "1,250,000 aUEC"
    # In a real impl, we would use:
    # ocr = PaddleOCR(...)
    # result = ocr.ocr(image_path)
    # text = extract_text(result)

    # Regex to find currency
    # Pattern: Digit,Digit... aUEC

    mock_text = "Contract Complete. Reward: 1,250,450 aUEC. Bonus: 0."

    # Extract Amount
    # Remove commas
    clean_text = mock_text.replace(",", "")
    match = re.search(r'(\d+)\s*aUEC', clean_text)

    if match:
        amount = int(match.group(1))
        return {"status": "SUCCESS", "amount": amount, "raw_text": mock_text}
    else:
        return {"status": "FAILED", "reason": "No aUEC amount found in screenshot."}
