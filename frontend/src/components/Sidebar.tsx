import { useState, useEffect } from "react";
import DemoPanel, { type DemographicsData } from "./DemoPanel";
import CompetitorsPanel, { type POIData } from "./CompetitorsPanel";
import ParcelPanel, { type PropertyData } from "./ParcelPanel";
import SpendingPanel, { type SpendingData } from "./SpendingPanel";

const TABS = ["Parcel", "Demographics", "Competitors", "Spending"] as const;
type Tab = (typeof TABS)[number];

interface SidebarProps {
  hasResult: boolean;
  demographics: DemographicsData | null;
  loading: boolean;
  poi: POIData | null;
  visibleCategories: Set<string>;
  onToggleCategory: (key: string) => void;
  property: PropertyData | null;
  spending: SpendingData | null;
  activeParcelId: string | null;
  selectedParcelId: string | null;
  onParcelHover: (parno: string | null) => void;
  onParcelSelect: (parno: string) => void;
}

export default function Sidebar({ hasResult, demographics, loading, poi, visibleCategories, onToggleCategory, property, spending, activeParcelId, selectedParcelId, onParcelHover, onParcelSelect }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<Tab>("Parcel");

  useEffect(() => {
    if (selectedParcelId) setActiveTab("Parcel");
  }, [selectedParcelId]);

  return (
    <aside
      className="flex h-full w-[480px] shrink-0 flex-col"
      style={{ backgroundColor: "#1a1f36", borderLeft: "1px solid #2e3a5c" }}
    >
      {/* Header */}
      <div className="px-4 py-4" style={{ borderBottom: "1px solid #2e3a5c" }}>
        <h1 className="text-base font-bold text-white">ParcelPulse</h1>
      </div>

      {/* Tabs */}
      <div className="flex" style={{ borderBottom: "1px solid #2e3a5c" }}>
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className="flex-1 py-2 text-sm font-medium transition-colors"
            style={{
              color: activeTab === tab ? "#0ea5e9" : "#64748b",
              borderBottom: activeTab === tab ? "2px solid #0ea5e9" : "2px solid transparent",
              backgroundColor: "transparent",
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {!hasResult ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-center text-sm" style={{ color: "#64748b" }}>
              Search an address to see data
            </p>
          </div>
        ) : (
          <div className="text-sm" style={{ color: "#94a3b8" }}>
            {activeTab === "Parcel" && (
              <ParcelPanel
                data={property}
                loading={loading}
                activeParcelId={activeParcelId}
                selectedParcelId={selectedParcelId}
                onHover={onParcelHover}
                onSelect={onParcelSelect}
              />
            )}
            {activeTab === "Demographics" && (
              <DemoPanel data={demographics} loading={loading} />
            )}
            {activeTab === "Competitors" && (
              <CompetitorsPanel
                data={poi}
                loading={loading}
                visibleCategories={visibleCategories}
                onToggle={onToggleCategory}
              />
            )}
            {activeTab === "Spending" && (
              <SpendingPanel data={spending} loading={loading} />
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2" style={{ borderTop: "1px solid #2e3a5c" }}>
        <p className="text-xs" style={{ color: "#334155" }}>
          Powered by Census Bureau · OpenStreetMap · NC OneMap
        </p>
      </div>
    </aside>
  );
}
