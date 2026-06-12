import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Divider,
  Grid,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assignmentApi, testCaseApi, userApi } from "@/services/endpoints";
import type {
  AssignByFilterRequest,
  AssignByFilterResult,
  ExecutionStatus,
  TestCaseFacets,
  User,
  UserRole,
} from "@/types";

type FacetKey = keyof TestCaseFacets;

const FILTER_FIELDS: { key: FacetKey; label: string }[] = [
  { key: "release_version", label: "Release" },
  { key: "execution_type", label: "Execution Type" },
  { key: "technology", label: "Technology" },
  { key: "product_line", label: "Product Line" },
  { key: "section_id", label: "Section ID (Test Plan)" },
  { key: "sdk_type", label: "SDK Type" },
  { key: "product_type", label: "Product Type" },
  { key: "deployment_status", label: "Deployment Status" },
  { key: "test_case_status", label: "Test Case Status" },
  { key: "priority", label: "Priority" },
];

const STATUSES: ExecutionStatus[] = [
  "NOT_STARTED",
  "IN_PROGRESS",
  "BLOCKED",
  "PASSED",
  "FAILED",
  "NEEDS_REVIEW",
  "TEST_AGENT_SUPPORT",
  "SDK_SUPPORT_MISSING",
  "TEST_STEPS_MISSING",
];

