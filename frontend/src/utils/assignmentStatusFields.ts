import type { Assignment, ExecutionStatus } from "@/types";

export type AssignmentDetailField = "comments" | "jira_ticket" | "evidence_link";

export const DETAIL_FIELD_LABELS: Record<AssignmentDetailField, string> = {
  comments: "Comment",
  jira_ticket: "Jira Details",
  evidence_link: "PR Details",
};

export const DETAIL_FIELDS: AssignmentDetailField[] = ["comments", "jira_ticket", "evidence_link"];

/** Required detail fields per status (empty = none required). */
export const STATUS_REQUIRED_FIELDS: Record<ExecutionStatus, AssignmentDetailField[]> = {
  NOT_STARTED: ["comments"],
  BLOCKED: ["comments"],
  FAILED: ["comments", "jira_ticket"],
  NEEDS_REVIEW: ["evidence_link"],
  TEST_AGENT_SUPPORT: ["jira_ticket"],
  SDK_SUPPORT_MISSING: ["comments", "jira_ticket"],
  TEST_STEPS_MISSING: ["comments", "jira_ticket"],
  IN_PROGRESS: [],
  PASSED: [],
};

export function isFieldRequired(status: ExecutionStatus, field: AssignmentDetailField): boolean {
  return STATUS_REQUIRED_FIELDS[status]?.includes(field) ?? false;
}

export function missingRequiredFields(
  status: ExecutionStatus,
  assignment: Pick<Assignment, AssignmentDetailField>,
): string[] {
  return (STATUS_REQUIRED_FIELDS[status] ?? [])
    .filter((field) => !(assignment[field] ?? "").trim())
    .map((field) => DETAIL_FIELD_LABELS[field]);
}
