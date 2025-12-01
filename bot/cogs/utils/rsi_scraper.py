import httpx
from bs4 import BeautifulSoup
from bot.core.logger import logger

async def fetch_rsi_bio(handle: str) -> str:
    """
    Scrapes the RSI public profile and returns the raw bio text.
    Target URL: https://robertsspaceindustries.com/en/citizens/{handle}
    """
    url = f"https://robertsspaceindustries.com/en/citizens/{handle}"

    # Headers are important to avoid being blocked as a bot
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, follow_redirects=True)

            if response.status_code == 404:
                logger.warning("rsi_scrape_404", handle=handle)
                return None

            if response.status_code != 200:
                logger.error("rsi_scrape_error", status=response.status_code, handle=handle)
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # The bio is usually in a div with class 'bio' or 'profile-content' -> 'bio'
            # Looking at RSI source code structure (approximation, may need adjustment if RSI changes layout)
            # Typically: <div class="bio"> ... </div> or inside the profile-content

            # Let's try finding the bio section.
            # Note: RSI structure is complex. We search for the meta description or the specific bio div.
            # The reliable way is often looking for 'div.bio > div.value'

            bio_element = soup.select_one("div.bio div.value")
            if bio_element:
                return bio_element.get_text(strip=True)

            # Fallback check
            return ""

        except Exception as e:
            logger.error("rsi_scrape_exception", error=str(e))
            return None

def verify_token_in_bio(bio_text: str, token: str) -> bool:
    """
    Checks if the verification token exists in the bio text.
    """
    if not bio_text:
        return False
    return token in bio_text
