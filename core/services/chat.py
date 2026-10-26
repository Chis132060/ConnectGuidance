"""
core/services/chat.py — AI Chatbot Service for GuidanceConnect Django replica.

Handles Groq / Anthropic / Gemini LLM integrations, Server-Sent Events (SSE) streaming,
crisis escalation protocols, rate limiting (GET 60/15min, POST 24/15min),
history constraints (36 messages, 24000 characters), and session persistence.
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Generator, Optional
import requests
from django.conf import settings
from core.models import ChatbotSession, Profile
from core.services.audit import log_action
from core.services.knowledge_base import GuidanceKnowledgeBase

logger = logging.getLogger(__name__)

ANTI_HALLUCINATION_SYSTEM_PROMPT = """You are "ConnectGuidance AI", a formal, professional, and supportive guidance counselor assistant for university students.

=== CRITICAL OPERATING BOUNDARIES & ANTI-HALLUCINATION RULES ===
1. SCOPE: You assist ONLY with:
   - University guidance counseling policies, schedules, and office procedures.
   - Evidence-based stress management, exam anxiety coping, and study well-being strategies.
   - Explaining how to book, reschedule, or cancel counseling appointments in ConnectGuidance.
   - Navigating campus support services (tutoring, writing center, financial aid).

2. GROUNDING & FACTUAL INTEGRITY:
   - You MUST base all factual details (office location, room numbers, operating hours, policies, personnel) EXCLUSIVELY on the VERIFIED UNIVERSITY CONTEXT provided below.
   - If the student asks a question whose factual answer is NOT contained in the VERIFIED CONTEXT or your guidance scope, you MUST honestly and politely state:
     "I do not have verified records on that specific topic. Please visit the Guidance Office in Room 204 or consult with your designated counselor."
   - NEVER invent or speculate on phone numbers, staff names, campus rules, or academic grades.
   - NEVER provide formal medical/psychiatric diagnoses, legal advice, or write assignments/essays for students.

3. CRISIS & SAFETY PROTOCOL:
   - If the student mentions self-harm, suicide, or severe hopeless despair, immediately validate their pain with warmth, reassure them they are not alone, and urge them to call or text 988 (Suicide & Crisis Lifeline) or contact Campus Security at (555) 019-2834 immediately.

=== STRICT RESPONSE FORMAT AND STYLE GUIDELINES ===
1. FORMAL, RESPECTFUL, AND PROFESSIONAL TONE:
   - Communicate in a formal, respectful, and courteous counselor manner.
   - Do not use casual conversational slang or enthusiastic fillers (avoid phrases like "Sure thing!", "Awesome!", "Absolutely!").
   - Begin directly with a polite, professional opening statement.

