import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { DATA_BASE, INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE } from "../config";
import { fetchDetail } from "../lib/data";
import { buildStationFeatures } from "../lib/mapData";
import { buildSimilarityLinks } from "../lib/mapInsights";
import { lensByKey } from "../lib/lenses";
import { useApp } from "../store";
import { Legend } from "../components/Legend";
import { LensTabs } from "../components/LensTabs";
import { StationCard } from "../components/StationCard";
import { TimeSlider } from "../components/TimeSlider";
import { MapPulse } from "../components/MapPulse";
import type { StationDetail } from "../types";

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
const EMPTY_LINES: GeoJSON.FeatureCollection<GeoJSON.LineString> = { type: "FeatureCollection", features: [] };

type OverlaySpec = {
  id: string;
  url: string;
  layer: Omit<maplibregl.LayerSpecification, "id" | "source">;
};

const RISK_OVERLAYS: OverlaySpec[] = [
  {
    id: "hazard-embankment",
    url: `${DATA_BASE}/hazard/embankment.geojson`,
    layer: {
      type: "fill",
      layout: { visibility: "none" },
      paint: { "fill-color": "#d8745f", "fill-opacity": 0.2 },
    },
  },
  {
    id: "hazard-danger-zone",
    url: `${DATA_BASE}/hazard/danger_zone.geojson`,
    layer: {
      type: "fill",
      layout: { visibility: "none" },
      paint: { "fill-color": "#c43f3f", "fill-opacity": 0.32 },
    },
  },
];

const REDEVELOPMENT_OVERLAYS: OverlaySpec[] = [
  {
    id: "redevelopment-district-plan",
    url: `${DATA_BASE}/redevelopment/district_plan.geojson`,
    layer: {
      type: "fill",
      layout: { visibility: "none" },
      paint: { "fill-color": "#4a8f8b", "fill-opacity": 0.2 },
    },
  },
  {
    id: "redevelopment-high-utilization",
    url: `${DATA_BASE}/redevelopment/high_utilization.geojson`,
    layer: {
      type: "fill",
      layout: { visibility: "none" },
      paint: { "fill-color": "#e06d4f", "fill-opacity": 0.24 },
    },
  },
  {
    id: "redevelopment-city-roads",
    url: `${DATA_BASE}/redevelopment/city_roads.geojson`,
    layer: {
      type: "line",
      layout: { visibility: "none", "line-cap": "round", "line-join": "round" },
      paint: { "line-color": "#f0c978", "line-width": 2.2, "line-opacity": 0.62 },
    },
  },
];

const RISK_OVERLAY_IDS = RISK_OVERLAYS.map(o => o.id);
const REDEVELOPMENT_OVERLAY_IDS = REDEVELOPMENT_OVERLAYS.map(o => o.id);
const ALL_THEMATIC_OVERLAY_IDS = [...RISK_OVERLAY_IDS, ...REDEVELOPMENT_OVERLAY_IDS];

async function ensureOptionalGeojson(
  map: maplibregl.Map,
  spec: OverlaySpec,
  before = "station-circles",
): Promise<void> {
  if (map.getLayer(spec.id)) return;
  try {
    const res = await fetch(spec.url);
    if (!res.ok || map.getLayer(spec.id)) return;
    const data = (await res.json()) as GeoJSON.FeatureCollection;
    if (!map.getSource(spec.id)) map.addSource(spec.id, { type: "geojson", data });
    if (!map.getLayer(spec.id)) {
      map.addLayer({ id: spec.id, source: spec.id, ...spec.layer } as maplibregl.LayerSpecification, before);
    }
  } catch { /* overlay is optional */ }
}

