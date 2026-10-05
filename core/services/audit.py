import logging
import uuid
from typing import Optional, Any, Dict
from django.utils import timezone
from core.models import AuditLog, Profile

logger = logging.getLogger(__name__)


def log_action(
    user: Optional[Profile],
    action: str,
    table_name: str = "application",
    record_id: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[AuditLog]:
    """
    Safely append an entry to the AuditLog table.
    Guaranteed to never raise an exception, preserving transaction flow.
    """
    try:
        rec_uuid = None
        if record_id:
            if isinstance(record_id, uuid.UUID):
                rec_uuid = record_id
            else:
                try:
                    rec_uuid = uuid.UUID(str(record_id))
                except (ValueError, AttributeError):
                    rec_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"{table_name}-{record_id}")

        return AuditLog.objects.create(
            user=user,
            action=action,
            table_name=table_name,
            record_id=rec_uuid,
            metadata=metadata or {}
        )
    except Exception as e:
        logger.warning(f"Audit log failed for action={action}, table={table_name}: {e}")
        return None
