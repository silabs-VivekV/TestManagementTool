import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { importApi, testCaseApi, type TestCaseFilters } from "@/services/endpoints";

const TECHNOLOGIES = ["", "WLAN STA", "BLE", "BTC", "Concurrent STA + AP"];
const PRIORITIES = ["", "P0", "P1", "P2", "P3"];

export default function TestCasesPage() {
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState("");
  const [technology, setTechnology] = useState("");
  const [priority, setPriority] = useState("");

  const filters: TestCaseFilters = useMemo(
    () => ({
      page: page + 1,
      page_size: pageSize,
      search: search || undefined,
      technology: technology || undefined,
      priority: priority || undefined,
    }),
    [page, pageSize, search, technology, priority]
  );

  const { data, isFetching } = useQuery({
    queryKey: ["test-cases", filters],
    queryFn: () => testCaseApi.list(filters),
    placeholderData: keepPreviousData,
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
          Test Cases {data ? `(${data.total.toLocaleString()})` : ""}
        </Typography>
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
            "Could not download Master_Project_List.xlsx. Ask a lead to run Sync from TestRail first."}
        </Alert>
      )}

      <Box sx={{ display: "flex", gap: 2, mb: 2, flexWrap: "wrap" }}>
        <TextField
          label="Search title / case id"
          size="small"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 260 }}
        />
        <TextField
          select
          label="Technology"
          size="small"
          value={technology}
          onChange={(e) => {
            setTechnology(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 200 }}
        >
          {TECHNOLOGIES.map((t) => (
            <MenuItem key={t} value={t}>
              {t || "All"}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Priority"
          size="small"
          value={priority}
          onChange={(e) => {
            setPriority(e.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 140 }}
        >
          {PRIORITIES.map((p) => (
            <MenuItem key={p} value={p}>
              {p || "All"}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      <TableContainer component={Paper} sx={{ opacity: isFetching ? 0.6 : 1 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Case ID</TableCell>
              <TableCell>Title</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Technology</TableCell>
              <TableCell>Release</TableCell>
              <TableCell>Execution Type</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((tc) => (
              <TableRow key={tc.id} hover>
                <TableCell>{tc.case_id}</TableCell>
                <TableCell sx={{ maxWidth: 480 }}>{tc.title}</TableCell>
                <TableCell>{tc.priority && <Chip size="small" label={tc.priority} />}</TableCell>
                <TableCell>{tc.technology}</TableCell>
                <TableCell>{tc.release_version}</TableCell>
                <TableCell>{tc.execution_type}</TableCell>
              </TableRow>
            ))}
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
          rowsPerPageOptions={[25, 50, 100, 200]}
        />
      </TableContainer>
    </Box>
  );
}