export function MapScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [selectedDetail, setSelectedDetail] = useState<StationDetail | null>(null);
  const { stations, quarters, lens, quarterIdx, select, selectedId } = useApp();

  // init once — StrictMode-safe: guard with mapRef.current check
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    let removed = false;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center: INITIAL_CENTER,
      zoom: INITIAL_ZOOM,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    const popup = new maplibregl.Popup({
      closeButton: false, closeOnClick: false, className: "station-tip", offset: 12,
    });

    map.on("load", () => {
      map.addSource("stations", { type: "geojson", data: EMPTY });
      map.addLayer({
        id: "station-glow", type: "circle", source: "stations",
        paint: {
          "circle-radius": ["get", "haloRadius"],
          "circle-color": ["get", "color"],
          "circle-opacity": ["get", "glowOpacity"],
          "circle-blur": 0.75,
        },
      });
      map.addLayer({
        id: "station-circles", type: "circle", source: "stations",
        paint: {
          "circle-radius": ["get", "radius"],
          "circle-color": ["get", "color"],
          "circle-color-transition": { duration: 300 },
          "circle-opacity": ["get", "opacity"],
          "circle-stroke-width": ["get", "strokeWidth"],
          "circle-stroke-color": ["get", "strokeColor"],
        },
      });
      map.addLayer({
        id: "station-volatility", type: "circle", source: "stations",
        paint: {
          "circle-radius": ["+", ["get", "radius"], 4],
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-width": ["get", "volatilityWidth"],
          "circle-stroke-color": "#f07c64",
          "circle-stroke-opacity": ["get", "volatilityOpacity"],
        },
      });
      map.addLayer({
        id: "station-selected", type: "circle", source: "stations",
        filter: ["==", ["get", "selected"], true],
        paint: {
          "circle-radius": ["+", ["get", "haloRadius"], 5],
          "circle-color": "rgba(0,0,0,0)",
          "circle-stroke-width": 2.5,
          "circle-stroke-color": "#f0c978",
          "circle-opacity": 0.95,
        },
      });
      map.addSource("similarity-links", { type: "geojson", data: EMPTY_LINES });
      map.addLayer({
        id: "similarity-link-glow", type: "line", source: "similarity-links",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["+", ["get", "width"], 3],
          "line-opacity": 0.12,
          "line-blur": 1.4,
        },
      }, "station-circles");
      map.addLayer({
        id: "similarity-links", type: "line", source: "similarity-links",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["get", "width"],
          "line-opacity": 0.62,
          "line-dasharray": [1.2, 1.4],
        },
      }, "station-circles");
      map.addLayer({
        id: "station-labels", type: "symbol", source: "stations", minzoom: 12.5,
        layout: {
          "text-field": ["get", "labelText"],
          "text-size": 11,
          "text-offset": [0, 1.6],
          "text-allow-overlap": false,
        },
        paint: {
          "text-color": "#cdd8f5",
          "text-halo-color": "#0a0f1e",
          "text-halo-width": 1.2,
        },
      });

      const addRail = async () => {
        try {
          const res = await fetch(`${DATA_BASE}/rail.geojson`);
          if (!res.ok || removed) return;
          const data = (await res.json()) as GeoJSON.FeatureCollection;
          if (removed) return; // map was torn down while fetching
          if (!map.getSource("rail")) map.addSource("rail", { type: "geojson", data });
          if (!map.getLayer("rail")) {
            map.addLayer({
              id: "rail",
              source: "rail",
              type: "line",
              paint: { "line-color": "#2e7d5b", "line-width": 1.2, "line-opacity": 0.35 },
            }, "station-circles");
          }
        } catch { /* overlay is optional */ }
      };

      void addRail();

      map.on("mousemove", "station-circles", e => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const p = f.properties as Record<string, string>;
        // Build the tooltip via DOM APIs (textContent only) — no innerHTML.
        const tip = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = p.name;
        tip.appendChild(name);
        tip.appendChild(document.createElement("br"));
        tip.appendChild(document.createTextNode(p.priceLabel));
        tip.appendChild(document.createElement("br"));
        const dim = document.createElement("span");
        dim.className = "tip-dim";
        dim.textContent = `${p.growthLabel}　${p.txLabel}`;
        tip.appendChild(dim);
        popup
          .setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number])
          .setDOMContent(tip)
          .addTo(map);
      });
      map.on("mouseleave", "station-circles", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
      map.on("click", "station-circles", e => {
        const f = e.features?.[0];
        if (f) select((f.properties as { id: string }).id);
      });
      setMapReady(true);
    });
    mapRef.current = map;
    return () => { removed = true; map.remove(); mapRef.current = null; };
  }, [select]);

  // push data on lens/quarter/data change
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !stations || !quarters) return;
    const fc = buildStationFeatures(stations.stations, quarters, lensByKey(lens), quarterIdx, selectedId);
    // Rebuilds ~1300 features per tick at 350ms play speed; fine for V8
    // young-gen GC, revisit if interval drops below ~100ms.
    (map.getSource("stations") as maplibregl.GeoJSONSource)?.setData(fc);
  }, [mapReady, stations, quarters, lens, quarterIdx, selectedId]);

  // load selected station detail for similarity constellation lines
  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null);
      return;
    }
    let cancelled = false;
    void fetchDetail(selectedId).then(detail => {
      if (!cancelled) setSelectedDetail(detail);
    });
    return () => { cancelled = true; };
  }, [selectedId]);

  // update similarity constellation
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady || !stations) return;
    const selected = selectedId ? stations.stations.find(station => station.id === selectedId) : null;
    const fc = selected
      ? buildSimilarityLinks(selected, selectedDetail, stations.stations)
      : EMPTY_LINES;
    (map.getSource("similarity-links") as maplibregl.GeoJSONSource)?.setData(fc);
  }, [mapReady, stations, selectedId, selectedDetail]);

  // fly to selection
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedId || !stations) return;
    const s = stations.stations.find(x => x.id === selectedId);
    if (s) map.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 12.5) });
  }, [selectedId, stations]);

  // toggle optional overlay visibility with thematic lenses
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    let cancelled = false;
    for (const id of ALL_THEMATIC_OVERLAY_IDS) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", "none");
    }
    const active = lens === "risk" ? RISK_OVERLAYS : lens === "redevelopment" ? REDEVELOPMENT_OVERLAYS : [];
    void (async () => {
      for (const spec of active) {
        await ensureOptionalGeojson(map, spec);
      }
      if (cancelled) return;
      for (const spec of active) {
        if (map.getLayer(spec.id)) map.setLayoutProperty(spec.id, "visibility", "visible");
      }
    })();
    return () => { cancelled = true; };
  }, [mapReady, lens]);

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-container" />
      <div className="map-atmosphere" />
      <LensTabs />
      <Legend />
      <MapPulse selectedDetail={selectedDetail} />
      <TimeSlider />
      <StationCard />
    </div>
  );
}
