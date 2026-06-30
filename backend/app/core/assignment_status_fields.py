"""Required assignment detail fields per execution status."""

from app.core.enums import ExecutionStatus

# Logical field name on Assignment -> user-facing label.
FIELD_LABELS: dict[str, str] = {
    "comments": "Comment",
    "jira_ticket": "Jira Details",
    "evidence_link": "PR Details",
}

STATUS_REQUIRED_FIELDS: dict[ExecutionStatus, list[str]] = {
    ExecutionStatus.NOT_STARTED: ["comments"],
    ExecutionStatus.BLOCKED: ["comments"],
    ExecutionStatus.FAILED: ["comments", "jira_ticket"],
    ExecutionStatus.NEEDS_REVIEW: ["evidence_link"],
    ExecutionStatus.TEST_AGENT_SUPPORT: ["jira_ticket"],
    ExecutionStatus.SDK_SUPPORT_MISSING: ["comments", "jira_ticket"],
    ExecutionStatus.TEST_STEPS_MISSING: ["comments", "jira_ticket"],
    ExecutionStatus.IN_PROGRESS: [],
    ExecutionStatus.PASSED: [],
}


def missing_required_fields(status: ExecutionStatus, values: dict[str, str | None]) -> list[str]:
    """Return user-facing labels for required fields that are empty."""
    missing: list[str] = []
    for field in STATUS_REQUIRED_FIELDS.get(status, []):
        if not (values.get(field) or "").strip():
            missing.append(FIELD_LABELS.get(field, field))
    return missing
