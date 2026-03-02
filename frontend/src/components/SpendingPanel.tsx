import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

export interface SpendingCategory {
  key: string;
  label: string;
  per_unit: number;
  total: number;
}

export interface SpendingData {
  bracket: string;
  bracket_label: string;
  households: number;
  categories: SpendingCategory[];
  is_estimated: boolean;
}

interface SpendingPanelProps {
  data: SpendingData | null;
  loading: boolean;
}

const AMBER = "#f59e0b";
const fmt = new Intl.NumberFormat("en-US");
const fmtCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function formatAbbrev(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${Math.round(value / 1_000)}K`;
  return `$${value}`;
}

function Skeleton() {
  return (
    <div className="space-y-3">
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className="h-12 animate-pulse rounded-lg"
          style={{ backgroundColor: "#0f1628" }}
        />
      ))}
    </div>
  );
}

export default function SpendingPanel({ data, loading }: SpendingPanelProps) {
  if (loading) return <Skeleton />;
  if (!data) return null;

  const labels = data.categories.map((c) => c.label);
  const totals = data.categories.map((c) => c.total);
  const perUnits = data.categories.map((c) => c.per_unit);

  const chartData = {
    labels,
    datasets: [
      {
        data: totals,
        backgroundColor: AMBER,
        borderRadius: 4,
      },
    ],
  };

  const chartOptions = {
    indexAxis: "y" as const,
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: { dataIndex: number }) => {
            const total = totals[ctx.dataIndex];
            const perUnit = perUnits[ctx.dataIndex];
            return [
              ` Total: ${fmtCurrency.format(total)}`,
              ` ${fmtCurrency.format(perUnit)} / household`,
            ];
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: "#94a3b8",
          font: { size: 12 },
          callback: (v: number | string) => formatAbbrev(Number(v)),
        },
        grid: { color: "#2e3a5c" },
      },
      y: {
        ticks: { color: "#94a3b8", font: { size: 12 } },
        grid: { color: "#2e3a5c" },
      },
    },
  } as const;

  return (
    <div className="space-y-4">
      {/* Fallback banner */}
      {data.is_estimated && (
        <div
          className="rounded-lg px-3 py-2 text-sm text-white"
          style={{ backgroundColor: "#0f1628", border: "1px solid #2e3a5c" }}
        >
          Income data unavailable — estimates based on national median ($75,000)
        </div>
      )}

      {/* Header card */}
      <div
        className="rounded-lg p-3"
        style={{ backgroundColor: "#0f1628", border: "1px solid #2e3a5c" }}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-white">
              Income Bracket
            </p>
            <p className="mt-1 text-sm font-semibold text-white">
              {data.bracket_label}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-white">
              Households
            </p>
            <p className="mt-1 text-sm font-semibold text-white">
              {fmt.format(data.households)}
            </p>
          </div>
        </div>
      </div>

      {/* Horizontal bar chart */}
      <div>
        <p className="mb-2 text-sm font-medium text-white">
          Annual Spending by Category (Trade Area Total)
        </p>
        <div style={{ height: data.categories.length * 36 + 16 }}>
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          <Bar data={chartData as any} options={chartOptions as any} />
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-xs" style={{ color: "#334155" }}>
        Modeled Estimate · BLS Consumer Expenditure Survey 2023 · Census ACS
      </p>
    </div>
  );
}
