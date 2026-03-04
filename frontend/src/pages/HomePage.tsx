import { useState } from "react";
import Map from "../components/Map";
import SearchBar, { type SearchResult } from "../components/SearchBar";
import InfoOverlay from "../components/InfoOverlay";
import Sidebar from "../components/Sidebar";
import { type DemographicsData } from "../components/DemoPanel";
import { type CompetitorData } from "../components/CompetitorsPanel";
import { type ParcelsData } from "../components/ParcelPanel";
import { type SpendingData } from "../components/SpendingPanel";
import { post } from "../api/client";

interface SearchResponse {
  address: string;
  lat: number;
  lng: number;
  state: string;
  demographics: DemographicsData | null;
  competitors: CompetitorData | null;
  parcels: ParcelsData | null;
  spending: SpendingData | null;
}

export default function HomePage() {
  const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);
  const [searchPin, setSearchPin] = useState<[number, number] | null>(null);
  const [boundary, setBoundary] = useState<object | null>(null);
  const [demographics, setDemographics] = useState<DemographicsData | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorData | null>(null);
  const [visibleCategories, setVisibleCategories] = useState<Set<string>>(new Set());
  const [parcels, setParcels] = useState<ParcelsData | null>(null);
  const [spending, setSpending] = useState<SpendingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeParcelId, setActiveParcelId] = useState<string | null>(null);
  const [selectedParcelId, setSelectedParcelId] = useState<string | null>(null);

  async function handleSearch(result: SearchResult) {
    const pin: [number, number] = [result.lat, result.lng];
    setMapCenter(pin);
    setSearchPin(pin);
    setBoundary(null);
    setLoading(true);
    setDemographics(null);
    setCompetitors(null);
    setVisibleCategories(new Set());
    setParcels(null);
    setSpending(null);
    setActiveParcelId(null);
    setSelectedParcelId(null);

    try {
      const data = await post<SearchResponse>("/api/search", {
        address: result.address,
        lat: result.lat,
        lng: result.lng,
        state: result.state,
      });
      setDemographics(data.demographics);
      setBoundary(data.demographics?.boundary ?? null);
      setCompetitors(data.competitors);
      if (data.competitors) {
        setVisibleCategories(new Set(data.competitors.categories.map((c) => c.key)));
      }
      setParcels(data.parcels);
      setSpending(data.spending);
    } catch {
      // data stays null
    } finally {
      setLoading(false);
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
    <div className="flex h-screen overflow-hidden">
      <div className="relative flex-1">
        <SearchBar onSelect={handleSearch} />
        <InfoOverlay onSearch={handleSearch} />
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
        loading={loading}
        competitors={competitors}
        visibleCategories={visibleCategories}
        onToggleCategory={handleToggleCategory}
        parcels={parcels}
        spending={spending}
        activeParcelId={activeParcelId}
        selectedParcelId={selectedParcelId}
        onParcelHover={setActiveParcelId}
        onParcelSelect={setSelectedParcelId}
      />
    </div>
  );
}
