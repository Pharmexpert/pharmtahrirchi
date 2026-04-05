import os
import logging
import google.generativeai as genai

logger = logging.getLogger("ai")

_gemini_model = None
_anthropic_client = None


def get_gemini():
    global _gemini_model
    if not _gemini_model:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            _gemini_model = genai.GenerativeModel("models/gemini-2.0-flash")
    return _gemini_model


def get_anthropic():
    global _anthropic_client
    if not _anthropic_client:
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            pass
    return _anthropic_client


def get_client():
    """Returns Gemini model (primary). Use generate_ai_content() for dual-AI calls."""
    return get_gemini() or (True if get_anthropic() else None)


async def generate_ai_content(prompt: str) -> str:
    """
    Dual-AI content generation:
      - Primary: Google Gemini 2.0 Flash
      - Fallback: Anthropic Claude (claude-3-5-haiku)
    Returns the text response or raises if both fail.
    """
    gemini = get_gemini()
    if gemini:
        try:
            response = gemini.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.warning(f"[AI] Gemini failed: {e} — switching to Anthropic...")

    anthropic_client = get_anthropic()
    if anthropic_client:
        try:
            msg = anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            logger.error(f"[AI] Anthropic also failed: {e}")
            raise

    raise Exception("No AI client configured. Set GOOGLE_API_KEY or ANTHROPIC_API_KEY.")
