import { useMemo, useState, useEffect, useRef } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import PersonOffIcon from "@mui/icons-material/PersonOff";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assignmentApi, userApi } from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import StatCard from "@/components/StatCard";
import { STATUS_COLORS } from "@/theme";
import {
  DETAIL_FIELD_LABELS,
  DETAIL_FIELDS,
  isFieldRequired,
  type AssignmentDetailField,
} from "@/utils/assignmentStatusFields";
import type { AssignmentImportResult, ExecutionStatus } from "@/types";

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

const DETAIL_SAVE_DELAY_MS = 600;

function AssignmentDetailFieldInput({
  assignmentId,
  field,
  savedValue,
  required,
  onSave,
}: {
  assignmentId: number;
  field: AssignmentDetailField;
  savedValue: string;
  required: boolean;
  onSave: (id: number, field: AssignmentDetailField, value: string) => void;
}) {
  const [draft, setDraft] = useState(savedValue);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setDraft(savedValue);
  }, [savedValue, assignmentId, field]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const scheduleSave = (next: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (next !== savedValue) {
        onSave(assignmentId, field, next);
      }
    }, DETAIL_SAVE_DELAY_MS);
  };

  const showError = required && !draft.trim();

  return (
    <TextField
      size="small"
      multiline
      minRows={1}
      maxRows={3}
      value={draft}
      placeholder={required ? `${DETAIL_FIELD_LABELS[field]} *` : DETAIL_FIELD_LABELS[field]}
      error={showError}
      onChange={(e) => {
        const next = e.target.value;
        setDraft(next);
        scheduleSave(next);
      }}
      onBlur={() => {
        if (timerRef.current) {
          clearTimeout(timerRef.current);
          timerRef.current = null;
        }
        if (draft !== savedValue) {
          onSave(assignmentId, field, draft);
        }
      }}
      sx={{ minWidth: 150 }}
    />
  );
}

