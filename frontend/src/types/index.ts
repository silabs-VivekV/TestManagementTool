export type UserRole = "ADMIN" | "TEAM_LEAD" | "TEAM_MEMBER";

export type ExecutionStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "BLOCKED"
  | "PASSED"
  | "FAILED"
  | "NEEDS_REVIEW"
  | "TEST_AGENT_SUPPORT"
  | "SDK_SUPPORT_MISSING"
  | "TEST_STEPS_MISSING";

export type AutoAssignStrategy =
  | "ROUND_ROBIN"
  | "EQUAL_DISTRIBUTION"
  | "TECHNOLOGY_BASED"
  | "PRIORITY_BASED";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface TestCase {
  id: number;
  case_id: string;
  title: string;
  priority?: string | null;
  technology?: string | null;
  release_version?: string | null;
  execution_type?: string | null;
  deployment_status?: string | null;
  product_line?: string | null;
  suite_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Assignment {
  id: number;
  test_case_id: number;
  assigned_to: number;
  assigned_by: number;
  assigned_date: string;
  status: ExecutionStatus;
  remarks?: string | null;
  comments?: string | null;
  evidence_link?: string | null;
  defect_info?: string | null;
  jira_ticket?: string | null;
  eta?: string | null;
  execution_date?: string | null;
  completed_date?: string | null;
  updated_at: string;
  test_case?: TestCase | null;
  assignee_name?: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ExecutiveDashboard {
  total_test_cases: number;
  assigned: number;
  completed: number;
  pending: number;
  blocked: number;
  failed: number;
  passed: number;
  pass_rate: number;
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface TestCaseFacets {
  technology: string[];
  priority: string[];
  release_version: string[];
  execution_type: string[];
  product_line: string[];
  section_id: string[];
  sdk_type: string[];
  product_type: string[];
  deployment_status: string[];
  test_case_status: string[];
  suite_id: string[];
}

export interface DashboardSummary {
  filters_applied: Record<string, string>;
  total_test_cases: number;
  assigned: number;
  unassigned: number;
  not_started: number;
  in_progress: number;
  blocked: number;
  passed: number;
  failed: number;
  needs_review: number;
  completed: number;
  pending: number;
  remaining: number;
  pass_rate: number;
}

export interface SummaryFilters {
  technology?: string[];
  priority?: string[];
  release_version?: string[];
  execution_type?: string[];
  product_line?: string[];
  section_id?: string[];
  sdk_type?: string[];
  product_type?: string[];
  deployment_status?: string[];
  test_case_status?: string[];
  suite_id?: string[];
  assignee?: number;
}

export interface ReleaseProgressItem {
  release_version: string;
  total: number;
  completed: number;
  completion_pct: number;
}

export interface WorkloadItem {
  assignee_id: number;
  assignee_name: string;
  total: number;
  completed: number;
  pending: number;
}

export interface TeamLeadDashboard {
  team_workload: WorkloadItem[];
  assignment_distribution: StatusCount[];
  execution_progress: StatusCount[];
  release_progress: ReleaseProgressItem[];
}

export interface TeamMemberDashboard {
  my_assignments: number;
  my_completed: number;
  my_in_progress: number;
  my_open_defects: number;
  my_blocked: number;
  status_breakdown: StatusCount[];
}

export interface ImportResultError {
  row: number;
  case_id?: string | null;
  reason: string;
}

export interface ImportResult {
  total_rows: number;
  imported: number;
  skipped_duplicates: number;
  failed: number;
  errors: ImportResultError[];
}

export interface AssignByFilterRequest {
  assigned_to?: number;
  status?: ExecutionStatus;
  eta?: string | null;
  dry_run?: boolean;
  case_ids?: string[];
  search?: string;
  technology?: string[];
  priority?: string[];
  release_version?: string[];
  execution_type?: string[];
  product_line?: string[];
  section_id?: string[];
  sdk_type?: string[];
  product_type?: string[];
  deployment_status?: string[];
  test_case_status?: string[];
  suite_id?: string[];
}

export interface AssignByFilterResult {
  matched: number;
  assigned: number;
  reassigned: number;
  dry_run: boolean;
  truncated: boolean;
  items: {
    case_id: string;
    title: string;
    section_id?: string | null;
    current_assignee?: string | null;
  }[];
}

export interface AssignmentImportResult {
  total_rows: number;
  assigned: number;
  reassigned: number;
  updated: number;
  users_created: number;
  failed: number;
  created_users: string[];
  errors: { row: number; case_id?: string | null; reason: string }[];
}

export interface TestRailProject {
  id: number;
  name: string;
}

export interface TestRailSyncResult {
  project_id: number;
  suite_id: number;
  fetched: number;
  output_file: string;
  import_result: ImportResult;
}

export interface TechnologyPivotRow {
  technology: string;
  total: number;
  passed: number;
  failed: number;
  blocked: number;
}

export interface ReleasePivotRow {
  release_version: string;
  total: number;
  completed: number;
  completion_pct: number;
  pass_rate: number;
  fail_rate: number;
}

export interface AssigneePivotRow {
  assignee_id: number;
  assignee_name: string;
  assigned: number;
  completed: number;
  pending: number;
}

export interface AssignmentMatrixSection {
  section_id: string;
  total: number;
  by_release: Record<string, number>;
  by_status: Record<string, number>;
  status_summary: string;
  by_deadline: Record<string, number>;
  deadline_summary: string;
}

export interface AssignmentMatrixRow {
  assignee_id: number;
  assignee_name: string;
  total: number;
  by_release: Record<string, number>;
  by_status: Record<string, number>;
  status_summary: string;
  by_deadline: Record<string, number>;
  deadline_summary: string;
  sections: AssignmentMatrixSection[];
}

export interface AssignmentMatrix {
  columns: string[];
  rows: AssignmentMatrixRow[];
  column_totals: Record<string, number>;
  grand_total: number;
}

export interface WeeklyBucket {
  key: string;
  label: string;
}

export interface WeeklyProgressRow {
  assignee_id: number;
  assignee_name: string;
  by_week: Record<string, number>;
  total: number;
  on_time: number;
  late: number;
  overdue: number;
}

export interface WeeklyProgress {
  weeks: WeeklyBucket[];
  rows: WeeklyProgressRow[];
  week_totals: Record<string, number>;
  grand_total: number;
  total_on_time: number;
  total_late: number;
  total_overdue: number;
}
