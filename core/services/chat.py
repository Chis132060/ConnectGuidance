import os
import time
import json
import logging
from typing import List, Dict, Any, Tuple
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
    "schedule", "book", "therapist", "mental health"
]

# Simple in-memory rate limiting: {student_id: [(timestamp)]}
_RATE_LIMIT_STORE: Dict[int, List[float]] = {}


def check_chat_rate_limit(student_id: int) -> bool:
    """Enforce max 24 requests per 15 minutes per student."""
    max_reqs = getattr(settings, 'CHAT_RATE_LIMIT_MAX', 24)
    window_secs = 15 * 60
    now = time.time()
    timestamps = _RATE_LIMIT_STORE.get(student_id, [])
    valid_stamps = [t for t in timestamps if now - t < window_secs]
    if len(valid_stamps) >= max_reqs:
        return False
    valid_stamps.append(now)
    _RATE_LIMIT_STORE[student_id] = valid_stamps
    return True


def should_trigger_booking_cta(text: str) -> bool:
    """Check if assistant should suggest booking an appointment."""
    lower = text.lower()
    return any(k in lower for k in BOOKING_KEYWORDS) or any(k in lower for k in CRISIS_KEYWORDS)


def is_crisis_text(text: str) -> bool:
    lower = text.lower()
    return any(k in lower for k in CRISIS_KEYWORDS)


def generate_chat_response(messages: List[Dict[str, str]]) -> str:
    """
    Call Groq (or Anthropic), or provide high-quality fallback counseling guidance if no API key is provided.
    """
    groq_api_key = getattr(settings, 'GROQ_API_KEY', '') or os.getenv('GROQ_API_KEY', '')
    model = getattr(settings, 'GROQ_MODEL', 'llama3-70b-8192')

    latest_user_text = messages[-1]['content'] if messages else ""

    if is_crisis_text(latest_user_text):
        return (
            "I hear how much pain you are experiencing right now, and I want you to know you don't have to carry this alone. "
            "Please reach out for immediate human support. You can call or text the Suicide & Crisis Lifeline at 988 anytime (24/7, free and confidential), "
            "or contact the Campus Guidance Center directly. Please let a counselor or trusted person assist you today."
        )

    if groq_api_key:
        try:
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }
            formatted_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
            payload = {
                "model": model,
                "messages": formatted_messages,
                "temperature": 0.7,
                "max_tokens": 800
            }
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                return data['choices'][0]['message']['content']
            else:
                logger.error(f"Groq API error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Groq request exception: {e}")

    # Intelligent fallback when LLM API keys are not supplied in local dev
    return (
        "Thank you for sharing that with me. Academic life and personal challenges can be demanding, "
        "and taking time to reflect is a powerful first step. Remember to take steady breaths, break your tasks into "
        "manageable segments, and be kind to yourself. If you'd like deeper support tailored to your journey, "
        "I strongly recommend scheduling a one-on-one session with our university guidance counselors."
    )


def save_or_update_session(student: Profile, messages: List[Dict[str, str]]) -> ChatbotSession:
    """Save or update latest student chatbot session."""
    session, created = ChatbotSession.objects.get_or_create(
        student=student,
        defaults={'messages': messages}
    )
    if not created:
        session.messages = messages[-36:]  # enforce 36 message limit
        session.save(update_fields=['messages'])

    log_action(
        user=student,
        action="CHAT_SESSION_UPSERT",
        table_name="core_chatbot_session",
        record_id=session.id,
        metadata={"message_count": len(session.messages)}
    )

    return session
