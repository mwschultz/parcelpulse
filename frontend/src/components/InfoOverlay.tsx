import { useState, useEffect } from "react";
import { API_URL } from "../api/client";
import type { SearchResult } from "./SearchBar";

const DEMO_ADDRESS = "4325 Glenwood Ave, Raleigh, NC";
const DISMISSED_KEY = "parcelpulse-info-dismissed";

interface InfoOverlayProps {
  onSearch: (result: SearchResult) => void;
}

export default function InfoOverlay({ onSearch }: InfoOverlayProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(DISMISSED_KEY)) {
      setOpen(true);
    }
  }, []);

  function dismiss() {
    setOpen(false);
    localStorage.setItem(DISMISSED_KEY, "1");
  }

  async function handleDemoSearch() {
    dismiss();
    try {
      const res = await fetch(`${API_URL}/api/geocode?text=${encodeURIComponent(DEMO_ADDRESS)}`);
      const data = await res.json();
      const feature = data.features?.[0];
      if (feature) {
        const { formatted, lat, lon, state_code, state } = feature.properties;
        onSearch({ address: formatted, lat, lng: lon, state: state_code || state });
      }
    } catch {
      // ignore
    }
  }

  return (
    <>
      {/* Info icon button — top-right of map, below zoom controls */}
      <button
        onClick={() => setOpen(true)}
        className="absolute right-2.5 top-[90px] z-[1000] flex h-8 w-8 items-center justify-center rounded-full bg-white text-[#0ea5e9] shadow-md transition-colors hover:bg-[#0ea5e9] hover:text-white"
        aria-label="About ParcelPulse"
      >
        <span className="text-base leading-none">ⓘ</span>
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="absolute inset-0 z-[1001] flex items-center justify-center"
          onClick={(e) => {
            if (e.target === e.currentTarget) dismiss();
          }}
        >
          <div
            className="relative mx-4 w-full max-w-[480px] rounded-xl p-6 text-white shadow-2xl"
            style={{ backgroundColor: "rgba(26, 31, 54, 0.92)" }}
          >
            {/* X button */}
            <button
              onClick={dismiss}
              className="absolute right-4 top-4 text-gray-400 transition-colors hover:text-white"
              aria-label="Close"
            >
              ✕
            </button>

            <h2 className="mb-0.5 font-bold text-lg text-[#0ea5e9]">ParcelPulse</h2>
            <p className="mb-4 text-sm text-gray-400">Commercial Real Estate Intelligence</p>

            <p className="mb-4 text-sm leading-relaxed text-gray-200">
              Enter any US address to instantly analyze a location's commercial potential.
              ParcelPulse aggregates public data sources to deliver:
            </p>

            <ul className="mb-4 space-y-2 text-sm text-gray-200">
              <li>
                <span className="text-[#0ea5e9]">•</span>{" "}
                <strong className="text-white">Parcel data</strong> — ownership, valuations, land use, and boundaries (NC)
              </li>
              <li>
                <span className="text-[#0ea5e9]">•</span>{" "}
                <strong className="text-white">Demographics</strong> — population, income, education, and housing
              </li>
              <li>
                <span className="text-[#0ea5e9]">•</span>{" "}
                <strong className="text-white">Competitors</strong> — nearby businesses by category with density scoring
              </li>
              <li>
                <span className="text-[#0ea5e9]">•</span>{" "}
                <strong className="text-white">Spending</strong> — estimated consumer spending potential by category
              </li>
            </ul>

            <p className="mb-4 text-xs text-gray-500">
              Data sources: NC OneMap Parcels, US Census Bureau, OpenStreetMap, BLS Consumer Expenditure Survey.
            </p>

            <p className="text-sm text-gray-300">
              <button
                onClick={handleDemoSearch}
                className="text-[#0ea5e9] underline underline-offset-2 transition-colors hover:text-white"
              >
                Try: {DEMO_ADDRESS}
              </button>
            </p>
          </div>
        </div>
      )}
    </>
  );
}
