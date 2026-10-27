-- ConnectGuidance: Important System Architecture Queries
-- PostgreSQL 17 / psql compatible
-- Read-only queries for System Architecture presentation.
-- Do not select passwords, encryption keys, encrypted note content, or chat data.
-- Connect with: psql -U postgres -d connectguidance

\pset null '[NULL]'
\x auto

-- ============================================================================
-- 1. ARCHITECTURE OVERVIEW
-- ============================================================================

-- Main application tables.
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- Database relationships for an ERD or system architecture diagram.
SELECT
    tc.table_name AS child_table,
    kcu.column_name AS child_column,
    ccu.table_name AS parent_table,
    ccu.column_name AS parent_column,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
  ON rc.constraint_name = tc.constraint_name
 AND rc.constraint_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY child_table, child_column;

-- Important columns and data types.
SELECT table_name, ordinal_position, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN (
      'core_profile', 'auth_user', 'core_appointment', 'core_casenote',
      'core_studentmoodalert', 'core_auditlog'
  )
ORDER BY table_name, ordinal_position;

-- ============================================================================
-- 2. USERS AND ROLE-BASED ACCESS
-- ============================================================================

-- Users with their application role. Password hashes are intentionally omitted.
SELECT
    p.id AS profile_id,
    u.id AS user_id,
    u.username,
    u.email,
    p.full_name,
    p.student_id,
    p.department,
    p.role,
    u.is_active AS login_active,
    p.is_active AS profile_active,
    u.is_staff,
    u.is_superuser
FROM core_profile AS p
JOIN auth_user AS u ON u.id = p.user_id
ORDER BY p.role, p.full_name;

-- Role distribution: demonstrates the RBAC population.
SELECT role, is_active, COUNT(*) AS user_count
FROM core_profile
GROUP BY role, is_active
ORDER BY role, is_active DESC;

-- Accounts that cannot properly access the application.
SELECT
    u.username,
    u.email,
    p.full_name,
    p.role,
    u.is_active AS login_active,
    p.is_active AS profile_active
FROM auth_user AS u
LEFT JOIN core_profile AS p ON p.user_id = u.id
WHERE p.id IS NULL
   OR u.is_active = FALSE
   OR p.is_active = FALSE
ORDER BY p.role, p.full_name;

-- ============================================================================
-- 3. CORE STUDENT–COUNSELOR WORKFLOW
-- ============================================================================

-- Appointment relationship: one student is assigned to one counselor.
SELECT
    a.id AS appointment_id,
    a.scheduled_at,
    a.status,
    a.concern_type,
    s.full_name AS student_name,
    s.student_id,
    c.full_name AS counselor_name,
    a.created_at
FROM core_appointment AS a
JOIN core_profile AS s ON s.id = a.student_id
JOIN core_profile AS c ON c.id = a.counselor_id
ORDER BY a.scheduled_at DESC;

-- Appointment lifecycle summary.
SELECT
    status,
    COUNT(*) AS total_appointments
FROM core_appointment
GROUP BY status
ORDER BY status;

-- Counselor workload and completion rate.
SELECT
    c.full_name AS counselor_name,
    COUNT(a.id) AS total_appointments,
    COUNT(a.id) FILTER (WHERE a.status = 'pending') AS pending,
    COUNT(a.id) FILTER (WHERE a.status = 'confirmed') AS confirmed,
    COUNT(a.id) FILTER (WHERE a.status = 'completed') AS completed,
    COUNT(a.id) FILTER (WHERE a.status = 'cancelled') AS cancelled,
    ROUND(
        100.0 * COUNT(a.id) FILTER (WHERE a.status = 'completed')
        / NULLIF(COUNT(a.id), 0), 2
    ) AS completion_rate_percent
FROM core_profile AS c
LEFT JOIN core_appointment AS a ON a.counselor_id = c.id
WHERE c.role = 'counselor'
GROUP BY c.id, c.full_name
ORDER BY total_appointments DESC;

-- ============================================================================
-- 4. CASE NOTES AND CONFIDENTIALITY
-- ============================================================================

-- Case-note metadata and visibility status. Content remains encrypted.
SELECT
    cn.id AS case_note_id,
    a.id AS appointment_id,
    a.status AS appointment_status,
    a.scheduled_at,
    s.full_name AS student_name,
    c.full_name AS counselor_name,
    cn.is_confidential,
    CASE
        WHEN cn.is_confidential THEN 'Counselor only'
        WHEN a.status = 'completed' THEN 'Visible to student'
        ELSE 'Not yet visible to student'
    END AS visibility_rule,
    cn.created_at,
    cn.updated_at
FROM core_casenote AS cn
JOIN core_appointment AS a ON a.id = cn.appointment_id
JOIN core_profile AS s ON s.id = a.student_id
JOIN core_profile AS c ON c.id = cn.counselor_id
ORDER BY cn.updated_at DESC;

-- Notes currently eligible for the student dashboard.
SELECT
    cn.id AS case_note_id,
    a.id AS appointment_id,
    s.full_name AS student_name,
    c.full_name AS counselor_name,
    a.scheduled_at,
    a.concern_type,
    cn.updated_at
FROM core_casenote AS cn
JOIN core_appointment AS a ON a.id = cn.appointment_id
JOIN core_profile AS s ON s.id = a.student_id
JOIN core_profile AS c ON c.id = cn.counselor_id
WHERE a.status = 'completed'
  AND cn.is_confidential = FALSE
ORDER BY cn.updated_at DESC;

