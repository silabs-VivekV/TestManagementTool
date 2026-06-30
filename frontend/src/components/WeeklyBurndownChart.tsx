import { Box, Typography } from "@mui/material";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { WeeklyBucket } from "@/types";

export const WEEKLY_TEAM_TARGET = 20;

interface WeeklyBurndownChartProps {
  weeks: WeeklyBucket[];
  weekTotals: Record<string, number>;
}

export default function WeeklyBurndownChart({ weeks, weekTotals }: WeeklyBurndownChartProps) {
  let cumulativeCompleted = 0;
  const totalTarget = weeks.length * WEEKLY_TEAM_TARGET;

  const chartData = weeks.map((w, index) => {
    const completed = weekTotals[w.key] ?? 0;
    cumulativeCompleted += completed;

    return {
      week: w.label,
      completed,
      targetRemaining: Math.max(totalTarget - WEEKLY_TEAM_TARGET * (index + 1), 0),
      actualRemaining: Math.max(totalTarget - cumulativeCompleted, 0),
    };
  });

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        Weekly Burndown
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Management target: {WEEKLY_TEAM_TARGET} test cases per week (whole team). The ideal line
        burns down by {WEEKLY_TEAM_TARGET} cases each week; the actual line burns down based on
        completed Passed/Failed cases.
      </Typography>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
          <XAxis dataKey="week" />
          <YAxis allowDecimals={false} domain={[0, "auto"]} />
          <Tooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="actualRemaining"
            name="Actual remaining"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
          <Line
            type="monotone"
            dataKey="targetRemaining"
            name="Ideal remaining"
            stroke="#3b82f6"
            strokeDasharray="6 4"
            strokeWidth={2}
            dot={{ r: 4 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </Box>
  );
}
