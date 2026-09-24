"""
core/views/chat.py — AI Chatbot views for GuidanceConnect Django replica.

Implements FLOWS §14-15:
- GET /chat/session/ — Hydrate student session with 60/15min rate limit
- POST /chat/ — SSE streaming endpoint with 24/15min rate limit, 36-msg cap, and booking CTA
- GET /chatbot/ — Student interactive chatbot page
"""

import json
from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from core.guards import require_student
from core.models import ChatbotSession
from core.services.chat import (
    check_chat_rate_limit,
    check_session_get_rate_limit,
    get_chat_retry_after,
    has_llm_api_key,
    stream_chat_response,
    save_or_update_session,
    should_trigger_booking_cta,
    is_crisis_text,
)


@require_student
def student_chatbot_page_view(request):
    """Render full student chatbot interaction screen."""
    return render(request, 'student/chatbot.html', {
        'profile': request.user.profile
    })


@require_student
@require_http_methods(["GET"])
def chat_session_get_view(request):
    """
    FLOWS §14: Restore or hydrate latest chatbot session.
    - Rate limit: 60 GET requests per 15 minutes per student.
    - Returns latest ChatbotSession messages or empty array.
    """
    student = request.user.profile

    if not check_session_get_rate_limit(student.id):
        resp = JsonResponse({'error': 'Rate limit exceeded.'}, status=429)
        resp['Retry-After'] = str(get_chat_retry_after(student.id, is_post=False))
        return resp

    session = ChatbotSession.objects.filter(student=student).first()

    if session:
        return JsonResponse({
            'sessionId': session.id,
            'messages': session.messages
        })

    return JsonResponse({
        'sessionId': None,
        'messages': []
    })


@require_student
@require_http_methods(["POST"])
def chat_stream_post_view(request):
    """
    FLOWS §15: Streaming chat endpoint via Server-Sent Events (SSE).
    - Checks LLM API key configuration (503 if not set).
    - Rate limit: 24 requests per 15 minutes per student (429 Retry-After).
    - Validates JSON body, last role == 'user', total content <= 24,000 chars, history cap 36.
    - Verifies session ownership if sessionId is passed.
    - Streams delta chunks, persists session, and provides should_suggest booking CTA flag.
    """
    student = request.user.profile

    # 1. 503 if no API key is available
    if not has_llm_api_key():
        return JsonResponse({'error': 'AI Chat service is not configured.'}, status=503)

    # 2. 429 Rate limit check
    if not check_chat_rate_limit(student.id):
        resp = JsonResponse({'error': 'Rate limit exceeded. Please wait before sending more messages.'}, status=429)
        resp['Retry-After'] = str(get_chat_retry_after(student.id, is_post=True))
        return resp

    # 3. Parse JSON request body
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Malformed JSON body.'}, status=400)

    messages = body.get('messages', [])
    if not isinstance(messages, list) or not messages:
        return JsonResponse({'error': 'Messages list is required and cannot be empty.'}, status=400)

    # Validate last message is from user
    last_msg = messages[-1]
    if not isinstance(last_msg, dict) or last_msg.get('role') != 'user' or not last_msg.get('content', '').strip():
        return JsonResponse({'error': 'Last message must have role "user" and non-empty content.'}, status=400)

    # Total content length constraint: max 24,000 characters
    total_chars = sum(len(str(m.get('content', ''))) for m in messages)
    if total_chars > 24000:
        return JsonResponse({'error': 'Total message content exceeds the 24,000 character limit.'}, status=400)

    # History cap: maximum 36 messages
    if len(messages) > 36:
        messages = messages[-36:]

    # Session ownership check if sessionId provided
    session_id = body.get('sessionId')
    if session_id:
        existing_session = ChatbotSession.objects.filter(id=session_id).first()
        if existing_session and existing_session.student_id != student.id:
            return HttpResponseForbidden("You do not own this chat session.")

    # 4. SSE Streaming response generator
    def event_stream():
        accumulated_chunks = []
        try:
            for delta in stream_chat_response(messages):
                accumulated_chunks.append(delta)
                event_data = json.dumps({'type': 'delta', 'chunk': delta})
                yield f"data: {event_data}\n\n"

            full_assistant_reply = "".join(accumulated_chunks)
            persisted_messages = messages + [{'role': 'assistant', 'content': full_assistant_reply}]
            saved_session = save_or_update_session(student, persisted_messages)

            should_suggest = (
                should_trigger_booking_cta(full_assistant_reply) or
                is_crisis_text(last_msg.get('content', ''))
            )

            done_event = json.dumps({
                'type': 'done',
                'sessionId': saved_session.id,
                'should_suggest': should_suggest,
                'is_crisis': is_crisis_text(last_msg.get('content', ''))
            })
            yield f"data: {done_event}\n\n"

        except Exception as e:
            err_event = json.dumps({'type': 'error', 'error': str(e)})
            yield f"data: {err_event}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
