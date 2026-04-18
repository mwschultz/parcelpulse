import { useEffect, useMemo, useRef } from "react";
import { MapContainer, TileLayer, GeoJSON, Marker, CircleMarker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { CompetitorItem, CompetitorCategory } from "./CompetitorsPanel";

// Fix Leaflet default marker icon broken by bundlers
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const BOUNDARY_STYLE = {
  color: "#0ea5e9",
  weight: 2,
  opacity: 0.8,
  fillColor: "#0ea5e9",
  fillOpacity: 0.12,
  interactive: false,
};

interface MapControllerProps {
  center: [number, number] | null;
}

function MapController({ center }: MapControllerProps) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.flyTo(center, 14, { duration: 1.2 });
    }
  }, [center, map]);
  return null;
}

const PARCEL_DEFAULT = { color: "#9ca3af", weight: 1.5, opacity: 0.9, fillColor: "#9ca3af", fillOpacity: 0.25 };
const PARCEL_ACTIVE  = { color: "#ffffff", weight: 2,   opacity: 1,   fillColor: "#0ea5e9", fillOpacity: 0.5  };

const parcelValueFmt = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

interface MapProps {
  center?: [number, number] | null;
  boundary?: object | null;
  searchPin?: [number, number] | null;
  competitorItems?: CompetitorItem[];
  competitorCategories?: CompetitorCategory[];
  visibleCategories?: Set<string>;
  parcelFeatures?: object[];
  activeParcelId?: string | null;
  selectedParcelId?: string | null;
  onParcelClick?: (parno: string) => void;
}

export default function Map({
  center = null,
  boundary = null,
  searchPin = null,
  competitorItems = [],
  competitorCategories = [],
  visibleCategories = new Set(),
  parcelFeatures = [],
  activeParcelId = null,
  selectedParcelId = null,
  onParcelClick,
}: MapProps) {
  const layerRefs = useRef<Record<string, L.Path>>({});
  const categoryColorMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const cat of competitorCategories) {
      map[cat.key] = cat.color;
    }
    return map;
  }, [competitorCategories]);

  useEffect(() => {
    Object.entries(layerRefs.current).forEach(([parno, layer]) => {
      const highlight = parno === activeParcelId || parno === selectedParcelId;
      layer.setStyle(highlight ? PARCEL_ACTIVE : PARCEL_DEFAULT);
    });
  }, [activeParcelId, selectedParcelId]);

  // Key boundary on its identity so GeoJSON layer re-mounts when it changes
  const boundaryKey = useMemo(
    () => (boundary ? JSON.stringify((boundary as { properties?: { GEOID?: string } }).properties?.GEOID ?? Math.random()) : "none"),
    [boundary]
  );

  return (
    <MapContainer
      center={[35.5, -79.0]}
      zoom={7}
      className="h-full w-full"
      zoomControl={true}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        subdomains="abcd"
        maxZoom={19}
      />
      <MapController center={center} />
      {boundary && (
        <GeoJSON
          key={boundaryKey}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          data={boundary as any}
          style={BOUNDARY_STYLE}
        />
      )}
      {parcelFeatures.length > 0 && (
        <GeoJSON
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          key={`${(parcelFeatures[0] as any)?.properties?.parno ?? ""}-${parcelFeatures.length}`}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          data={{ type: "FeatureCollection", features: parcelFeatures } as any}
          style={() => PARCEL_DEFAULT}
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          onEachFeature={(feature: any, layer: any) => {
            const p = feature.properties ?? {};
            const parno: string = p.parno ?? "";
            if (parno) layerRefs.current[parno] = layer as L.Path;
            layer.on("click", () => { if (parno) onParcelClick?.(parno); });
            const val = p.total_value > 0 ? parcelValueFmt.format(p.total_value) : "N/A";
            const container = L.DomUtil.create("div");
            const title = L.DomUtil.create("strong", "", container);
            title.textContent = p.address || "Parcel";
            container.appendChild(document.createElement("br"));
            container.appendChild(document.createTextNode(val));
            layer.bindPopup(container);
          }}
        />
      )}
      {searchPin && <Marker position={searchPin} />}
      {competitorItems
        .filter((item) => visibleCategories.has(item.category))
        .map((item, idx) => {
          const color = categoryColorMap[item.category] ?? "#94a3b8";
          return (
            <CircleMarker
              key={idx}
              center={[item.lat, item.lng]}
              radius={6}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.8, weight: 1 }}
            >
              <Popup>{item.name || item.category}</Popup>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