2. NO MARKDOWN SYMBOLS OR ASTERISKS:
   - STRICT PROHIBITION: Do NOT use any asterisks (*) or double asterisks (**) anywhere in your response. No bold or italic markdown.
   - Do NOT use markdown heading tags (#, ##, ###).
   - Do NOT use horizontal divider lines (--- or ===).
   - Do NOT use markdown pipe table syntax (| or |---|).
   - All text must be pure, clean, readable plain text.

3. STRUCTURE AND READABILITY:
   - Use clean paragraphs separated by a blank line.
   - Number sections cleanly without markdown symbols (for example: "1. Guidance and Counseling Office:").
   - For lists, use simple numbers (1., 2., 3.) or plain hyphens (- ) without asterisks.
   - Present information in well-spaced, clean paragraphs.
   - Conclude with a formal offer of assistance (for example: "Please let me know if you require further assistance or details regarding any of these services.").

=== VERIFIED UNIVERSITY GUIDANCE CONTEXT ===
{context_block}
===========================================
"""

CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end my life", "want to die", "self harm",
    "hurting myself", "can't go on", "hopeless", "give up"
]

BOOKING_KEYWORDS = [
    "appointment", "talk to someone", "counselor", "guidance session",
    "schedule", "book", "therapist", "mental health", "stressed", "stress", "burnout"
]

# In-memory rate limiting stores: {student_id: [timestamps]}
_RATE_LIMIT_STORE_POST: Dict[int, List[float]] = {}
_RATE_LIMIT_STORE_GET: Dict[int, List[float]] = {}


def check_chat_rate_limit(student_id: int) -> bool:
    """Enforce max POST requests per 15 minutes (default 24)."""
    max_reqs = getattr(settings, 'CHAT_RATE_LIMIT_MAX', 24)
    window_ms = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_MS', 900000)
    window_secs = window_ms / 1000.0

    now = time.time()
    timestamps = _RATE_LIMIT_STORE_POST.get(student_id, [])
    valid_stamps = [t for t in timestamps if now - t < window_secs]

    if len(valid_stamps) >= max_reqs:
        return False

    valid_stamps.append(now)
    _RATE_LIMIT_STORE_POST[student_id] = valid_stamps
    return True


def check_session_get_rate_limit(student_id: int) -> bool:
    """Enforce max GET session requests per 15 minutes (default 60)."""
    max_reqs = getattr(settings, 'CHAT_SESSION_GET_MAX', 60)
    window_ms = getattr(settings, 'CHAT_SESSION_GET_WINDOW', 900000)
    window_secs = window_ms / 1000.0

    now = time.time()
    timestamps = _RATE_LIMIT_STORE_GET.get(student_id, [])
    valid_stamps = [t for t in timestamps if now - t < window_secs]

    if len(valid_stamps) >= max_reqs:
        return False

    valid_stamps.append(now)
    _RATE_LIMIT_STORE_GET[student_id] = valid_stamps
    return True


def get_chat_retry_after(student_id: int, is_post: bool = True) -> int:
    """Calculate remaining seconds before oldest timestamp expires in window."""
    store = _RATE_LIMIT_STORE_POST if is_post else _RATE_LIMIT_STORE_GET
    window_ms = getattr(settings, 'CHAT_RATE_LIMIT_WINDOW_MS', 900000) if is_post else getattr(settings, 'CHAT_SESSION_GET_WINDOW', 900000)
    window_secs = window_ms / 1000.0

    timestamps = store.get(student_id, [])
    if not timestamps:
        return 60
    now = time.time()
    oldest = min(timestamps)
    elapsed = now - oldest
    remaining = int(window_secs - elapsed)
    return max(1, remaining)


def should_trigger_booking_cta(text: str) -> bool:
    """Check if assistant should suggest booking an appointment.
    Requires at least TWO booking keyword matches, or one crisis keyword,
    to reduce false positives on generic words like 'schedule'.
    """
    lower = text.lower()
    # Crisis text always triggers CTA
    if any(k in lower for k in CRISIS_KEYWORDS):
        return True
    # Require at least 2 booking keywords to trigger CTA
    booking_matches = sum(1 for k in BOOKING_KEYWORDS if k in lower)
    return booking_matches >= 2


def is_crisis_text(text: str) -> bool:
    """Detect acute crisis or self-harm mentions."""
    lower = text.lower()
    return any(k in lower for k in CRISIS_KEYWORDS)


def has_llm_api_key() -> bool:
    """Check if at least one supported LLM API key is configured."""
    groq_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
    anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    return bool(groq_key or anthropic_key or gemini_key)


def _stream_local_fallback() -> Generator[str, None, None]:
    """Return a fast local response when an external provider is unavailable."""
    fallback_text = (
        "Thank you for sharing your thoughts with me. While navigating university coursework and personal development, "
        "it helps to break large goals into small steps. If you would like to discuss this further, "
        "our guidance counselors are always here to support you."
    )
    for word in fallback_text.split(" "):
        yield word + " "
        time.sleep(0.01)


def stream_chat_response(messages: List[Dict[str, str]]) -> Generator[str, None, None]:
    """
    Yields text delta chunks from Groq, Anthropic, or crisis protocol.
    Streams via SSE chunks.
    """
    latest_user_text = messages[-1]['content'] if messages else ""

    # Crisis protocol intervention takes precedence
    if is_crisis_text(latest_user_text):
        crisis_message = (
            "I hear how much pain you are experiencing right now, and I want you to know you don't have to carry this alone. "
            "Please reach out for immediate human support. You can call or text the Suicide & Crisis Lifeline at 988 anytime (24/7, free and confidential), "
            "or contact the Campus Guidance Center directly. Please let a counselor or trusted person assist you today."
        )
        words = crisis_message.split(" ")
        for word in words:
            yield word + " "
            time.sleep(0.02)
        return

    context_block = GuidanceKnowledgeBase.get_grounded_context_block(latest_user_text)
    grounded_system_prompt = ANTI_HALLUCINATION_SYSTEM_PROMPT.format(context_block=context_block)

    groq_api_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
    anthropic_api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
    gemini_api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
    model = getattr(settings, 'GROQ_MODEL', 'openai/gpt-oss-120b')
    provider_timeout = getattr(settings, 'CHAT_PROVIDER_TIMEOUT_SECONDS', 15)

    if groq_api_key:
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        formatted_messages = [{"role": "system", "content": grounded_system_prompt}] + messages[-36:]
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": 0.2,
            "max_tokens": 800,
            "stream": True,
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=(8, provider_timeout)
        )
        if resp.status_code != 200:
            if not (gemini_api_key or anthropic_api_key):
                raise RuntimeError(f"Groq API returned error status {resp.status_code}: {resp.text}")
            logger.warning("Groq provider failed with HTTP %s; trying the next configured provider.", resp.status_code)
        else:
            for line in resp.iter_lines(chunk_size=1):
                if not line:
                    continue
                line_str = line.decode('utf-8').strip()
                if line_str == "data: [DONE]":
                    break
                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])
                        delta = data.get('choices', [{}])[0].get('delta', {})
                        chunk = delta.get('content', '')
                        if chunk:
                            chunk = chunk.replace('*', '')
                            if chunk:
                                yield chunk
                    except json.JSONDecodeError:
                        continue
            return

    if anthropic_api_key:
        headers = {
            "x-api-key": anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "claude-3-haiku-20240307",
            "max_tokens": 800,
            "system": grounded_system_prompt,
            "messages": messages[-36:],
            "temperature": 0.2,
            "stream": True
        }
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            stream=True,
            timeout=(8, provider_timeout)
        )
        if resp.status_code != 200:
            if not gemini_api_key:
                raise RuntimeError(f"Anthropic API returned error status {resp.status_code}")
            logger.warning("Anthropic provider failed with HTTP %s; trying Gemini fallback.", resp.status_code)
        else:
            for line in resp.iter_lines(chunk_size=1):
                if not line:
                    continue
                line_str = line.decode('utf-8').strip()
                if line_str.startswith("data: "):
                    try:
                        event = json.loads(line_str[6:])
                        if event.get('type') == 'content_block_delta':
                            chunk = event.get('delta', {}).get('text', '')
                            if chunk:
                                chunk = chunk.replace('*', '')
                                if chunk:
                                    yield chunk
                    except json.JSONDecodeError:
                        continue
            return

    if gemini_api_key:
        gemini_model = getattr(settings, 'GEMINI_MODEL', 'gemini-3.8-flash')
        contents = []
        for message in messages[-36:]:
            role = 'model' if message.get('role') == 'assistant' else 'user'
            contents.append({
                'role': role,
                'parts': [{'text': str(message.get('content', ''))}],
            })

        payload = {
            'system_instruction': {
                'parts': [{'text': grounded_system_prompt}],
            },
            'contents': contents,
            'generationConfig': {
                'temperature': 0.2,
                'maxOutputTokens': 800,
            },
        }
        resp = None
        for attempt in range(3):
            try:
                resp = requests.post(
                    f'https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:streamGenerateContent?alt=sse',
                    headers={
                        'x-goog-api-key': gemini_api_key,
                        'Content-Type': 'application/json',
                    },
                    json=payload,
                    stream=True,
                    timeout=(8, provider_timeout),
                )
            except requests.exceptions.RequestException as exc:
                logger.warning("Gemini provider timed out or was unavailable: %s", exc)
                if attempt == 2:
                    yield from _stream_local_fallback()
                    return
                time.sleep(1 << attempt)
                continue

            if resp.status_code not in (429, 503) or attempt == 2:
                break

            logger.warning("Gemini provider returned HTTP %s; retrying.", resp.status_code)
            time.sleep(1 << attempt)

        if resp.status_code != 200:
            raise RuntimeError(f'Gemini API returned error status {resp.status_code}: {resp.text}')

        try:
            for line in resp.iter_lines(chunk_size=1):
                if not line:
                    continue
                line_str = line.decode('utf-8').strip()
                if line_str.startswith('data: '):
                    try:
                        data = json.loads(line_str[6:])
                        candidates = data.get('candidates', [])
                        parts = candidates[0].get('content', {}).get('parts', []) if candidates else []
                        chunk = ''.join(str(part.get('text', '')) for part in parts if part.get('text'))
                        chunk = chunk.replace('*', '')
                        if chunk:
                            yield chunk
                    except (json.JSONDecodeError, IndexError, TypeError):
                        continue
        except requests.exceptions.RequestException as exc:
            logger.warning("Gemini stream timed out or was interrupted: %s", exc)
            yield from _stream_local_fallback()
        return

    # Fallback simulation if no API keys are set (e.g. testing)
    yield from _stream_local_fallback()


def generate_chat_response(messages: List[Dict[str, str]]) -> str:
    """Non-streaming fallback method returning accumulated text string."""
    chunks = []
    for chunk in stream_chat_response(messages):
        chunks.append(chunk)
    return "".join(chunks)


def save_or_update_session(student: Profile, messages: List[Dict[str, str]]) -> ChatbotSession:
    """
    Save or update latest student chatbot session.
    Enforces maximum of 36 messages in history.
    """
    capped_messages = messages[-36:]
    session, created = ChatbotSession.objects.get_or_create(
        student=student,
        defaults={'messages': capped_messages}
    )
    if not created:
        session.messages = capped_messages
        session.save(update_fields=['messages'])

    log_action(
        user=student,
        action="CHAT_SESSION_UPSERT",
        table_name="core_chatbot_session",
        record_id=session.id,
        metadata={"message_count": len(session.messages)}
    )

    return session
