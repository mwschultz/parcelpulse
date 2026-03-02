export interface POIItem {
  lat: number;
  lng: number;
  name: string;
  category: string;
}

export interface POICategory {
  key: string;
  label: string;
  color: string;
  count: number;
}

export interface POIData {
  items: POIItem[];
  categories: POICategory[];
  density_score: string;
  radius_m: number;
}

interface CompetitorsPanelProps {
  data: POIData | null;
  loading: boolean;
  visibleCategories: Set<string>;
  onToggle: (key: string) => void;
}

function DensityBadge({ score }: { score: string }) {
  const styles: Record<string, { bg: string; text: string }> = {
    High:   { bg: "#14532d", text: "#4ade80" },
    Medium: { bg: "#78350f", text: "#fcd34d" },
    Low:    { bg: "#1e293b", text: "#94a3b8" },
  };
  const s = styles[score] ?? styles.Low;
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      ● {score} Density
    </span>
  );
}

export default function CompetitorsPanel({ data, loading, visibleCategories, onToggle }: CompetitorsPanelProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="h-8 animate-pulse rounded"
            style={{ backgroundColor: "#2e3a5c" }}
          />
        ))}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-3">
      {/* Panel header */}
      <p className="text-sm font-semibold uppercase tracking-wide text-white">
        Competitive Landscape
      </p>

      {/* Density badge */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-white">
          Retail Density
        </span>
        <DensityBadge score={data.density_score} />
      </div>

      {/* Category rows */}
      <div className="space-y-1">
        {data.categories.map((cat) => {
          const visible = visibleCategories.has(cat.key);
          return (
            <button
              key={cat.key}
              onClick={() => onToggle(cat.key)}
              className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left transition-opacity"
              style={{
                backgroundColor: "transparent",
                opacity: visible ? 1 : 0.4,
              }}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: cat.color }}
              />
              <span className="flex-1 text-sm text-white">
                {cat.label}
              </span>
              <span className="text-sm font-semibold text-white">
                {cat.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <p className="pt-1 text-xs" style={{ color: "#475569" }}>
        Within 1 mi · OpenStreetMap
      </p>
    </div>
  );
}
