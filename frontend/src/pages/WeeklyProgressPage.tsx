import {
  Box,
  Card,
  CardContent,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import WeeklyBurndownChart from "@/components/WeeklyBurndownChart";
import { analyticsApi } from "@/services/endpoints";

const WEEK_OPTIONS = [4, 8, 12, 16, 26];

export default function WeeklyProgressPage() {
  const [weeks, setWeeks] = useState(8);
  const { data } = useQuery({
    queryKey: ["analytics", "weekly", weeks],
    queryFn: () => analyticsApi.weeklyProgress(weeks),
  });

  const cell = (n: number | undefined) => (n ? n : "");

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Weekly Progress
      </Typography>

      <Card>
        <CardContent>
          <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
            <Box>
              <Typography variant="h6">Test cases completed per team member</Typography>
              <Typography variant="body2" color="text.secondary">
                Counts a test case in the week its status was changed to Passed or Failed. The On
                time / Late / Overdue columns compare each assignment against its ETA (deadline).
              </Typography>
            </Box>
            <TextField
              select
              size="small"
              label="Weeks"
              value={weeks}
              onChange={(e) => setWeeks(Number(e.target.value))}
              sx={{ minWidth: 120 }}
            >
              {WEEK_OPTIONS.map((w) => (
                <MenuItem key={w} value={w}>
                  Last {w}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          {data && data.rows.length > 0 ? (
            <Box sx={{ overflowX: "auto" }}>
              <Table size="small" sx={{ "& td, & th": { whiteSpace: "nowrap" } }}>
                <TableHead>
                  <TableRow sx={{ bgcolor: "primary.main" }}>
                    <TableCell sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Team member
                    </TableCell>
                    {data.weeks.map((w) => (
                      <TableCell
                        key={w.key}
                        align="right"
                        sx={{ color: "primary.contrastText", fontWeight: 700 }}
                      >
                        {w.label}
                      </TableCell>
                    ))}
                    <TableCell align="right" sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Total
                    </TableCell>
                    <TableCell align="right" sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      On time
                    </TableCell>
                    <TableCell align="right" sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Late
                    </TableCell>
                    <TableCell align="right" sx={{ color: "primary.contrastText", fontWeight: 700 }}>
                      Overdue
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.rows.map((row) => (
                    <TableRow key={row.assignee_id} hover>
                      <TableCell sx={{ fontWeight: 600 }}>{row.assignee_name}</TableCell>
                      {data.weeks.map((w) => (
                        <TableCell key={w.key} align="right">
                          {cell(row.by_week[w.key])}
                        </TableCell>
                      ))}
                      <TableCell align="right" sx={{ fontWeight: 700 }}>
                        {row.total}
                      </TableCell>
                      <TableCell align="right" sx={{ color: "success.main", fontWeight: 600 }}>
                        {cell(row.on_time)}
                      </TableCell>
                      <TableCell align="right" sx={{ color: "warning.main", fontWeight: 600 }}>
                        {cell(row.late)}
                      </TableCell>
                      <TableCell align="right" sx={{ color: "error.main", fontWeight: 600 }}>
                        {cell(row.overdue)}
                      </TableCell>
                    </TableRow>
                  ))}
                  <TableRow sx={{ bgcolor: "action.selected" }}>
                    <TableCell sx={{ fontWeight: 700 }}>Grand Total</TableCell>
                    {data.weeks.map((w) => (
                      <TableCell key={w.key} align="right" sx={{ fontWeight: 700 }}>
                        {cell(data.week_totals[w.key])}
                      </TableCell>
                    ))}
                    <TableCell align="right" sx={{ fontWeight: 700 }}>
                      {data.grand_total}
                    </TableCell>
                    <TableCell align="right" sx={{ color: "success.main", fontWeight: 700 }}>
                      {cell(data.total_on_time)}
                    </TableCell>
                    <TableCell align="right" sx={{ color: "warning.main", fontWeight: 700 }}>
                      {cell(data.total_late)}
                    </TableCell>
                    <TableCell align="right" sx={{ color: "error.main", fontWeight: 700 }}>
                      {cell(data.total_overdue)}
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <WeeklyBurndownChart weeks={data.weeks} weekTotals={data.week_totals} />
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No completed test cases yet. Progress appears here once members mark cases as
              Passed/Failed.
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
