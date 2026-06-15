import { api, getToken } from "./api";
import type {
  AssignByFilterRequest,
  AssignByFilterResult,
  AssigneePivotRow,
  Assignment,
  AssignmentImportResult,
  AssignmentMatrix,
  WeeklyProgress,
  AuthResponse,
  AutoAssignStrategy,
  DashboardSummary,
  ExecutiveDashboard,
  ImportResult,
  Page,
  ReleasePivotRow,
  SummaryFilters,
  TeamLeadDashboard,
  TeamMemberDashboard,
  TechnologyPivotRow,
  TestCase,
  TestCaseFacets,
  TestRailProject,
  TestRailSyncResult,
  User,
  UserRole,
} from "@/types";

export const authApi = {
  login: (email: string, password: string) =>
    api.post<AuthResponse>("/auth/login", { email, password }).then((r) => r.data),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
};

export interface TestCaseFilters {
  page?: number;
  page_size?: number;
  search?: string;
  technology?: string;
  priority?: string;
  release_version?: string;
  execution_type?: string;
  product_line?: string;
}

export const testCaseApi = {
  list: (params: TestCaseFilters) =>
    api.get<Page<TestCase>>("/test-cases", { params }).then((r) => r.data),
  facets: () => api.get<TestCaseFacets>("/test-cases/facets").then((r) => r.data),
};

export const userApi = {
  list: () => api.get<User[]>("/users").then((r) => r.data),
  quickCreate: (name: string, role: UserRole = "TEAM_MEMBER") =>
    api.post<User>("/users/quick", { name, role }).then((r) => r.data),
};

export const assignmentApi = {
  list: (params: { page?: number; page_size?: number; status?: string; assigned_to?: number }) =>
    api.get<Page<Assignment>>("/assignments", { params }).then((r) => r.data),
  createSingle: (test_case_id: number, assigned_to: number, remarks?: string) =>
    api.post<Assignment>("/assignments", { test_case_id, assigned_to, remarks }).then((r) => r.data),
  bulk: (test_case_ids: number[], assigned_to: number, remarks?: string) =>
    api.post("/assignments/bulk", { test_case_ids, assigned_to, remarks }).then((r) => r.data),
  auto: (test_case_ids: number[], assignee_ids: number[], strategy: AutoAssignStrategy) =>
    api.post("/assignments/auto", { test_case_ids, assignee_ids, strategy }).then((r) => r.data),
  updateStatus: (id: number, payload: Partial<Assignment>) =>
    api.patch<Assignment>(`/assignments/${id}/status`, payload).then((r) => r.data),
  reassign: (id: number, assigned_to: number) =>
    api.patch<Assignment>(`/assignments/${id}/reassign`, { assigned_to }).then((r) => r.data),
  remove: (id: number) => api.delete<void>(`/assignments/${id}`).then((r) => r.data),
  importSheet: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post<AssignmentImportResult>("/assignments/import", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  byFilter: (payload: AssignByFilterRequest) =>
    api.post<AssignByFilterResult>("/assignments/by-filter", payload).then((r) => r.data),
  exportSheet: () =>
    api.get("/assignments/export", { responseType: "blob" }).then((r) => r.data as Blob),
};

export const dashboardApi = {
  executive: () => api.get<ExecutiveDashboard>("/dashboards/executive").then((r) => r.data),
  teamLead: () => api.get<TeamLeadDashboard>("/dashboards/team-lead").then((r) => r.data),
  teamMember: () => api.get<TeamMemberDashboard>("/dashboards/team-member").then((r) => r.data),
  summary: (filters: SummaryFilters) => {
    const search = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (Array.isArray(value)) {
        value.forEach((v) => {
          if (v !== undefined && v !== null && v !== "") search.append(key, String(v));
        });
      } else if (value !== undefined && value !== null && (value as unknown) !== "") {
        search.append(key, String(value));
      }
    });
    const qs = search.toString();
    return api
      .get<DashboardSummary>(`/dashboards/summary${qs ? `?${qs}` : ""}`)
      .then((r) => r.data);
  },
};

export const analyticsApi = {
  byTechnology: (params: Record<string, string | number | undefined>) =>
    api.get<TechnologyPivotRow[]>("/analytics/pivot/technology", { params }).then((r) => r.data),
  byRelease: (params: Record<string, string | number | undefined>) =>
    api.get<ReleasePivotRow[]>("/analytics/pivot/release", { params }).then((r) => r.data),
  byAssignee: (params: Record<string, string | number | undefined>) =>
    api.get<AssigneePivotRow[]>("/analytics/pivot/assignee", { params }).then((r) => r.data),
  assignmentMatrix: (params: Record<string, string | number | undefined>) =>
    api.get<AssignmentMatrix>("/analytics/assignment-matrix", { params }).then((r) => r.data),
  weeklyProgress: (weeks = 8) =>
    api.get<WeeklyProgress>("/analytics/weekly-progress", { params: { weeks } }).then((r) => r.data),
};

export const importApi = {
  uploadTestCases: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post<ImportResult>("/imports/test-cases", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
};

export const testrailApi = {
  projects: () => api.get<TestRailProject[]>("/testrail/projects").then((r) => r.data),
  sync: (project_id: number, suite_id: number) =>
    api
      .post<TestRailSyncResult>("/testrail/sync", { project_id, suite_id })
      .then((r) => r.data),
};

export interface SyncStreamHandlers {
  onLog: (message: string) => void;
  onResult: (data: TestRailSyncResult) => void;
  onError: (message: string) => void;
}

const apiBase = import.meta.env.VITE_API_BASE_URL || "/api/v1";

/** Stream the TestRail sync, invoking handlers as NDJSON lines arrive. */
export async function syncFromTestRailStream(
  project_id: number,
  suite_id: number,
  handlers: SyncStreamHandlers,
): Promise<void> {
  const token = getToken();
  let res: Response;
  try {
    res = await fetch(`${apiBase}/testrail/sync/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ project_id, suite_id }),
    });
  } catch (e) {
    handlers.onError((e as Error)?.message ?? "Network error");
    return;
  }

  if (!res.ok || !res.body) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = j?.detail ?? detail;
    } catch {
      /* ignore */
    }
    handlers.onError(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      try {
        const msg = JSON.parse(line);
        if (msg.type === "log") handlers.onLog(msg.message);
        else if (msg.type === "result") handlers.onResult(msg.data as TestRailSyncResult);
        else if (msg.type === "error") handlers.onError(msg.message);
      } catch {
        handlers.onLog(line);
      }
    }
  }
}
