import os
import logging

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
    """Returns Gemini model (primary). Use generate_ai_content() for dual-AI calls."""
    return get_gemini() or (True if get_anthropic() else None)


async def generate_ai_content(prompt: str, prefer: str = "auto") -> str:
    """
    Multi-AI content generation. Provider order:
      0. Mistral-7B-Instruct-Uz (if MISTRAL available — best Uzbek)
      1. Google Gemini 2.0 Flash
      2. Anthropic Claude (fallback)

    `prefer`:
      - "auto"     — try Mistral first if available, else cloud
      - "mistral"  — force Mistral, fallback to cloud
      - "cloud"    — skip Mistral, use Gemini/Claude only
      - "uzbek"    — same as "mistral" (best Uzbek-aware)
    """
    # Try Mistral (Uzbek-optimized) first when available and preferred
    try:
        import mistral_engine
        if mistral_engine.is_available() and prefer in ("auto", "mistral", "uzbek"):
            try:
                txt = await mistral_engine.generate_async(prompt, max_tokens=2048, temperature=0.25)
                if txt and len(txt.strip()) > 5:
                    try:
                        mistral_engine.learn_record(prompt, txt, kind="generate")
                    except Exception:
                        pass
                    return txt
            except Exception as e:
                logger.warning(f"[AI] Mistral failed: {e} — falling back to cloud")
    except Exception:
        pass

    gemini = get_gemini()
    if gemini:
        try:
            # New google-genai API
            if hasattr(gemini, 'models'):
                response = gemini.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                return response.text
            else:
                # Old google-generativeai API
                response = gemini.generate_content(prompt)
                return response.text
        except Exception as e:
            logger.warning(f"[AI] Gemini failed: {e} — switching to Anthropic...")

    anthropic_client = get_anthropic()
    if anthropic_client:
        try:
            msg = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return msg.content[0].text
        except Exception as e:
            logger.error(f"[AI] Anthropic also failed: {e}")
            raise

    raise Exception("No AI client configured. Set GOOGLE_API_KEY or ANTHROPIC_API_KEY.")
