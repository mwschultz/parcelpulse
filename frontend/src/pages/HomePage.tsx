import { useState } from "react";
import Map from "../components/Map";
import SearchBar, { type SearchResult } from "../components/SearchBar";
import InfoOverlay from "../components/InfoOverlay";
import Sidebar from "../components/Sidebar";
import { type DemographicsData } from "../components/DemoPanel";
import { type CompetitorData } from "../components/CompetitorsPanel";
import { type ParcelsData } from "../components/ParcelPanel";
import { type SpendingData } from "../components/SpendingPanel";
import { get } from "../api/client";

export default function HomePage() {
  const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);
  const [searchPin, setSearchPin] = useState<[number, number] | null>(null);
  const [boundary, setBoundary] = useState<object | null>(null);
  const [demographics, setDemographics] = useState<DemographicsData | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorData | null>(null);
  const [visibleCategories, setVisibleCategories] = useState<Set<string>>(new Set());
  const [parcels, setParcels] = useState<ParcelsData | null>(null);
  const [spending, setSpending] = useState<SpendingData | null>(null);
  const [demoLoading, setDemoLoading] = useState(false);
  const [competitorsLoading, setCompetitorsLoading] = useState(false);
  const [spendingLoading, setSpendingLoading] = useState(false);
  const [parcelsLoading, setParcelsLoading] = useState(false);
  const [lastSearch, setLastSearch] = useState<SearchResult | null>(null);
  const [activeParcelId, setActiveParcelId] = useState<string | null>(null);
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);

  async function handleRetryCompetitors() {
    if (!lastSearch) return;
    setCompetitorsLoading(true);
    setCompetitors(null);
    setVisibleCategories(new Set());
    get<CompetitorData>(`/api/competitors?lat=${lastSearch.lat}&lng=${lastSearch.lng}`)
      .then((data) => {
        setCompetitors(data);
        setVisibleCategories(new Set(data.categories.map((c) => c.key)));
      })
      .catch(() => {})
      .finally(() => setCompetitorsLoading(false));
  }

  async function handleSearch(result: SearchResult) {
    setLastSearch(result);
    const pin: [number, number] = [result.lat, result.lng];
    setMapCenter(pin);
    setSearchPin(pin);
    setBoundary(null);
    setDemoLoading(true);
    setCompetitorsLoading(true);
    setParcelsLoading(true);
    setDemographics(null);
    setCompetitors(null);
    setVisibleCategories(new Set());
    setParcels(null);
    setSpending(null);
    setActiveParcelId(null);
    setSelectedParcelId(null);

    // Fire demographics, competitors, parcels in parallel — each updates its panel independently
    const demoPromise = get<DemographicsData>(`/api/demographics?lat=${result.lat}&lng=${result.lng}`)
      .then((data): DemographicsData | null => {
        setDemographics(data);
        setBoundary(data.boundary ?? null);
        return data;
      })
      .catch((): null => null)
      .finally(() => setDemoLoading(false));

    get<CompetitorData>(`/api/competitors?lat=${result.lat}&lng=${result.lng}`)
      .then((data) => {
        setCompetitors(data);
        setVisibleCategories(new Set(data.categories.map((c) => c.key)));
      })
      .catch(() => {})
      .finally(() => setCompetitorsLoading(false));

    get<ParcelsData>(`/api/parcels?lat=${result.lat}&lng=${result.lng}&state=${result.state}`)
      .then((data) => setParcels(data))
      .catch(() => {})
      .finally(() => setParcelsLoading(false));

    // Spending needs income + households from demographics, fires after demo resolves
    const demo = await demoPromise;
    if (demo) {
      setSpendingLoading(true);
      get<SpendingData>(`/api/spending?income=${demo.median_household_income}&households=${demo.households}`)
        .then((data) => setSpending(data))
        .catch(() => {})
        .finally(() => setSpendingLoading(false));
    }
  }

  function handleToggleCategory(key: string) {
    setVisibleCategories((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  return (
    <div className="flex h-[100dvh] flex-col overflow-hidden">
      <header className="flex shrink-0 items-center justify-between bg-[#1a1f36] px-4 py-2">
        <span className="text-sm font-bold tracking-wide text-[#0ea5e9]">ParcelPulse</span>
        <a
          href="https://mwschultz.com"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-gray-400 transition-colors hover:text-white"
        >
          Built by Matt Schultz · mwschultz.com
        </a>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="relative flex-1">
          <SearchBar onSelect={handleSearch} />
          <InfoOverlay onSearch={handleSearch} />
          {parcelsLoading && (
            <div className="absolute bottom-6 left-3 z-[1000] flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium pointer-events-none" style={{ backgroundColor: "#1a1f36", color: "#94a3b8", border: "1px solid #2e3a5c" }}>
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
              Loading parcels…
            </div>
          )}
          <Map
            center={mapCenter}
            boundary={boundary}
            searchPin={searchPin}
            competitorItems={competitors?.items ?? []}
            competitorCategories={competitors?.categories ?? []}
            visibleCategories={visibleCategories}
            parcelFeatures={
              parcels?.parcels
                ?.filter((p) => p.geometry)
                .map((p) => ({
                  type: "Feature",
                  geometry: p.geometry,
                  properties: {
                    parno: p.parno,
                    use_description: p.use_description,
                    address: p.address,
                    total_value: p.total_value,
                  },
                })) ?? []
            }
            activeParcelId={activeParcelId}
            selectedParcelId={selectedParcelId}
            onParcelClick={(parno) => setSelectedParcelId(parno)}
          />
        </div>
        <Sidebar
          hasResult={mapCenter !== null}
          demographics={demographics}
          demoLoading={demoLoading}
          competitorsLoading={competitorsLoading}
          spendingLoading={spendingLoading}
          parcelsLoading={parcelsLoading}
          competitors={competitors}
          visibleCategories={visibleCategories}
          onToggleCategory={handleToggleCategory}
          onRetryCompetitors={handleRetryCompetitors}
          parcels={parcels}
          spending={spending}
          activeParcelId={activeParcelId}
          selectedParcelId={selectedParcelId}
          onParcelHover={setActiveParcelId}
          onParcelSelect={setSelectedParcelId}
        />
      </div>

      <footer className="flex shrink-0 items-center justify-center bg-[#1a1f36] py-1.5">
        <span className="text-xs text-gray-500">
          © 2026{" "}
          <a
            href="https://mwschultz.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-400 transition-colors hover:text-white"
          >
            Matt Schultz
          </a>
        </span>
      </footer>
    </div>
  );
}
