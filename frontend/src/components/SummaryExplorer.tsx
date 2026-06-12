import { useEffect, useMemo, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  TextField,
  Typography,
} from "@mui/material";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { dashboardApi, testCaseApi } from "@/services/endpoints";
import StatCard from "@/components/StatCard";
import { STATUS_COLORS } from "@/theme";
import type { SummaryFilters, TestCaseFacets } from "@/types";

type FilterKey = keyof Omit<SummaryFilters, "assignee">;

const FILTER_FIELDS: { key: FilterKey; label: string }[] = [
  { key: "release_version", label: "Release" },
  { key: "execution_type", label: "Execution Type" },
  { key: "technology", label: "Technology" },
  { key: "product_line", label: "Product Line" },
  { key: "section_id", label: "Section ID" },
  { key: "sdk_type", label: "SDK Type" },
  { key: "product_type", label: "Product Type" },
  { key: "deployment_status", label: "Deployment Status" },
  { key: "test_case_status", label: "Test Case Status" },
];

const FILTERS_STORAGE_KEY = "tt_insights_filters";

function loadStoredFilters(): SummaryFilters {
  try {
    const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SummaryFilters) : {};
  } catch {
    return {};
  }
}

export default function SummaryExplorer() {
  // Persist selections so they survive navigating between Dashboard tabs / reloads.
  const [filters, setFilters] = useState<SummaryFilters>(loadStoredFilters);

  useEffect(() => {
    localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify(filters));
  }, [filters]);

  const { data: facets } = useQuery({ queryKey: ["facets"], queryFn: testCaseApi.facets });

  // Drop empty arrays before querying.
  const cleanFilters = useMemo<SummaryFilters>(() => {
    const out: SummaryFilters = {};
    (Object.keys(filters) as FilterKey[]).forEach((k) => {
      const v = filters[k];
      if (Array.isArray(v) && v.length > 0) out[k] = v;
    });
    return out;
  }, [filters]);

  const { data: summary, isFetching } = useQuery({
    queryKey: ["summary", cleanFilters],
    queryFn: () => dashboardApi.summary(cleanFilters),
    placeholderData: keepPreviousData,
  });

  const activeChips = useMemo(() => {
    const chips: { field: FilterKey; value: string }[] = [];
    (Object.keys(cleanFilters) as FilterKey[]).forEach((k) => {
      (cleanFilters[k] as string[]).forEach((v) => chips.push({ field: k, value: v }));
    });
    return chips;
  }, [cleanFilters]);

  const setField = (key: FilterKey, values: string[]) =>
    setFilters((prev) => ({ ...prev, [key]: values }));

  const removeChip = (field: FilterKey, value: string) =>
    setFilters((prev) => ({
      ...prev,
      [field]: (prev[field] as string[] | undefined)?.filter((v) => v !== value) ?? [],
    }));

  const cards = [
    { label: "Matching Test Cases", value: summary?.total_test_cases ?? 0 },
    { label: "Remaining (not completed)", value: summary?.remaining ?? 0, color: STATUS_COLORS.IN_PROGRESS },
    { label: "Completed", value: summary?.completed ?? 0, color: STATUS_COLORS.PASSED },
    { label: "Passed", value: summary?.passed ?? 0, color: STATUS_COLORS.PASSED },
    { label: "Failed", value: summary?.failed ?? 0, color: STATUS_COLORS.FAILED },
    { label: "Blocked", value: summary?.blocked ?? 0, color: STATUS_COLORS.BLOCKED },
    { label: "Assigned", value: summary?.assigned ?? 0 },
    { label: "Unassigned", value: summary?.unassigned ?? 0, color: STATUS_COLORS.NOT_STARTED },
    { label: "Pending (assigned)", value: summary?.pending ?? 0, color: STATUS_COLORS.IN_PROGRESS },
    { label: "Pass Rate", value: `${summary?.pass_rate ?? 0}%`, color: STATUS_COLORS.PASSED },
  ];

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Filtered Insights
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Select one or more values per field (e.g. Release = 25Q4 + 26Q2, Execution Type = Automatable)
          to see live counts. Filters combine with AND across fields, OR within a field.
        </Typography>

        <Grid container spacing={2} sx={{ mb: 1 }}>
          {FILTER_FIELDS.map((f) => (
            <Grid key={f.key} item xs={12} sm={6} md={3}>
              <Autocomplete
                multiple
                size="small"
                disableCloseOnSelect
                limitTags={2}
                options={(facets?.[f.key as keyof TestCaseFacets] ?? []) as string[]}
                value={(filters[f.key] as string[]) ?? []}
                onChange={(_, values) => setField(f.key, values)}
                renderInput={(params) => <TextField {...params} label={f.label} placeholder="All" />}
              />
            </Grid>
          ))}
        </Grid>

        {activeChips.length > 0 && (
          <Box sx={{ mb: 2, display: "flex", gap: 1, flexWrap: "wrap", alignItems: "center" }}>
            {activeChips.map((c) => (
              <Chip
                key={`${c.field}:${c.value}`}
                size="small"
                label={`${labelFor(c.field)}: ${c.value}`}
                onDelete={() => removeChip(c.field, c.value)}
              />
            ))}
            <Button size="small" startIcon={<FilterAltOffIcon />} onClick={() => setFilters({})}>
              Clear all
            </Button>
          </Box>
        )}

        <Grid container spacing={2} sx={{ opacity: isFetching ? 0.6 : 1 }}>
          {cards.map((c) => (
            <Grid key={c.label} item xs={6} sm={4} md={2.4}>
              <StatCard label={c.label} value={c.value} color={c.color} />
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
}

function labelFor(key: FilterKey): string {
  return FILTER_FIELDS.find((f) => f.key === key)?.label ?? key;
}
