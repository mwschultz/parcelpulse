import { useEffect, useRef } from "react";

export interface ParcelData {
  parno: string;
  address: string;
  city: string;
  owner: string;
  owner_type: string;
  land_value: number;
  improvement_value: number;
  total_value: number;
  use_description: string;
  acres: number;
  has_structure: boolean;
  year_built: number | null;
  sale_date: string | null;
  distance_mi: number | null;
  geometry: object | null;
}

export interface ParcelsData {
  coverage: boolean;
  state: string;
  message: string | null;
  parcels: ParcelData[];
  rate_limited: boolean;
  unavailable?: boolean;
}

interface ParcelPanelProps {
  data: ParcelsData | null;
  loading: boolean;
  activeParcelId: string | null;
  selectedParcelId: string | null;
  onHover: (parno: string | null) => void;
  onSelect: (parno: string) => void;
}

const fmtCurrency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function landUseColor(desc: string): string {
  const d = (desc ?? "").toLowerCase();
  if (d.includes("commercial")) return "#3b82f6";
  if (d.includes("residential") || d.includes("single") || d.includes("multi")) return "#64748b";
  if (d.includes("vacant") || d.includes("undeveloped")) return "#f59e0b";
  return "#94a3b8";
}

function Skeleton() {
  return (
    <div className="space-y-3">
      {[...Array(4)].map((_, i) => (
        <div
          key={i}
          className="h-16 animate-pulse rounded-lg"
          style={{ backgroundColor: "#0f1628" }}
        />
      ))}
    </div>
  );
}

function ParcelCard({
  parcel,
  isSelected,
  cardRef,
  onMouseEnter,
  onMouseLeave,
  onClick,
}: {
  parcel: ParcelData;
  isSelected: boolean;
  cardRef: (el: HTMLDivElement | null) => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  onClick: () => void;
}) {
  const color = landUseColor(parcel.use_description);
  const meta: string[] = [];
  if (parcel.distance_mi != null) meta.push(`${parcel.distance_mi.toFixed(2)} mi`);
  if (parcel.acres > 0) meta.push(`${parcel.acres.toFixed(2)} ac`);
  if (parcel.year_built) meta.push(`Built ${parcel.year_built}`);
  if (parcel.sale_date) meta.push(`Sold ${parcel.sale_date}`);

  return (
    <div
      ref={cardRef}
      className="rounded-lg p-4"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      onClick={onClick}
      style={{
        backgroundColor: "#0f1628",
        border: isSelected ? "1px solid #0ea5e9" : "1px solid #2e3a5c",
        cursor: "pointer",
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-semibold text-white">
            {parcel.address || parcel.parno || "Unknown Parcel"}
          </p>
          <span
            className="mt-1 inline-block rounded px-1.5 py-0.5 text-sm font-medium"
            style={{ backgroundColor: color + "22", color }}
          >
            {parcel.use_description || "Unknown Use"}
          </span>
        </div>
        {parcel.total_value > 0 && (
          <p className="shrink-0 text-base font-semibold" style={{ color: "#0ea5e9" }}>
            {fmtCurrency.format(parcel.total_value)}
          </p>
        )}
      </div>
      {parcel.owner && (
        <p className="mt-2 text-sm text-white">
          {parcel.owner}
          {parcel.owner_type ? ` (${parcel.owner_type})` : ""}
        </p>
      )}
      {meta.length > 0 && (
        <p className="mt-1 text-sm text-white">
          {meta.join(" · ")}
        </p>
      )}
    </div>
  );
}

export default function ParcelPanel({ data, loading, activeParcelId, selectedParcelId, onHover, onSelect }: ParcelPanelProps) {
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (selectedParcelId && cardRefs.current[selectedParcelId]) {
      cardRefs.current[selectedParcelId]!.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [selectedParcelId]);

  if (loading) return <Skeleton />;

  if (!data) return null;

  if (!data.coverage) {
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>
          Parcel Intelligence
        </p>
        <div
          className="rounded-lg p-3"
          style={{ backgroundColor: "#1c1408", border: "1px solid #78350f" }}
        >
          <p className="text-xs font-semibold" style={{ color: "#fbbf24" }}>
            ⚠ Parcel data is available for North Carolina addresses.
          </p>
          <p className="mt-1 text-xs" style={{ color: "#92400e" }}>
            Try: 4325 Glenwood Ave, Raleigh, NC
          </p>
        </div>
      </div>
    );
  }

  if (data.rate_limited) {
    return (
      <div
        className="rounded-lg p-3"
        style={{ backgroundColor: "#0f1628", border: "1px solid #2e3a5c" }}
      >
        <p className="text-xs" style={{ color: "#64748b" }}>
          Daily request limit reached — try again tomorrow.
        </p>
      </div>
    );
  }

  if (data.unavailable) {
    return (
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "#94a3b8" }}>
          Parcel Intelligence
        </p>
        <div
          className="rounded-lg p-3"
          style={{ backgroundColor: "#1c1408", border: "1px solid #78350f" }}
        >
          <p className="text-xs font-semibold" style={{ color: "#fbbf24" }}>
            ⚠ Parcel data is temporarily unavailable.
          </p>
          <p className="mt-1 text-xs" style={{ color: "#92400e" }}>
            NC OneMap is not responding — try again shortly.
          </p>
        </div>
      </div>
    );
  }

  if (data.parcels.length === 0) {
    return (
      <p className="text-sm" style={{ color: "#64748b" }}>
        No parcels found near this location.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold uppercase tracking-wide text-white">
        Parcel Intelligence
      </p>
      <div className="space-y-2">
        {data.parcels.map((parcel) => (
          <ParcelCard
            key={parcel.parno || parcel.address}
            parcel={parcel}
            isSelected={parcel.parno === selectedParcelId || parcel.parno === activeParcelId}
            cardRef={(el) => { cardRefs.current[parcel.parno] = el; }}
            onMouseEnter={() => onHover(parcel.parno)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onSelect(parcel.parno)}
          />
        ))}
      </div>
      <p className="text-xs" style={{ color: "#334155" }}>
        NC OneMap · County Assessor Data
      </p>
    </div>
  );
}
