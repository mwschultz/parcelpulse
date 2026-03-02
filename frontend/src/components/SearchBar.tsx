import { useState, useEffect, useRef, useCallback } from "react";

interface GeoapifyFeature {
  properties: {
    formatted: string;
    lat: number;
    lon: number;
    state: string;
    state_code: string;
    country_code: string;
  };
}

interface GeoapifyResponse {
  features: GeoapifyFeature[];
}

export interface SearchResult {
  address: string;
  lat: number;
  lng: number;
  state: string;
}

interface SearchBarProps {
  onSelect: (result: SearchResult) => void;
}

export default function SearchBar({ onSelect }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<GeoapifyFeature[]>([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const skipNextFetch = useRef(false);
  const apiKey = import.meta.env.VITE_GEOAPIFY_KEY as string;

  const fetchSuggestions = useCallback(
    async (text: string) => {
      if (!text || text.length < 3) {
        setSuggestions([]);
        setOpen(false);
        return;
      }
      try {
        const url = `https://api.geoapify.com/v1/geocode/autocomplete?text=${encodeURIComponent(text)}&apiKey=${apiKey}&limit=5&filter=countrycode:us`;
        const res = await fetch(url);
        const data: GeoapifyResponse = await res.json();
        setSuggestions(data.features ?? []);
        setOpen(true);
      } catch {
        setSuggestions([]);
      }
    },
    [apiKey],
  );

  useEffect(() => {
    if (skipNextFetch.current) {
      skipNextFetch.current = false;
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchSuggestions]);

  // Click-outside dismisses the dropdown
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setSuggestions([]);
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(feature: GeoapifyFeature) {
    const { formatted, lat, lon, state, state_code } = feature.properties;
    skipNextFetch.current = true;
    setQuery(formatted);
    setSuggestions([]);
    setOpen(false);
    onSelect({
      address: formatted,
      lat,
      lng: lon,
      state: state_code || state,
    });
  }

  return (
    <div ref={containerRef} className="absolute left-1/2 top-4 z-[1000] w-full max-w-md -translate-x-1/2 px-4">
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="Search an address..."
          className="w-full rounded-lg bg-white px-4 py-3 text-sm text-gray-900 shadow-lg focus:outline-none focus:ring-2"
          style={{ focusRingColor: "#0ea5e9" } as React.CSSProperties}
        />
        {open && suggestions.length > 0 && (
          <ul className="absolute mt-1 w-full rounded-lg bg-white shadow-lg">
            {suggestions.map((f, i) => (
              <li
                key={i}
                onClick={() => handleSelect(f)}
                className="cursor-pointer px-4 py-2 text-sm text-gray-800 hover:bg-gray-100 first:rounded-t-lg last:rounded-b-lg"
              >
                {f.properties.formatted}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
