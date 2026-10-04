"""
Chat views — AI wellness assistant conversation and streaming endpoints.
Handles chat session retrieval and response streaming for the student wellness bot.
"""
import os
import json
from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.guards import role_required
from core.models import ChatbotSession
from core.services.chat import (
    check_chat_rate_limit,
    check_session_get_rate_limit,
    get_session,
    stream_chat,
)


def has_llm_api_key():
    """Return True if an AI LLM provider key is available in settings or environment."""
    groq = getattr(settings, "GROQ_API_KEY", "") or os.environ.get("GROQ_API_KEY", "")
    anthropic = getattr(settings, "ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    return bool(groq or anthropic)


@role_required("student")
def chat_session_view(request):
    """GET: return latest chat session for the student."""
    if not check_session_get_rate_limit(request.profile.id):
        resp = JsonResponse({"error": "Too many requests", "retryAfter": 900}, status=429)
        resp["Retry-After"] = "900"
        return resp

    session = get_session(request.profile)
    if session:
        return JsonResponse({
            "sessionId": session.pk,
            "messages": session.messages,
        })
    return JsonResponse({"sessionId": None, "messages": []})


@csrf_exempt
@role_required("student")
def chat_stream_view(request):
    """POST: stream AI response via SSE."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # 1. Rate limit
    if not check_chat_rate_limit(request.profile.id):
        resp = JsonResponse({"error": "Too many requests", "retryAfter": 900}, status=429)
        resp["Retry-After"] = "900"
        return resp

    # 2. Check service availability
    if not has_llm_api_key():
        return JsonResponse({"error": "AI service unavailable"}, status=503)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_messages = body.get("messages", [])
    session_id = body.get("sessionId")

    # 3. Message validation
    if not user_messages or not isinstance(user_messages, list):
        return JsonResponse({"error": "Messages must be a non-empty list"}, status=400)

    if user_messages[-1].get("role") != "user":
        return JsonResponse({"error": "Last message must be from user"}, status=400)

    total_content = sum(len(m.get("content", "")) for m in user_messages)
    if total_content > 24000:
        return JsonResponse({"error": "Content exceeds maximum length of 24,000 characters"}, status=400)

    # 4. Session ownership verification
    if session_id:
        if not ChatbotSession.objects.filter(pk=session_id, student=request.profile).exists():
            return JsonResponse({"error": "Unauthorized session access"}, status=403)

    response = StreamingHttpResponse(
        stream_chat(request.profile, user_messages, session_id),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