export default function AssignPage() {
  const [filters, setFilters] = useState<Record<string, string[]>>({});
  const [search, setSearch] = useState("");
  const [caseIdsText, setCaseIdsText] = useState("");
  const [assignedTo, setAssignedTo] = useState<number | "">("");
  const [statusValue, setStatusValue] = useState<ExecutionStatus>("NOT_STARTED");
  const [eta, setEta] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [newMemberName, setNewMemberName] = useState("");
  const [newMemberRole, setNewMemberRole] = useState<UserRole>("TEAM_MEMBER");
  const queryClient = useQueryClient();

  const { data: facets } = useQuery({ queryKey: ["facets"], queryFn: testCaseApi.facets });
  const { data: users } = useQuery({ queryKey: ["users"], queryFn: userApi.list });

  const addMemberMutation = useMutation<User, Error, void>({
    mutationFn: () => userApi.quickCreate(newMemberName.trim(), newMemberRole),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setAssignedTo(created.id);
      setNewMemberName("");
    },
  });

  const caseIds = useMemo(
    () =>
      caseIdsText
        .split(/[\s,;]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    [caseIdsText],
  );

  // Build the criteria payload (without assignee) shared by preview + assign.
  const criteria = useMemo<AssignByFilterRequest>(() => {
    const out: AssignByFilterRequest = {};
    Object.entries(filters).forEach(([k, v]) => {
      if (Array.isArray(v) && v.length > 0) (out as any)[k] = v;
    });
    if (search.trim()) out.search = search.trim();
    if (caseIds.length > 0) out.case_ids = caseIds;
    return out;
  }, [filters, search, caseIds]);

  const hasCriteria =
    Object.keys(criteria).length > 0 && JSON.stringify(criteria) !== "{}";

  const { data: preview, isFetching: previewing } = useQuery({
    queryKey: ["assign-preview", criteria],
    queryFn: () => assignmentApi.byFilter({ ...criteria, dry_run: true }),
    enabled: hasCriteria,
    placeholderData: keepPreviousData,
  });

  // Reset row selection whenever the criteria (and thus the matched set) change.
  useEffect(() => {
    setSelected(new Set());
  }, [criteria]);

  const assignMutation = useMutation<AssignByFilterResult, Error, void>({
    mutationFn: () => {
      // If specific rows are ticked, assign exactly those; otherwise assign all matched.
      const payload: AssignByFilterRequest =
        selected.size > 0 ? { case_ids: [...selected] } : { ...criteria };
      return assignmentApi.byFilter({
        ...payload,
        assigned_to: assignedTo as number,
        status: statusValue,
        eta: eta || undefined,
        dry_run: false,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assignments"] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      setSelected(new Set());
    },
  });

  const matched = preview?.matched ?? 0;
  const items = preview?.items ?? [];
  const setField = (key: FacetKey, values: string[]) =>
    setFilters((prev) => ({ ...prev, [key]: values }));
  const clearAll = () => {
    setFilters({});
    setSearch("");
    setCaseIdsText("");
  };

  const toggleRow = (caseId: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(caseId)) next.delete(caseId);
      else next.add(caseId);
      return next;
    });
  const allLoadedSelected = items.length > 0 && items.every((i) => selected.has(i.case_id));
  const toggleAll = () =>
    setSelected(() => (allLoadedSelected ? new Set() : new Set(items.map((i) => i.case_id))));

  const assignCount = selected.size > 0 ? selected.size : matched;

  const errMsg = (e: unknown) =>
    (e as any)?.response?.data?.detail ?? (e as Error)?.message ?? "Failed";

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <AssignmentIndIcon color="primary" />
        <Typography variant="h5">Assign Test Cases</Typography>
      </Stack>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            1. Choose which test cases to assign
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Filter by Release, Section ID (test plan), Technology, etc.; search by title/Case ID;
            or paste specific Case IDs. Criteria combine together.
          </Typography>

          <Grid container spacing={2}>
            {FILTER_FIELDS.map((f) => (
              <Grid key={f.key} item xs={12} sm={6} md={3}>
                <Autocomplete
                  multiple
                  size="small"
                  disableCloseOnSelect
                  limitTags={2}
                  options={(facets?.[f.key] ?? []) as string[]}
                  value={filters[f.key] ?? []}
                  onChange={(_, values) => setField(f.key, values)}
                  renderInput={(params) => (
                    <TextField {...params} label={f.label} placeholder="All" />
                  )}
                />
              </Grid>
            ))}
          </Grid>

          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                size="small"
                label="Search (title or Case ID contains)"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                size="small"
                label="Case IDs (comma / space / newline separated)"
                placeholder="19673, 19674, 1742318"
                value={caseIdsText}
                onChange={(e) => setCaseIdsText(e.target.value)}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
            <Chip
              color={matched > 0 ? "primary" : "default"}
              label={
                !hasCriteria
                  ? "Set criteria to preview"
                  : previewing
                    ? "Counting..."
                    : `${matched.toLocaleString()} test case(s) match`
              }
            />
            <Button size="small" onClick={clearAll}>
              Clear criteria
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" gutterBottom>
            2. Assign to a team member
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Team members ({users?.length ?? 0}) — click to select:
          </Typography>
          <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
            {(users ?? []).map((u) => (
              <Chip
                key={u.id}
                label={`${u.name} · ${u.role}`}
                color={assignedTo === u.id ? "primary" : "default"}
                variant={assignedTo === u.id ? "filled" : "outlined"}
                onClick={() => setAssignedTo(u.id)}
                size="small"
              />
            ))}
            {(users ?? []).length === 0 && (
              <Typography variant="body2" color="text.secondary">
                No members yet — add one below.
              </Typography>
            )}
          </Box>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
            <TextField
              select
              size="small"
              label="Team member"
              value={assignedTo}
              onChange={(e) => setAssignedTo(Number(e.target.value))}
              sx={{ minWidth: 240 }}
            >
              {(users ?? []).map((u) => (
                <MenuItem key={u.id} value={u.id}>
                  {u.name} · {u.role}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Initial status"
              value={statusValue}
              onChange={(e) => setStatusValue(e.target.value as ExecutionStatus)}
              sx={{ minWidth: 180 }}
            >
              {STATUSES.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              type="date"
              label="ETA (deadline)"
              value={eta}
              onChange={(e) => setEta(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 170 }}
            />
            <Button
              variant="contained"
              disabled={!hasCriteria || !assignedTo || assignCount === 0 || assignMutation.isPending}
              onClick={() => assignMutation.mutate()}
            >
              {assignMutation.isPending
                ? "Assigning..."
                : selected.size > 0
                  ? `Assign ${selected.size} selected`
                  : `Assign all ${matched.toLocaleString()}`}
            </Button>
          </Stack>

          <Divider sx={{ my: 2 }} />
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Not in the list? Add a new team member:
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
            <TextField
              size="small"
              label="New member name"
              value={newMemberName}
              onChange={(e) => setNewMemberName(e.target.value)}
              sx={{ minWidth: 220 }}
            />
            <TextField
              select
              size="small"
              label="Role"
              value={newMemberRole}
              onChange={(e) => setNewMemberRole(e.target.value as UserRole)}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="TEAM_MEMBER">TEAM_MEMBER</MenuItem>
              <MenuItem value="TEAM_LEAD">TEAM_LEAD</MenuItem>
            </TextField>
            <Button
              variant="outlined"
              startIcon={<PersonAddIcon />}
              disabled={!newMemberName.trim() || addMemberMutation.isPending}
              onClick={() => addMemberMutation.mutate()}
            >
              {addMemberMutation.isPending ? "Adding..." : "Add member"}
            </Button>
          </Stack>
          {addMemberMutation.isError && (
            <Alert severity="error" sx={{ mt: 1 }}>
              {errMsg(addMemberMutation.error)}
            </Alert>
          )}
          {addMemberMutation.data && (
            <Alert severity="success" sx={{ mt: 1 }}>
              Added {addMemberMutation.data.name} (login: {addMemberMutation.data.email} / default
              password <code>Welcome@123</code>) and selected them.
            </Alert>
          )}

          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
            Each test case keeps one current owner — assigning again reassigns it to the selected
            member.
          </Typography>

          {assignMutation.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {errMsg(assignMutation.error)}
            </Alert>
          )}
          {assignMutation.data && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Done — {assignMutation.data.assigned} newly assigned, {assignMutation.data.reassigned}{" "}
              reassigned (out of {assignMutation.data.matched} matched).
            </Alert>
          )}
        </CardContent>
      </Card>

      {items.length > 0 && (
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }} flexWrap="wrap" gap={1}>
            <Typography variant="subtitle2">
              Matching test cases — showing {items.length.toLocaleString()} of{" "}
              {matched.toLocaleString()}
              {selected.size > 0 ? ` · ${selected.size} ticked` : ""}
            </Typography>
            {selected.size > 0 && (
              <Button size="small" onClick={() => setSelected(new Set())}>
                Clear selection
              </Button>
            )}
          </Stack>

          {/* Inline assign bar — assign the ticked cases to a member without scrolling up */}
          {selected.size > 0 && (
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={2}
              alignItems="center"
              sx={{ mb: 1.5, p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}
            >
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {selected.size} selected →
              </Typography>
              <TextField
                select
                size="small"
                label="Assign to"
                value={assignedTo}
                onChange={(e) => setAssignedTo(Number(e.target.value))}
                sx={{ minWidth: 220 }}
              >
                {(users ?? []).map((u) => (
                  <MenuItem key={u.id} value={u.id}>
                    {u.name} · {u.role}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                size="small"
                label="Status"
                value={statusValue}
                onChange={(e) => setStatusValue(e.target.value as ExecutionStatus)}
                sx={{ minWidth: 160 }}
              >
                {STATUSES.map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                size="small"
                type="date"
                label="ETA (deadline)"
                value={eta}
                onChange={(e) => setEta(e.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 170 }}
              />
              <Button
                variant="contained"
                disabled={!assignedTo || assignMutation.isPending}
                onClick={() => assignMutation.mutate()}
              >
                {assignMutation.isPending ? "Assigning..." : `Assign ${selected.size} selected`}
              </Button>
            </Stack>
          )}
          {preview?.truncated && (
            <Alert severity="info" sx={{ mb: 1 }}>
              Only the first {items.length.toLocaleString()} rows are listed for ticking. Narrow the
              filters to tick specific cases, or use “Assign all {matched.toLocaleString()}”.
            </Alert>
          )}
          <Divider sx={{ mb: 1 }} />
          <Box sx={{ maxHeight: 480, overflow: "auto" }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={allLoadedSelected}
                      indeterminate={selected.size > 0 && !allLoadedSelected}
                      onChange={toggleAll}
                    />
                  </TableCell>
                  <TableCell>Case ID</TableCell>
                  <TableCell>Test Plan (Section ID)</TableCell>
                  <TableCell>Title</TableCell>
                  <TableCell>Current owner</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((s) => (
                  <TableRow key={s.case_id} hover selected={selected.has(s.case_id)}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        size="small"
                        checked={selected.has(s.case_id)}
                        onChange={() => toggleRow(s.case_id)}
                      />
                    </TableCell>
                    <TableCell>{s.case_id}</TableCell>
                    <TableCell sx={{ maxWidth: 240 }}>{s.section_id ?? "—"}</TableCell>
                    <TableCell sx={{ maxWidth: 480 }}>{s.title}</TableCell>
                    <TableCell>{s.current_assignee ?? "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Paper>
      )}
    </Box>
  );
}