-- Completed appointments with no student-visible note.
SELECT
    a.id AS appointment_id,
    a.scheduled_at,
    s.full_name AS student_name,
    c.full_name AS counselor_name,
    CASE
        WHEN cn.id IS NULL THEN 'No case note created'
        WHEN cn.is_confidential THEN 'Case note is confidential'
        ELSE 'Shared note available'
    END AS note_status
FROM core_appointment AS a
JOIN core_profile AS s ON s.id = a.student_id
JOIN core_profile AS c ON c.id = a.counselor_id
LEFT JOIN core_casenote AS cn ON cn.appointment_id = a.id
WHERE a.status = 'completed'
ORDER BY a.scheduled_at DESC;

-- ============================================================================
-- 5. WELLNESS AND SUPPORT SERVICES
-- ============================================================================

-- Student wellness alerts routed to counselors.
SELECT
    ma.id AS alert_id,
    ma.created_at,
    s.full_name AS student_name,
    s.student_id,
    c.full_name AS counselor_name,
    CASE WHEN ma.note IS NULL THEN FALSE ELSE TRUE END AS has_reflection_note
FROM core_studentmoodalert AS ma
JOIN core_profile AS s ON s.id = ma.student_id
JOIN core_profile AS c ON c.id = ma.counselor_id
ORDER BY ma.created_at DESC;

-- Alert workload by counselor.
SELECT
    c.full_name AS counselor_name,
    COUNT(ma.id) AS total_alerts,
    MAX(ma.created_at) AS latest_alert
FROM core_profile AS c
LEFT JOIN core_studentmoodalert AS ma ON ma.counselor_id = c.id
WHERE c.role = 'counselor'
GROUP BY c.id, c.full_name
ORDER BY total_alerts DESC;

-- ============================================================================
-- 6. AUDITABILITY AND SECURITY
-- ============================================================================

-- Recent activity for demonstrating the audit-trail architecture.
SELECT
    al.id AS audit_id,
    al.created_at,
    al.action,
    al.table_name,
    p.full_name AS performed_by,
    p.role,
    al.record_id,
    al.metadata
FROM core_auditlog AS al
LEFT JOIN core_profile AS p ON p.id = al.user_id
ORDER BY al.created_at DESC
LIMIT 50;

-- Audit event totals.
SELECT
    action,
    table_name,
    COUNT(*) AS event_count,
    MAX(created_at) AS latest_event
FROM core_auditlog
GROUP BY action, table_name
ORDER BY event_count DESC;

-- Case-note access and modification history.
SELECT
    al.created_at,
    al.action,
    p.full_name AS performed_by,
    p.role,
    al.record_id,
    al.metadata
FROM core_auditlog AS al
LEFT JOIN core_profile AS p ON p.id = al.user_id
WHERE al.table_name = 'core_case_note'
   OR al.action LIKE 'CASE_NOTE%'
ORDER BY al.created_at DESC;

-- ============================================================================
-- 7. SYSTEM INTEGRITY CHECKS
-- ============================================================================

-- Appointments with invalid student/counselor role assignments.
SELECT
    a.id AS appointment_id,
    s.full_name AS student_name,
    s.role AS student_role,
    c.full_name AS counselor_name,
    c.role AS counselor_role
FROM core_appointment AS a
JOIN core_profile AS s ON s.id = a.student_id
JOIN core_profile AS c ON c.id = a.counselor_id
WHERE s.role <> 'student'
   OR c.role <> 'counselor';

-- Case notes whose author is not the assigned counselor.
SELECT
    cn.id AS case_note_id,
    cn.appointment_id,
    cn.counselor_id AS note_author_id,
    a.counselor_id AS assigned_counselor_id
FROM core_casenote AS cn
JOIN core_appointment AS a ON a.id = cn.appointment_id
WHERE cn.counselor_id <> a.counselor_id;

-- Completed sessions without a case note.
SELECT
    a.id AS appointment_id,
    s.full_name AS student_name,
    c.full_name AS counselor_name,
    a.scheduled_at
FROM core_appointment AS a
JOIN core_profile AS s ON s.id = a.student_id
JOIN core_profile AS c ON c.id = a.counselor_id
LEFT JOIN core_casenote AS cn ON cn.appointment_id = a.id
WHERE a.status = 'completed'
  AND cn.id IS NULL
ORDER BY a.scheduled_at DESC;

-- ============================================================================
-- 8. PRESENTATION KPI QUERY
-- ============================================================================

WITH appointment_metrics AS (
    SELECT
        COUNT(*) AS total_appointments,
        COUNT(*) FILTER (WHERE status = 'completed') AS completed_appointments,
        COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_appointments,
        COUNT(DISTINCT student_id) AS students_served,
        COUNT(DISTINCT counselor_id) AS counselors
    FROM core_appointment
), note_metrics AS (
    SELECT
        COUNT(*) AS total_notes,
        COUNT(*) FILTER (WHERE is_confidential = FALSE) AS shared_notes,
        COUNT(*) FILTER (WHERE is_confidential = TRUE) AS confidential_notes
    FROM core_casenote
)
SELECT
    a.total_appointments,
    a.completed_appointments,
    a.cancelled_appointments,
    a.students_served,
    a.counselors,
    n.total_notes,
    n.shared_notes,
    n.confidential_notes,
    ROUND(
        100.0 * a.completed_appointments
        / NULLIF(a.total_appointments, 0), 2
    ) AS completion_rate_percent
FROM appointment_metrics AS a
CROSS JOIN note_metrics AS n;

-- Monthly trend for a presentation chart.
SELECT
    DATE_TRUNC('month', scheduled_at)::date AS month,
    COUNT(*) AS total_appointments,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
    COUNT(DISTINCT student_id) AS students_served
FROM core_appointment
GROUP BY DATE_TRUNC('month', scheduled_at)
ORDER BY month;
