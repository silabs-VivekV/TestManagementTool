import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CloudSyncIcon from "@mui/icons-material/CloudSync";
import DownloadIcon from "@mui/icons-material/Download";
import TerminalIcon from "@mui/icons-material/Terminal";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { importApi, syncFromTestRailStream, testrailApi } from "@/services/endpoints";
import StatCard from "@/components/StatCard";
import type { ImportResult, TestRailSyncResult } from "@/types";

function refreshDataKeys(qc: ReturnType<typeof useQueryClient>) {
  ["test-cases", "facets", "summary", "dashboards", "analytics"].forEach((k) =>
    qc.invalidateQueries({ queryKey: [k] }),
  );
}

function nowStamp() {
  return new Date().toLocaleTimeString();
}

export default function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [projectId, setProjectId] = useState("9");
  const [suiteId, setSuiteId] = useState("87");
  const [showProjects, setShowProjects] = useState(false);

  const [syncing, setSyncing] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [syncResult, setSyncResult] = useState<TestRailSyncResult | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const consoleRef = useRef<HTMLDivElement | null>(null);

  const queryClient = useQueryClient();

  const importMutation = useMutation<ImportResult, Error, File>({
    mutationFn: (f) => importApi.uploadTestCases(f),
    onSuccess: () => refreshDataKeys(queryClient),
  });

  const downloadMutation = useMutation<Blob, Error, void>({
    mutationFn: () => importApi.downloadMasterList(),
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "Master_Project_List.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    },
  });

  const projectsQuery = useQuery({
    queryKey: ["testrail-projects"],
    queryFn: testrailApi.projects,
    enabled: showProjects,
  });

  // Auto-scroll the console to the latest line.
  useEffect(() => {
    if (consoleRef.current) consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }, [logs]);

  const appendLog = (msg: string) => setLogs((prev) => [...prev, `[${nowStamp()}] ${msg}`]);

  const runSync = async () => {
    setSyncing(true);
    setSyncError(null);
    setSyncResult(null);
    setLogs([`[${nowStamp()}] Starting TestRail sync for Project ${projectId} / Suite ${suiteId}...`]);
    await syncFromTestRailStream(Number(projectId), Number(suiteId), {
      onLog: appendLog,
      onResult: (data) => {
        setSyncResult(data);
        appendLog("Refreshing dashboard data...");
        refreshDataKeys(queryClient);
      },
      onError: (message) => {
        setSyncError(message);
        appendLog(`ERROR: ${message}`);
      },
    });
    setSyncing(false);
  };

  const result: ImportResult | undefined = syncResult?.import_result ?? importMutation.data;
  const fetched = syncResult?.fetched;
  const busy = importMutation.isPending || syncing;

  const errMsg = (e: unknown) =>
    (e as any)?.response?.data?.detail ?? (e as Error)?.message ?? "Operation failed";

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
        <Typography variant="h5">Import Test Cases</Typography>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          disabled={downloadMutation.isPending}
          onClick={() => downloadMutation.mutate()}
        >
          {downloadMutation.isPending ? "Preparing..." : "Download Master_Project_List.xlsx"}
        </Button>
      </Stack>

      {downloadMutation.isError && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={() => downloadMutation.reset()}>
          {(downloadMutation.error as any)?.response?.data?.detail ??
            "Could not download Master_Project_List.xlsx. Run Sync from TestRail first."}
        </Alert>
      )}

      {/* One-shot TestRail pipeline */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
            <CloudSyncIcon color="primary" />
            <Typography variant="h6">Sync from TestRail</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Pulls the Master Project from TestRail, builds the Master Project List, and imports
            it into the tool in one shot. The dashboard updates automatically.
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
            <TextField
              label="Project ID"
              size="small"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value.replace(/\D/g, ""))}
              sx={{ width: 140 }}
            />
            <TextField
              label="Suite ID"
              size="small"
              value={suiteId}
              onChange={(e) => setSuiteId(e.target.value.replace(/\D/g, ""))}
              sx={{ width: 140 }}
            />
            <Tooltip title="Fetch from TestRail and import">
              <span>
                <Button
                  variant="contained"
                  startIcon={<CloudSyncIcon />}
                  disabled={busy || !projectId || !suiteId}
                  onClick={runSync}
                >
                  {syncing ? "Syncing from TestRail..." : "Fetch & Import"}
                </Button>
              </span>
            </Tooltip>
            <Button size="small" onClick={() => setShowProjects((v) => !v)}>
              {showProjects ? "Hide projects" : "Browse project IDs"}
            </Button>
          </Stack>

          {showProjects && (
            <Box sx={{ mt: 2 }}>
              {projectsQuery.isLoading && (
                <Typography variant="body2">Loading projects\u2026</Typography>
              )}
              {projectsQuery.isError && (
                <Alert severity="error">{errMsg(projectsQuery.error)}</Alert>
              )}
              {projectsQuery.data && (
                <Box sx={{ maxHeight: 220, overflow: "auto", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Project ID</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell />
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {projectsQuery.data.map((p) => (
                        <TableRow key={p.id} hover>
                          <TableCell>{p.id}</TableCell>
                          <TableCell>{p.name}</TableCell>
                          <TableCell>
                            <Button size="small" onClick={() => setProjectId(String(p.id))}>
                              Use
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              )}
            </Box>
          )}

          {/* Live console */}
          {(syncing || logs.length > 0) && (
            <Box sx={{ mt: 2 }}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
                <TerminalIcon fontSize="small" />
                <Typography variant="subtitle2">Console</Typography>
                {syncing && (
                  <Typography variant="caption" color="primary">
                    running\u2026
                  </Typography>
                )}
              </Stack>
              <Box
                ref={consoleRef}
                sx={{
                  bgcolor: "#0b1021",
                  color: "#d6e2ff",
                  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                  fontSize: 12.5,
                  lineHeight: 1.6,
                  p: 1.5,
                  borderRadius: 1,
                  height: 240,
                  overflow: "auto",
                  whiteSpace: "pre-wrap",
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                {logs.map((line, i) => (
                  <div
                    key={i}
                    style={{ color: line.includes("ERROR") ? "#ff8585" : undefined }}
                  >
                    {line}
                  </div>
                ))}
                {syncing && <div style={{ opacity: 0.7 }}>\u258b</div>}
              </Box>
            </Box>
          )}

          {syncError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {syncError}
            </Alert>
          )}
        </CardContent>
      </Card>

      <Divider sx={{ mb: 3 }}>or upload a file</Divider>

      {/* Manual file upload */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
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
            disabled={!file || busy}
            onClick={() => file && importMutation.mutate(file)}
          >
            {importMutation.isPending ? "Importing..." : "Import"}
          </Button>
        </CardContent>
      </Card>

      {importMutation.isError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errMsg(importMutation.error)}
        </Alert>
      )}

      {result && (
        <>
          {fetched !== undefined && (
            <Alert severity="success" sx={{ mb: 2 }}>
              Fetched {fetched} cases from TestRail and ran the import below.
            </Alert>
          )}
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={6} md={3}>
              <StatCard label="Total Rows" value={result.total_rows} />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard label="Imported" value={result.imported} color="#22c55e" />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard label="Skipped (dupes)" value={result.skipped_duplicates} color="#f59e0b" />
            </Grid>
            <Grid item xs={6} md={3}>
              <StatCard label="Failed" value={result.failed} color="#ef4444" />
            </Grid>
          </Grid>

          {result.errors.length > 0 && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Issues ({result.errors.length})
                </Typography>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Row</TableCell>
                      <TableCell>Case ID</TableCell>
                      <TableCell>Reason</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.errors.map((err, i) => (
                      <TableRow key={i}>
                        <TableCell>{err.row}</TableCell>
                        <TableCell>{err.case_id ?? "-"}</TableCell>
                        <TableCell>{err.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </Box>
  );
}
