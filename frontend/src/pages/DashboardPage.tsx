import { Box, Card, CardContent, Grid, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { dashboardApi } from "@/services/endpoints";
import { useAuth } from "@/hooks/useAuth";
import StatCard from "@/components/StatCard";
import SummaryExplorer from "@/components/SummaryExplorer";
import { STATUS_COLORS } from "@/theme";

export default function DashboardPage() {
  const { hasRole } = useAuth();
  const isLeadOrAdmin = hasRole("ADMIN", "TEAM_LEAD");

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 3 }}>
        Dashboard
      </Typography>
      <SummaryExplorer />
      {isLeadOrAdmin ? <LeadDashboard /> : <MemberDashboard />}
    </Box>
  );
}

function LeadDashboard() {
  const { data: exec } = useQuery({ queryKey: ["dash", "exec"], queryFn: dashboardApi.executive });
  const { data: lead } = useQuery({ queryKey: ["dash", "lead"], queryFn: dashboardApi.teamLead });

  const stats = [
    { label: "Total Test Cases", value: exec?.total_test_cases ?? 0 },
    { label: "Assigned", value: exec?.assigned ?? 0 },
    { label: "Completed", value: exec?.completed ?? 0, color: STATUS_COLORS.PASSED },
    { label: "Pending", value: exec?.pending ?? 0, color: STATUS_COLORS.IN_PROGRESS },
    { label: "Blocked", value: exec?.blocked ?? 0, color: STATUS_COLORS.BLOCKED },
    { label: "Failed", value: exec?.failed ?? 0, color: STATUS_COLORS.FAILED },
    { label: "Pass Rate", value: `${exec?.pass_rate ?? 0}%`, color: STATUS_COLORS.PASSED },
  ];

  return (
    <Grid container spacing={2}>
      {stats.map((s) => (
        <Grid key={s.label} item xs={12} sm={6} md={3}>
          <StatCard label={s.label} value={s.value} color={s.color} />
        </Grid>
      ))}

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Assignment Distribution
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={lead?.assignment_distribution ?? []}
                  dataKey="count"
                  nameKey="status"
                  outerRadius={100}
                  label
                >
                  {(lead?.assignment_distribution ?? []).map((entry) => (
                    <Cell key={entry.status} fill={STATUS_COLORS[entry.status] ?? "#888"} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Release Progress
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={lead?.release_progress ?? []}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="release_version" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="total" fill="#3b82f6" name="Total" />
                <Bar dataKey="completed" fill="#22c55e" name="Completed" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

function MemberDashboard() {
  const { data } = useQuery({ queryKey: ["dash", "member"], queryFn: dashboardApi.teamMember });
  const stats = [
    { label: "My Assignments", value: data?.my_assignments ?? 0 },
    { label: "Completed", value: data?.my_completed ?? 0, color: STATUS_COLORS.PASSED },
    { label: "In Progress", value: data?.my_in_progress ?? 0, color: STATUS_COLORS.IN_PROGRESS },
    { label: "Open Defects", value: data?.my_open_defects ?? 0, color: STATUS_COLORS.FAILED },
    { label: "Blocked", value: data?.my_blocked ?? 0, color: STATUS_COLORS.BLOCKED },
  ];
  return (
    <Grid container spacing={2}>
      {stats.map((s) => (
        <Grid key={s.label} item xs={12} sm={6} md={3}>
          <StatCard label={s.label} value={s.value} color={s.color} />
        </Grid>
      ))}
    </Grid>
  );
}
