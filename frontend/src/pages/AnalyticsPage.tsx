import {
  Box,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Fragment } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyticsApi } from "@/services/endpoints";

export default function AnalyticsPage() {
  const { data: byTech } = useQuery({
    queryKey: ["analytics", "tech"],
    queryFn: () => analyticsApi.byTechnology({}),
  });
  const { data: byRelease } = useQuery({
    queryKey: ["analytics", "release"],
    queryFn: () => analyticsApi.byRelease({}),
  });
  const { data: matrix } = useQuery({
    queryKey: ["analytics", "matrix"],
    queryFn: () => analyticsApi.assignmentMatrix({}),
  });

  const columns = matrix?.columns ?? [];
  const cell = (n: number | undefined) => (n ? n : "");

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Analytics & Pivot Reports
      </Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Automation assigned test plan
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Assigned test cases per team member, broken down by Test Plan (Section ID) and release.
          </Typography>
          {matrix && matrix.rows.length > 0 ? (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small" sx={{ "& td, & th": { whiteSpace: "nowrap" } }}>
                <TableHead>
                  <TableRow sx={{ bgcolor: "primary.main" }}>
                    <TableCell sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Row Labels
                    </TableCell>
                    {columns.map((c) => (
                      <TableCell
                        key={c}
                        align="right"
                        sx={{ color: "primary.contrastText", fontWeight: 700 }}
                      >
                        {c}
                      </TableCell>
                    ))}
                    <TableCell align="right" sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Grand Total
                    </TableCell>
                    <TableCell sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Current Status
                    </TableCell>
                    <TableCell sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Deadline (ETA)
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {matrix.rows.map((row) => (
                    <Fragment key={`a-${row.assignee_id}`}>
                      <TableRow sx={{ bgcolor: "warning.light" }}>
                        <TableCell sx={{ fontWeight: 700 }}>{row.assignee_name}</TableCell>
                        {columns.map((c) => (
                          <TableCell key={c} align="right" sx={{ fontWeight: 700 }}>
                            {cell(row.by_release[c])}
                          </TableCell>
                        ))}
                        <TableCell align="right" sx={{ fontWeight: 700 }}>
                          {row.total}
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{row.status_summary}</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>{row.deadline_summary}</TableCell>
                      </TableRow>
                      {row.sections.map((sec) => (
                        <TableRow key={`a-${row.assignee_id}-${sec.section_id}`} hover>
                          <TableCell sx={{ pl: 4 }}>{sec.section_id}</TableCell>
                          {columns.map((c) => (
                            <TableCell key={c} align="right">
                              {cell(sec.by_release[c])}
                            </TableCell>
                          ))}
                          <TableCell align="right">{sec.total}</TableCell>
                          <TableCell>{sec.status_summary}</TableCell>
                          <TableCell>{sec.deadline_summary}</TableCell>
                        </TableRow>
                      ))}
                    </Fragment>
                  ))}
                  <TableRow sx={{ bgcolor: "action.selected" }}>
                    <TableCell sx={{ fontWeight: 700 }}>Grand Total</TableCell>
                    {columns.map((c) => (
                      <TableCell key={c} align="right" sx={{ fontWeight: 700 }}>
                        {cell(matrix.column_totals[c])}
                      </TableCell>
                    ))}
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      {matrix.grand_total}
                    </TableCell>
                    <TableCell />
                    <TableCell />
                  </TableRow>
                </TableBody>
              </Table>
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No assignments yet. Assign test cases to team members to see this report.
            </Typography>
          )}
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            By Technology
          </Typography>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={byTech ?? []}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="technology" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="passed" stackId="a" fill="#22c55e" name="Passed" />
              <Bar dataKey="failed" stackId="a" fill="#ef4444" name="Failed" />
              <Bar dataKey="blocked" stackId="a" fill="#f59e0b" name="Blocked" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            By Release
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Release</TableCell>
                <TableCell align="right">Total</TableCell>
                <TableCell align="right">Completed</TableCell>
                <TableCell align="right">Completion %</TableCell>
                <TableCell align="right">Pass Rate</TableCell>
                <TableCell align="right">Fail Rate</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(byRelease ?? []).map((r) => (
                <TableRow key={r.release_version} hover>
                  <TableCell>{r.release_version}</TableCell>
                  <TableCell align="right">{r.total}</TableCell>
                  <TableCell align="right">{r.completed}</TableCell>
                  <TableCell align="right">{r.completion_pct}%</TableCell>
                  <TableCell align="right">{r.pass_rate}%</TableCell>
                  <TableCell align="right">{r.fail_rate}%</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  );
}
