"""
Audit Service — Resilient append-only activity logger.
Safely captures user events, transactions, and security actions without breaking primary operations.
"""
import logging

logger = logging.getLogger(__name__)


def log_action(user=None, action="", table_name="application", record_id=None, metadata=None):
    """
    Append an AuditLog row. Returns created AuditLog instance or None if an error occurred.
    user: Profile instance or None
    record_id: UUID, string, int, or None
    """
    try:
        from core.models import AuditLog
        import uuid as _uuid

        # Sanitize record_id to UUID if possible
        rid = None
        if record_id is not None:
            try:
                rid = _uuid.UUID(str(record_id))
            except (ValueError, AttributeError):
                rid = None

        log_obj = AuditLog.objects.create(
            user=user,
            action=action,
            table_name=table_name,
            record_id=rid,
            metadata=metadata or {},
        )
        return log_obj
    except Exception as exc:
        logger.warning("AuditLog write failed (swallowed): %s", exc)
        return None
