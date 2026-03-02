import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export interface DemographicsData {
  population: number;
  median_age: number;
  median_household_income: number;
  median_home_value: number;
  median_gross_rent: number;
  households: number;
  education: {
    hs_diploma: number;
    some_college: number;
    associates: number;
    bachelors: number;
    graduate: number;
  };
  race: {
    white: number;
    black: number;
    american_indian: number;
    asian: number;
    pacific_islander: number;
  };
  fips: Record<string, string>;
  geography_level: string;
  geography_label: string;
  boundary: object | null;
}

interface DemoPanelProps {
  data: DemographicsData | null;
  loading: boolean;
}

const fmt = new Intl.NumberFormat("en-US");
const fmtCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const TEAL = "#0ea5e9";
const TEAL_DIM = "#0284c7";

function toPercents(values: number[]): number[] {
  const total = values.reduce((a, b) => a + b, 0);
  if (total === 0) return values.map(() => 0);
  return values.map((v) => parseFloat(((v / total) * 100).toFixed(1)));
}

function makeChartData(labels: string[], rawValues: number[], colors: string[]) {
  const percents = toPercents(rawValues);
  return {
    labels,
    datasets: [
      {
        data: percents,
        rawValues,
        backgroundColor: colors,
        borderRadius: 4,
      },
    ],
  };
}

const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: { raw: unknown; dataset: { rawValues?: number[] }; dataIndex: number }) => {
          const pct = ctx.raw as number;
          const raw = ctx.dataset.rawValues?.[ctx.dataIndex] ?? 0;
          return ` ${pct}% (${fmt.format(raw)} people)`;
        },
      },
    },
  },
  scales: {
    x: {
      ticks: { color: "#94a3b8", font: { size: 12 } },
      grid: { color: "#2e3a5c" },
    },
    y: {
      ticks: {
        color: "#94a3b8",
        font: { size: 12 },
        callback: (v: number | string) => `${v}%`,
      },
      grid: { color: "#2e3a5c" },
    },
  },
} as const;

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-lg p-3"
      style={{ backgroundColor: "#0f1628", border: "1px solid #2e3a5c" }}
    >
      <p className="text-sm" style={{ color: "#64748b" }}>
        {label}
      </p>
      <p className="mt-1 text-base font-semibold text-white">{value}</p>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="h-12 animate-pulse rounded-lg"
          style={{ backgroundColor: "#0f1628" }}
        />
      ))}
    </div>
  );
}

export default function DemoPanel({ data, loading }: DemoPanelProps) {
  if (loading) return <Skeleton />;

  if (!data || data.geography_level === "unavailable") {
    return (
      <p className="text-sm" style={{ color: "#64748b" }}>
        Demographic data unavailable for this location.
      </p>
    );
  }

  const showFallbackBanner = data.geography_level !== "block_group";
  const fallbackLevel = data.geography_level === "tract" ? "tract" : "county";

  const eduData = makeChartData(
    ["HS Diploma", "Some College", "Associates", "Bachelors", "Graduate"],
    [
      data.education.hs_diploma,
      data.education.some_college,
      data.education.associates,
      data.education.bachelors,
      data.education.graduate,
    ],
    [TEAL, TEAL_DIM, TEAL, TEAL_DIM, TEAL],
  );

  const raceData = makeChartData(
    ["White", "Black", "Am. Indian", "Asian", "Pac. Islander"],
    [
      data.race.white,
      data.race.black,
      data.race.american_indian,
      data.race.asian,
      data.race.pacific_islander,
    ],
    [TEAL, TEAL_DIM, TEAL, TEAL_DIM, TEAL],
  );

  return (
    <div className="flex h-full flex-col justify-between gap-4">
      {/* Fallback banner */}
      {showFallbackBanner && (
        <div
          className="rounded-lg px-3 py-2 text-sm text-white"
          style={{ backgroundColor: "#0f1628", border: "1px solid #2e3a5c" }}
        >
          Block group data unavailable — showing {fallbackLevel}-level data
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Population" value={fmt.format(data.population)} />
        <StatCard label="Median Age" value={`${data.median_age} yrs`} />
        <StatCard
          label="Median HH Income"
          value={data.median_household_income > 0 ? fmtCurrency.format(data.median_household_income) : "N/A"}
        />
        <StatCard
          label="Median Home Value"
          value={data.median_home_value > 0 ? fmtCurrency.format(data.median_home_value) : "N/A"}
        />
      </div>
      <StatCard
        label="Median Gross Rent"
        value={data.median_gross_rent > 0 ? fmtCurrency.format(data.median_gross_rent) + "/mo" : "N/A"}
      />

      {/* Education chart */}
      <div>
        <p className="mb-2 text-sm font-medium text-white">
          Educational Attainment
        </p>
        <div style={{ height: 140 }}>
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Bar data={eduData as any} options={CHART_OPTS as any} />
        </div>
      </div>

      {/* Race chart */}
      <div>
        <p className="mb-2 text-sm font-medium text-white">
          Race / Ethnicity
        </p>
        <div style={{ height: 140 }}>
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Bar data={raceData as any} options={CHART_OPTS as any} />
        </div>
      </div>

      {/* FIPS footnote */}
      <p className="text-xs" style={{ color: "#334155" }}>
        {data.geography_label} · ACS 5-Year
      </p>
    </div>
  );
}