export default function AssignmentsPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [statusFilter, setStatusFilter] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const canManage = hasRole("ADMIN", "TEAM_LEAD");

  const importMutation = useMutation<AssignmentImportResult, Error, File>({
    mutationFn: (f) => assignmentApi.importSheet(f),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assignments"] }),
  });
  const importResult = importMutation.data;

  const downloadMutation = useMutation<Blob, Error, void>({
    mutationFn: () => assignmentApi.exportSheet(),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Assigned_Test_Cases_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const params = useMemo(
    () => ({ page: page + 1, page_size: pageSize, status: statusFilter || undefined }),
    [page, pageSize, statusFilter]
  );

  const { data, isFetching } = useQuery({
    queryKey: ["assignments", params],
    queryFn: () => assignmentApi.list(params),
    placeholderData: keepPreviousData,
  });

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: userApi.list,
    enabled: canManage,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ExecutionStatus }) =>
      assignmentApi.updateStatus(id, { status }),
    onSuccess: () => {
      setStatusError(null);
      queryClient.invalidateQueries({ queryKey: ["assignments"] });
    },
    onError: (err: Error) => {
      setStatusError(
        (err as any)?.response?.data?.detail ?? "Could not update status. Fill required fields first.",
      );
    },
  });

  const detailMutation = useMutation({
    mutationFn: ({
      id,
      field,
      value,
    }: {
      id: number;
      field: AssignmentDetailField;
      value: string;
    }) => assignmentApi.updateStatus(id, { [field]: value || null }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assignments"] }),
  });

  const reassignMutation = useMutation({
    mutationFn: ({ id, assigned_to }: { id: number; assigned_to: number }) =>
      assignmentApi.reassign(id, assigned_to),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assignments"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => assignmentApi.remove(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assignments"] }),
  });

  const etaMutation = useMutation({
    mutationFn: ({ id, eta }: { id: number; eta: string | null }) =>
      assignmentApi.updateStatus(id, { eta }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["assignments"] }),
  });

  return (
    <Box>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ mb: 2 }}
        flexWrap="wrap"
        gap={1}
      >
        <Typography variant="h5">
          Assignments {data ? `(${data.total.toLocaleString()})` : ""}
        </Typography>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          disabled={downloadMutation.isPending}
          onClick={() => downloadMutation.mutate()}
        >
          {downloadMutation.isPending ? "Preparing..." : "Download assignment sheet"}
        </Button>
      </Stack>

      {statusError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setStatusError(null)}>
          {statusError}
        </Alert>
      )}

      {canManage && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Assign from Excel
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload a sheet with <strong>Case ID</strong>, <strong>Assignee</strong>, and
              optional <strong>Status</strong> / <strong>Comments</strong> / <strong>ETA</strong>{" "}
              columns. Each case is
              assigned to the named member; re-importing updates the current owner. Unknown
              members are created automatically as team members.
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
              <Button variant="outlined" component="label" startIcon={<UploadFileIcon />}>
                Choose .csv / .xlsx
                <input
                  hidden
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </Button>
              <Typography variant="body2" color="text.secondary">
                {file ? file.name : "No file selected"}
              </Typography>
              <Button
                variant="contained"
                disabled={!file || importMutation.isPending}
                onClick={() => file && importMutation.mutate(file)}
              >
                {importMutation.isPending ? "Assigning..." : "Import & Assign"}
              </Button>
            </Stack>

            {importMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {(importMutation.error as any)?.response?.data?.detail ?? "Import failed"}
              </Alert>
            )}

            {importResult && (
              <Box sx={{ mt: 2 }}>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={2.4}>
                    <StatCard label="Rows" value={importResult.total_rows} />
                  </Grid>
                  <Grid item xs={6} md={2.4}>
                    <StatCard label="Assigned" value={importResult.assigned} color="#22c55e" />
                  </Grid>
                  <Grid item xs={6} md={2.4}>
                    <StatCard label="Reassigned" value={importResult.reassigned} color="#3b82f6" />
                  </Grid>
                  <Grid item xs={6} md={2.4}>
                    <StatCard label="Members created" value={importResult.users_created} color="#f59e0b" />
                  </Grid>
                  <Grid item xs={6} md={2.4}>
                    <StatCard label="Failed" value={importResult.failed} color="#ef4444" />
                  </Grid>
                </Grid>
                {importResult.created_users.length > 0 && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    New members created (default password <code>Welcome@123</code>):{" "}
                    {importResult.created_users.join(", ")}
                  </Alert>
                )}
                {importResult.errors.length > 0 && (
                  <Box sx={{ mt: 2, maxHeight: 200, overflow: "auto" }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Row</TableCell>
                          <TableCell>Case ID</TableCell>
                          <TableCell>Reason</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {importResult.errors.map((e, i) => (
                          <TableRow key={i}>
                            <TableCell>{e.row}</TableCell>
                            <TableCell>{e.case_id ?? "-"}</TableCell>
                            <TableCell>{e.reason}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                )}
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      <TextField
        select
        label="Status"
        size="small"
        value={statusFilter}
        onChange={(e) => {
          setStatusFilter(e.target.value);
          setPage(0);
        }}
        sx={{ minWidth: 200, mb: 2 }}
      >
        <MenuItem value="">All</MenuItem>
        {STATUSES.map((s) => (
          <MenuItem key={s} value={s}>
            {s}
          </MenuItem>
        ))}
      </TextField>

      <Alert severity="info" sx={{ mb: 2 }}>
        Required fields for each status are marked with <strong>*</strong>. Comment, Jira Details,
        and PR Details save automatically as you type.
      </Alert>

      <TableContainer component={Paper} sx={{ opacity: isFetching ? 0.6 : 1 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Case ID</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Assignee</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>ETA</TableCell>
              {DETAIL_FIELDS.map((field) => (
                <TableCell key={field}>{DETAIL_FIELD_LABELS[field]}</TableCell>
              ))}
              {canManage && <TableCell align="center">Actions</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((a) => (
              <TableRow key={a.id} hover>
                <TableCell>{a.test_case?.case_id}</TableCell>
                <TableCell sx={{ maxWidth: 280 }}>{a.test_case?.title}</TableCell>
                <TableCell>
                  {canManage ? (
                    <Select
                      size="small"
                      value={users?.some((u) => u.id === a.assigned_to) ? a.assigned_to : ""}
                      displayEmpty
                      onChange={(e) =>
                        reassignMutation.mutate({ id: a.id, assigned_to: Number(e.target.value) })
                      }
                      sx={{ minWidth: 140 }}
                    >
                      {!users?.some((u) => u.id === a.assigned_to) && (
                        <MenuItem value="" disabled>
                          {a.assignee_name ?? "Unknown"}
                        </MenuItem>
                      )}
                      {(users ?? []).map((u) => (
                        <MenuItem key={u.id} value={u.id}>
                          {u.name}
                        </MenuItem>
                      ))}
                    </Select>
                  ) : (
                    a.assignee_name
                  )}
                </TableCell>
                <TableCell>
                  <Select
                    size="small"
                    value={a.status}
                    onChange={(e) =>
                      statusMutation.mutate({ id: a.id, status: e.target.value as ExecutionStatus })
                    }
                    sx={{ minWidth: 170 }}
                    renderValue={(value) => (
                      <Chip
                        size="small"
                        label={value}
                        sx={{ bgcolor: STATUS_COLORS[value as ExecutionStatus], color: "#fff" }}
                      />
                    )}
                  >
                    {STATUSES.map((s) => (
                      <MenuItem key={s} value={s}>
                        {s}
                      </MenuItem>
                    ))}
                  </Select>
                </TableCell>
                <TableCell>
                  {canManage ? (
                    <TextField
                      size="small"
                      type="date"
                      value={a.eta ? a.eta.slice(0, 10) : ""}
                      onChange={(e) =>
                        etaMutation.mutate({ id: a.id, eta: e.target.value || null })
                      }
                      InputLabelProps={{ shrink: true }}
                      sx={{ width: 140 }}
                    />
                  ) : (
                    a.eta?.slice(0, 10) ?? "\u2014"
                  )}
                </TableCell>
                {DETAIL_FIELDS.map((field) => {
                  const required = isFieldRequired(a.status, field);
                  const value = (a[field] as string | null | undefined) ?? "";
                  return (
                    <TableCell key={field}>
                      <AssignmentDetailFieldInput
                        assignmentId={a.id}
                        field={field}
                        savedValue={value}
                        required={required}
                        onSave={(id, f, v) => detailMutation.mutate({ id, field: f, value: v })}
                      />
                    </TableCell>
                  );
                })}
                {canManage && (
                  <TableCell align="center">
                    <Tooltip title="Unassign (remove this assignment)">
                      <span>
                        <IconButton
                          size="small"
                          color="error"
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            if (
                              window.confirm(
                                `Unassign ${a.test_case?.case_id ?? "this test case"} from ${
                                  a.assignee_name ?? "the current owner"
                                }? The test case will have no owner until reassigned.`
                              )
                            ) {
                              deleteMutation.mutate(a.id);
                            }
                          }}
                        >
                          <PersonOffIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                )}
              </TableRow>
            ))}
            {data && data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={canManage ? 9 : 8} align="center" sx={{ py: 4 }}>
                  No assignments yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={data?.total ?? 0}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(e) => {
            setPageSize(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[25, 50, 100]}
        />
      </TableContainer>
    </Box>
  );
}
