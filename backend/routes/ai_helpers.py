import os
import logging
import asyncio

logger = logging.getLogger("ai")

_gemini_client = None
_anthropic_client = None


def get_gemini():
    global _gemini_client
    if not _gemini_client:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                from google import genai
                _gemini_client = genai.Client(api_key=api_key)
            except ImportError:
                # Fallback to old package
                import google.generativeai as genai_old
                genai_old.configure(api_key=api_key)
                _gemini_client = genai_old.GenerativeModel("models/gemini-2.0-flash")
    return _gemini_client


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
    """Returns first available AI client."""
    return get_anthropic() or get_gemini() or None


async def generate_with_sonnet(system: str, user_prompt: str, max_tokens: int = 8192) -> str:
    """Call Claude Sonnet directly with system + user separation.
    Best quality for pharma translation/editing tasks."""
    client = get_anthropic()
    if not client:
        raise Exception("ANTHROPIC_API_KEY not configured")
    loop = asyncio.get_event_loop()
    msg = await loop.run_in_executor(
        None,
        lambda: client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_prompt}]
        )
    )
    return msg.content[0].text


async def generate_ai_content(prompt: str, prefer: str = "auto") -> str:
    """
    Multi-AI content generation.

    NEW provider order (Claude Sonnet first):
      0. Anthropic Claude Sonnet (PRIMARY — best quality)
      1. Mistral-7B-Instruct-Uz (if local available)
      2. Google Gemini 2.0 Flash (fallback)

    `prefer`:
      - "auto"     — Claude Sonnet first, fallback to others
      - "cloud"    — Claude Sonnet first, then Gemini
      - "mistral"  — try Mistral first, then Claude
      - "uzbek"    — same as "mistral"
      - "gemini"   — force Gemini only
    """
    # Try Mistral first only if explicitly preferred
    if prefer in ("mistral", "uzbek"):
        try:
            import mistral_engine
            if mistral_engine.is_available():
                try:
                    txt = await mistral_engine.generate_async(prompt, max_tokens=2048, temperature=0.25)
                    if txt and len(txt.strip()) > 5:
                        try:
                            mistral_engine.learn_record(prompt, txt, kind="generate")
                        except Exception:
                            pass
                        return txt
                except Exception as e:
                    logger.warning(f"[AI] Mistral failed: {e} — falling back to Claude")
        except Exception:
            pass

    # PRIMARY: Claude Sonnet
    if prefer != "gemini":
        anthropic_client = get_anthropic()
        if anthropic_client:
            try:
                loop = asyncio.get_event_loop()
                msg = await loop.run_in_executor(
                    None,
                    lambda: anthropic_client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=8192,
                        messages=[{"role": "user", "content": prompt}]
                    )
                )
                return msg.content[0].text
            except Exception as e:
                logger.warning(f"[AI] Claude Sonnet failed: {e} — falling back to Gemini")

    # FALLBACK: Gemini
    gemini = get_gemini()
    if gemini:
        try:
            if hasattr(gemini, 'models'):
                response = gemini.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                return response.text
            else:
                response = gemini.generate_content(prompt)
                return response.text
        except Exception as e:
            logger.warning(f"[AI] Gemini also failed: {e}")

    # LAST RESORT: try Mistral if not tried yet
    if prefer not in ("mistral", "uzbek"):
        try:
            import mistral_engine
            if mistral_engine.is_available():
                txt = await mistral_engine.generate_async(prompt, max_tokens=2048, temperature=0.25)
                if txt and len(txt.strip()) > 5:
                    return txt
        except Exception:
            pass

    raise Exception("No AI client configured. Set ANTHROPIC_API_KEY or GOOGLE_API_KEY.")
