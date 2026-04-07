"""
Pharmacist Assistant — multimodal AI chat endpoint.

Features:
  - Engine selection: llama, mistral, russian, nllb, gemini, anthropic, auto
  - Tasks: chat, edit (scientific edit), translate
  - Upload: image, file (txt/pdf/docx), audio (max 50MB)
  - Language: en, ru, uz-lat, uz-cyr

Endpoints:
  POST /api/assistant/chat            — text chat with engine choice
  POST /api/assistant/edit            — scientific editing
  POST /api/assistant/translate       — multi-engine translation
  POST /api/assistant/upload          — multimodal file upload (returns extracted text + transcribe)
  GET  /api/assistant/engines         — list available engines
"""
import os
import io
import logging
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from auth import get_current_user
import db

logger = logging.getLogger("assistant_routes")
router = APIRouter(prefix="/api/assistant", tags=["assistant"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# ═══════════════════════════════════════════════════
# Pharma Expert system prompt — applied to ALL engines
# ═══════════════════════════════════════════════════
PHARMA_EXPERT_PROMPT = """Сен Pharma Expert платформасининг фармацевт асистенти, фармацевтика фанлари доктори, профессор, дори воситаларини стандартлаштириш ва сифатини назорат қилиш соҳасида халқаро тажрибага эга эксперт, фармакопейщик, фармацевтика соҳаси юқори малакали мутахассисисан.

ИХТИСОСЛИГИНГ: Норматив-ҳуқуқий ҳужжатларни (фармакопея мақолаларини) халқаро стандартлар (АҚШ фармакопеяси USP, Европа фармакопеяси Ph. Eur., Ўзбекистон Республикаси Давлат фармакопеяси) асосида экспертиза қилиш.

ТИЛЛАР: Сен билан ўзбек, рус ва инглиз тилларида мурожаат қилишади. Қайси тилда савол берилса, ўша тилда жавоб бер.

УСЛУБ: Матнни илмий таржима ва илмий таҳрир қилиш билан шуғулланасан. Матндаги хатоликларни тушунчани институтнинг аълочи талабасига тушунтиргандек, механизм ва асоси билан қадамма-қадам тушунтир. Матндаги илмий ва мантиқий хатоларни бирма-бир сана. Ҳар доим холис, илмий асосланган ва педагогик маҳорат билан жавоб бер.

ВАЗИФА (умумий): Сенга юкланган ва савол тарзида берилган мураккаб фармацевтик маълумотларни ва фармакопея мақолаларни ҳам илмий тилда мисоллар билан тушунтириш, ҳамда профессионал даражада танқидий таҳлил қилиш. Ҳар қандай материал юборилса, аввал "Вазифа учун ташаккур, бажаришга киришяпман" дегин, кейин таҳлилни бошла.

ВАЗИФА (фармакопея таҳлили): Тақдим этилган фармакопея мақоласи (норматив ҳужжат) лойиҳасини чуқур илмий, техник ва эксперт назари билан таҳлил қилиб, фармакопея талабларига номувофиқликларни, мантиқий хатоликларни ва критик номувофиқликларни аниқлаш ва сифат кўрсаткичларининг илмий асосланганлигини баҳолаш.

ТАҲЛИЛ МЕЗОНЛАРИ:
- Усуллар ва спецификацияларнинг мантиқан тўғри ишлаб чиқилганлиги
- Дори воситасини тўлиқ баҳолаш учун етарли эканлиги
- Критик бўлган чинлик, миқдорий таҳлил, аралашмалар (impurities), қолдиқ эритувчилар, микробиологик тозалик нормалари ва ҳисоблашлари тўғри келтирилганлиги
- Академик даражада ичига кириб бориш

ҚЎЛЛАНИЛАДИГАН УСУЛЛАР: Фармакопея, стандартлаштириш, техник, метрологик ва асослашнинг барча усулларини қўлла.

АНИҚЛАНГАН ХАТОЛАРНИ ҚУЙИДАГИ КАТЕГОРИЯЛАР БЎЙИЧА ЖАДВАЛ КЎРИНИШИДА ТАҚДИМ ЭТ:
| № | Категория | Хатолик тавсифи | Жойи | Тавсия (тузатиш) |
|---|-----------|-----------------|------|-----------------|

КАТЕГОРИЯЛАР:
1. Критик хатолар (Critical) — хавфсизликка бевосита таҳдид солувчи
2. Жиддий хатолар (Major) — стандартларга зид, лекин тузатиш мумкин бўлган
3. Техник камчиликлар (Minor) — расмийлаштиришдаги хатолар
(Керак бўлса ўз категорияларингни ҳам қўш)

ТАҲЛИЛ ДАВОМИДА ҚУЙИДАГИЛАРГА ЭЪТИБОР ҚАРАТ:
- Таҳлил услубларининг тўғрилиги
- Усулнинг баёни: Спецификлик, чизиқлилик, қайтарилувчанлик, аниқлик (precision) ва тўғрилик (accuracy) кўрсаткичларининг етарлилиги
- Меъёрларнинг асосланганлиги: усуллар, заррачалар ўлчами, аралашмалар миқдори (impurities), миқдорий таҳлил чегараларининг хавфсизлик талабларига мослиги
- Халқаро мувофиқлик: Етакчи халқаро фармакопеялар талаблари билан уйғунлиги (гармонизация)

ЧЕКЛОВ: Оддий фойдаланувчилар платформа хавфсизлигига оид саволлар берса (масалан "паролни қандай олиш мумкин", "админ тизимга қандай киради" ва ҳоказо), буни тақиқла ва "Бу ҳақида маълумот беришим мумкин эмас. Платформа хавфсизлиги маҳфий сақланади" деб жавоб бер."""


@router.get("/engines")
async def list_engines(current_user: Dict = Depends(get_current_user)):
    """List available AI engines for user selection."""
    engines = []

    def add(key: str, label: str, mod_name: str, languages: List[str], capabilities: List[str]):
        try:
            mod = __import__(mod_name)
            avail = mod.is_available()
            mode = mod.get_mode()
            engines.append({
                "key": key,
                "label": label,
                "available": avail,
                "mode": mode,
                "model": getattr(mod, "MODEL_ID", key),
                "languages": languages,
                "capabilities": capabilities,
            })
        except Exception as e:
            engines.append({"key": key, "label": label, "available": False, "error": str(e)[:80]})

    add("llama", "Llama 3.1 8B Uzbek", "llama_engine", ["uz", "en", "ru"], ["chat", "edit", "translate"])
    add("mistral", "Mistral 7B Uzbek", "mistral_engine", ["uz", "en"], ["chat", "edit", "translate"])
    add("russian", "Sage FRED-T5 Russian", "russian_engine", ["ru"], ["edit"])
    add("nllb", "NLLB-200 Multilingual", "translator_engine", ["en", "ru", "uz"], ["translate"])
    engines.append({"key": "auto", "label": "Авто (энг яхшиси)", "available": True, "languages": ["en", "ru", "uz"], "capabilities": ["chat", "edit", "translate"]})
    return {"engines": engines}


async def _call_engine(engine: str, prompt: str, system: Optional[str] = None, lang: str = "uz", task: str = "chat", source_lang: str = "en", target_lang: str = "uz") -> Dict[str, Any]:
    """Route through LOCAL engines only (no cloud fallback). Auto = try Llama → Mistral."""
    try:
        if engine == "llama":
            import llama_engine
            if not llama_engine.is_available():
                return {"text": "Llama engine ҳозир мавжуд эмас. Сервер моделни юкламоқда — 3-5 минут кутинг.", "engine": "llama_unavailable", "error": "not_loaded"}
            if task == "edit":
                txt = await llama_engine.improve_text(prompt, lang)
            elif task == "translate":
                txt = await llama_engine.translate(prompt, source_lang, target_lang)
            else:
                txt = await llama_engine.generate_async(prompt, system=system, max_tokens=1024)
            if txt and txt.strip():
                llama_engine.learn_record(prompt, txt, kind=f"assistant_{task}")
                return {"text": txt.strip(), "engine": "llama_" + llama_engine.get_mode()}
            return {"text": "Llama бўш жавоб қайтарди. Модель ҳали юкланмоқда (~3-5 мин). Қайта уриниб кўринг.", "engine": "llama_empty", "error": "empty_response"}

        if engine == "mistral":
            import mistral_engine
            if not mistral_engine.is_available():
                return {"text": "Mistral engine ҳозир мавжуд эмас.", "engine": "mistral_unavailable", "error": "not_loaded"}
            if task == "edit":
                txt = await mistral_engine.improve_text(prompt, lang)
            elif task == "translate":
                txt = await mistral_engine.translate(prompt, source_lang, target_lang)
            else:
                txt = await mistral_engine.generate_async(prompt, system=system, max_tokens=1024)
            if txt and txt.strip():
                return {"text": txt.strip(), "engine": "mistral_" + mistral_engine.get_mode()}
            return {"text": "Mistral бўш жавоб қайтарди.", "engine": "mistral_empty", "error": "empty_response"}

        if engine == "russian":
            import russian_engine
            if not russian_engine.is_available():
                return {"text": "Russian engine мавжуд эмас.", "engine": "russian_unavailable", "error": "not_loaded"}
            txt = await russian_engine.improve(prompt)
            if txt and txt.strip():
                return {"text": txt.strip(), "engine": "russian_" + russian_engine.get_mode()}
            return {"text": "Russian engine бўш жавоб қайтарди.", "engine": "russian_empty", "error": "empty_response"}

        if engine == "nllb":
            import translator_engine
            if not translator_engine.is_available():
                return {"text": "NLLB engine мавжуд эмас.", "engine": "nllb_unavailable", "error": "not_loaded"}
            if task != "translate":
                return {"text": "NLLB фақат таржима учун ишлатилади. Илмий таржима режимига ўтинг.", "engine": "nllb", "error": "wrong_task"}
            txt = await translator_engine.translate_async(prompt, source_lang, target_lang)
            if txt and txt.strip():
                return {"text": txt.strip(), "engine": "nllb_" + translator_engine.get_mode()}
            return {"text": "NLLB бўш жавоб қайтарди.", "engine": "nllb_empty", "error": "empty_response"}

        if engine == "auto":
            # Try Llama → Mistral → Russian (for ru) → NLLB (for translate)
            for fallback_engine in ("llama", "mistral"):
                r = await _call_engine(fallback_engine, prompt, system=system, lang=lang, task=task, source_lang=source_lang, target_lang=target_lang)
                if r.get("text") and not r.get("error"):
                    return r
            return {"text": "Барча локал engine'лар бўш жавоб қайтарди. Моделлар ҳали юкланмоқда — 3-5 минут кутинг ва қайта уриниб кўринг.", "engine": "all_empty", "error": "all_failed"}

        return {"text": f"Номаълум engine: {engine}", "engine": engine, "error": "unknown_engine"}

    except Exception as e:
        logger.warning(f"[assistant] {engine} threw: {e}")
        return {"text": f"Хато: {e}", "engine": engine, "error": str(e)}


@router.post("/chat")
async def chat(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """General-purpose chat with engine selection."""
    message = (payload.get("message") or "").strip()
    if not message:
        return {"text": ""}
    engine = payload.get("engine", "auto")
    lang = payload.get("lang", "uz")
    history = payload.get("history", [])  # [{role, content}]
    # ALWAYS use Pharma Expert prompt as the base; user can append extra instructions via `system`
    extra_system = payload.get("system", "")
    system = PHARMA_EXPERT_PROMPT + (("\n\nҚўшимча йўриқнома: " + extra_system) if extra_system else "")

    # Build context from history
    context = ""
    for h in history[-6:]:  # last 3 turns
        role = h.get("role", "user")
        content = h.get("content", "")
        context += f"{role.upper()}: {content}\n"
    full_message = (context + f"USER: {message}\nASSISTANT:") if context else message

    res = await _call_engine(engine, full_message, system=system, lang=lang, task="chat")
    return res


@router.post("/edit")
async def edit(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Scientific editing — Pharma Expert prompt applied."""
    text = (payload.get("text") or "").strip()
    engine = payload.get("engine", "auto")
    lang = payload.get("lang", "uz")
    if not text:
        return {"text": ""}
    # Wrap user text with the Pharma Expert system prompt for consistent behavior
    return await _call_engine(engine, text, system=PHARMA_EXPERT_PROMPT, lang=lang, task="edit")


@router.post("/translate")
async def translate(payload: Dict[str, Any], current_user: Dict = Depends(get_current_user)):
    """Translation — Pharma Expert prompt applied (preserves INN, ATC, doses)."""
    text = (payload.get("text") or "").strip()
    engine = payload.get("engine", "auto")
    src = payload.get("source_lang", "en")
    tgt = payload.get("target_lang", "uz")
    if not text:
        return {"text": ""}
    return await _call_engine(engine, text, system=PHARMA_EXPERT_PROMPT, source_lang=src, target_lang=tgt, task="translate")


@router.post("/upload")
async def upload(file: UploadFile = File(...), kind: str = Form("auto"), current_user: Dict = Depends(get_current_user)):
    """
    Multimodal upload (image, file, audio).
    Returns extracted text + metadata.

    Limits:
      - Max 50 MB per file
      - Allowed: txt, md, csv, pdf, docx, jpg, png, webp, gif, mp3, wav, m4a, ogg
    """
    name = (file.filename or "").lower()
    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Файл ўлчами 50 МБдан катта ({len(raw) // (1024*1024)} МБ)")
    if not raw:
        raise HTTPException(status_code=400, detail="Бўш файл")

    info = {"filename": name, "size": len(raw), "size_mb": round(len(raw) / (1024 * 1024), 2)}

    # Text files
    if name.endswith(('.txt', '.md', '.csv')):
        for enc in ('utf-8', 'utf-8-sig', 'cp1251', 'latin-1'):
            try:
                info["text"] = raw.decode(enc)
                info["kind"] = "text"
                return info
            except UnicodeDecodeError:
                continue
        info["text"] = raw.decode('utf-8', errors='ignore')
        info["kind"] = "text"
        return info

    # DOCX
    if name.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            paragraphs.append(cell.text)
            info["text"] = "\n".join(paragraphs)
            info["kind"] = "docx"
            return info
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DOCX ўқишда хато: {e}")

    # PDF
    if name.endswith('.pdf'):
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        except Exception:
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw))
                text = "\n".join((p.extract_text() or "") for p in reader.pages)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"PDF ўқишда хато: {e}")
        info["text"] = text
        info["kind"] = "pdf"
        return info

    # Image — return base64 + dimensions, can be sent to vision-capable engine
    if name.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
        import base64
        info["base64"] = base64.b64encode(raw).decode('ascii')
        info["mime"] = "image/jpeg" if name.endswith(('.jpg', '.jpeg')) else f"image/{name.rsplit('.', 1)[-1]}"
        info["kind"] = "image"
        info["text"] = f"[Image: {name}, {info['size_mb']} MB]"
        return info

    # Audio — return base64 + try transcription if Whisper available
    if name.endswith(('.mp3', '.wav', '.m4a', '.ogg', '.flac')):
        import base64
        info["base64"] = base64.b64encode(raw).decode('ascii')
        info["mime"] = f"audio/{name.rsplit('.', 1)[-1]}"
        info["kind"] = "audio"
        # Try Whisper transcription
        try:
            import whisper_engine
            if whisper_engine.is_available():
                transcript = await whisper_engine.transcribe_async(raw, name)
                info["text"] = transcript or f"[Audio: {name}]"
                info["transcribed"] = bool(transcript)
            else:
                info["text"] = f"[Audio: {name}, {info['size_mb']} MB — transcription not available]"
        except Exception:
            info["text"] = f"[Audio: {name}, {info['size_mb']} MB]"
        return info

    raise HTTPException(status_code=400, detail=f"Қўллаб-қувватланмаган формат: {name}")
