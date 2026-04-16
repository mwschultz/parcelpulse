import { useState, useEffect, useRef } from "react";
import DemoPanel, { type DemographicsData } from "./DemoPanel";
import CompetitorsPanel, { type CompetitorData } from "./CompetitorsPanel";
import ParcelPanel, { type ParcelsData } from "./ParcelPanel";
import SpendingPanel, { type SpendingData } from "./SpendingPanel";

const TABS = ["Parcel", "Demographics", "Competitors", "Spending"] as const;
type Tab = (typeof TABS)[number];

const EXPANDED_RATIO = 0.6;

interface SidebarProps {
  hasResult: boolean;
  demographics: DemographicsData | null;
  loading: boolean;
  parcelsLoading: boolean;
  competitors: CompetitorData | null;
  visibleCategories: Set<string>;
  onToggleCategory: (key: string) => void;
  onRetryCompetitors: () => void;
  parcels: ParcelsData | null;
  spending: SpendingData | null;
  activeParcelId: string | null;
  selectedParcelId: string | null;
  onParcelHover: (parno: string | null) => void;
  onParcelSelect: (parno: string) => void;
}

export default function Sidebar({
  hasResult, demographics, loading, parcelsLoading, competitors, visibleCategories,
  onToggleCategory, onRetryCompetitors, parcels, spending, activeParcelId, selectedParcelId,
  onParcelHover, onParcelSelect,
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<Tab>("Parcel");
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [dragHeight, setDragHeight] = useState<number | null>(null);
  // collapsedH is measured from the actual rendered header so safe-area is included
  const [collapsedH, setCollapsedH] = useState(100);
  const headerRef = useRef<HTMLDivElement>(null);
  const dragHeightRef = useRef<number | null>(null);
  const dragStartY = useRef<number | null>(null);
  const dragStartH = useRef<number | null>(null);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // Measure true collapsed height (drag handle + tabs + safe-area spacer)
  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    setCollapsedH(el.offsetHeight);
    const ro = new ResizeObserver(() => setCollapsedH(el.offsetHeight));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (selectedParcelId) setActiveTab("Parcel");
  }, [selectedParcelId]);

  function handleTabClick(tab: Tab) {
    setActiveTab(tab);
    if (isMobile && !sheetOpen) setSheetOpen(true);
  }

  function handleDragStart(clientY: number) {
    dragStartY.current = clientY;
    dragStartH.current = dragHeightRef.current ?? (sheetOpen ? window.innerHeight * EXPANDED_RATIO : collapsedH);
  }

  function handleDragMove(clientY: number) {
    if (dragStartY.current === null || dragStartH.current === null) return;
    const delta = dragStartY.current - clientY;
    const newH = Math.min(
      Math.max(dragStartH.current + delta, collapsedH),
      window.innerHeight * 0.9,
    );
    dragHeightRef.current = newH;
    setDragHeight(newH);
  }

  function handleDragEnd() {
    const h = dragHeightRef.current ?? (sheetOpen ? window.innerHeight * EXPANDED_RATIO : collapsedH);
    setSheetOpen(h > collapsedH + 20);
    dragHeightRef.current = null;
    setDragHeight(null);
    dragStartY.current = null;
    dragStartH.current = null;
  }

  const mobileHeight = dragHeight ?? (sheetOpen ? window.innerHeight * EXPANDED_RATIO : collapsedH);

  return (
    <aside
      className="flex flex-col overflow-hidden fixed bottom-0 left-0 right-0 z-[500] md:relative md:bottom-auto md:left-auto md:right-auto md:z-auto md:h-full md:w-[480px] md:shrink-0 md:overflow-visible"
      style={{
        backgroundColor: "#1a1f36",
        borderTop: isMobile ? "1px solid #2e3a5c" : undefined,
        borderLeft: !isMobile ? "1px solid #2e3a5c" : undefined,
        height: isMobile ? mobileHeight : undefined,
        minHeight: isMobile ? collapsedH : undefined,
        transition: dragHeight === null ? "height 0.25s ease" : undefined,
      }}
    >
      {/* Header: drag handle + tabs + safe-area spacer — measured by ref */}
      <div ref={headerRef} className="shrink-0">
        {/* Drag handle — mobile only */}
        <div
          className="md:hidden flex justify-center py-3 touch-none cursor-grab active:cursor-grabbing"
          onTouchStart={(e) => handleDragStart(e.touches[0].clientY)}
          onTouchMove={(e) => handleDragMove(e.touches[0].clientY)}
          onTouchEnd={handleDragEnd}
        >
          <div className="h-1 w-10 rounded-full bg-gray-600" />
        </div>

        {/* Desktop header */}
        <div className="hidden md:block px-4 py-4" style={{ borderBottom: "1px solid #2e3a5c" }}>
          <h1 className="text-base font-bold text-white">ParcelPulse</h1>
        </div>

        {/* Tabs */}
        <div className="flex" style={{ borderBottom: "1px solid #2e3a5c" }}>
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => handleTabClick(tab)}
              className="flex-1 py-4 md:py-2 text-sm font-medium transition-colors"
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

        {/* Safe-area spacer — mobile only, pushes tab bar above home indicator */}
        <div className="md:hidden" style={{ height: "env(safe-area-inset-bottom)" }} />
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
                data={parcels}
                loading={parcelsLoading}
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
                data={competitors}
                loading={loading}
                failed={!loading && competitors === null}
                onRetry={onRetryCompetitors}
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

      {/* Footer — desktop only */}
      <div className="hidden md:block px-4 py-2" style={{ borderTop: "1px solid #2e3a5c" }}>
        <p className="text-xs" style={{ color: "#334155" }}>
          Powered by Census Bureau · OpenStreetMap · NC OneMap
        </p>
      </div>
    </aside>
  );
}
