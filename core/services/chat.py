"""
core/services/chat.py — AI Chatbot Service for GuidanceConnect Django replica.

Handles Groq / Anthropic LLM integrations, Server-Sent Events (SSE) streaming,
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
from .audit import log_action

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are GuidanceConnect's supportive, empathetic AI Assistant for university students.
Your mission is to provide warm, non-judgmental guidance, academic planning tips, stress management strategies, and campus resource navigation.

CRITICAL SAFETY PROTOCOL:
You are NOT a substitute for professional mental health therapy or crisis intervention.
If the student expresses acute crisis, self-harm, suicidal ideation, or severe distress:
1. Immediately acknowledge their feelings with compassion.
2. Emphasize that they are not alone and that immediate human help is available.
3. Explicitly urge them to contact crisis hotlines (e.g., 988 Suicide & Crisis Lifeline) or visit the Campus Guidance Center immediately.
4. Recommend scheduling an in-person session with a university counselor.
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
    """Check if Groq or Anthropic API key is configured."""
    groq_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
    anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
    return bool(groq_key or anthropic_key)


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

    groq_api_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
    anthropic_api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
    model = getattr(settings, 'GROQ_MODEL', 'llama3-70b-8192')

    if groq_api_key:
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages[-36:]
        payload = {
            "model": model,
            "messages": formatted_messages,
            "temperature": 0.7,
            "max_tokens": 800,
            "stream": True,
        }
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=25
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Groq API returned error status {resp.status_code}: {resp.text}")

        for line in resp.iter_lines():
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
            "system": SYSTEM_PROMPT,
            "messages": messages[-36:],
            "stream": True
        }
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            stream=True,
            timeout=25
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Anthropic API returned error status {resp.status_code}")

        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode('utf-8').strip()
            if line_str.startswith("data: "):
                try:
                    event = json.loads(line_str[6:])
                    if event.get('type') == 'content_block_delta':
                        chunk = event.get('delta', {}).get('text', '')
                        if chunk:
                            yield chunk
                except json.JSONDecodeError:
                    continue
        return

    # Fallback simulation if no API keys are set (e.g. testing)
    fallback_text = (
        "Thank you for sharing your thoughts with me. While navigating university coursework and personal development, "
        "it helps to break large goals into small steps. If you would like to discuss this further, "
        "our guidance counselors are always here to support you."
    )
    for word in fallback_text.split(" "):
        yield word + " "
        time.sleep(0.01)


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
