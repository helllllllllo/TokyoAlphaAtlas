import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { DATA_BASE, INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE } from "../config";
import { buildStationFeatures } from "../lib/mapData";
import { lensByKey } from "../lib/lenses";
import { useApp } from "../store";
import { Legend } from "../components/Legend";
import { LensTabs } from "../components/LensTabs";
import { StationCard } from "../components/StationCard";
import { TimeSlider } from "../components/TimeSlider";

const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

export function MapScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [mapReady, setMapReady] = useState(false);
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
      // Optional overlay layers — sequential so before: "station-circles" always works
      const addOptionalGeojson = async (
        id: string,
        url: string,
        layer: Omit<maplibregl.LayerSpecification, "id" | "source">,
        before?: string,
      ) => {
        try {
          const res = await fetch(url);
          if (!res.ok || removed) return;
          const data = (await res.json()) as GeoJSON.FeatureCollection;
          if (removed) return; // map was torn down while fetching
          if (!map.getSource(id)) map.addSource(id, { type: "geojson", data });
          if (!map.getLayer(id)) {
            map.addLayer({ id, source: id, ...layer } as maplibregl.LayerSpecification, before);
          }
        } catch { /* overlay is optional */ }
      };

      void (async () => {
        await addOptionalGeojson("rail", `${DATA_BASE}/rail.geojson`, {
          type: "line",
          paint: { "line-color": "#2e7d5b", "line-width": 1.2, "line-opacity": 0.35 },
        }, "station-circles");
        await addOptionalGeojson("hazard-flood", `${DATA_BASE}/hazard/flood.geojson`, {
          type: "fill",
          layout: { visibility: "none" },
          paint: { "fill-color": "#3a7da0", "fill-opacity": 0.25 },
        }, "station-circles");
        await addOptionalGeojson("hazard-landslide", `${DATA_BASE}/hazard/landslide.geojson`, {
          type: "fill",
          layout: { visibility: "none" },
          paint: { "fill-color": "#a05f3a", "fill-opacity": 0.3 },
        }, "station-circles");
        if (removed) return;
        // sync visibility with the current lens — the toggle effect may have
        // already run before these layers existed
        const vis = useApp.getState().lens === "risk" ? "visible" : "none";
        for (const id of ["hazard-flood", "hazard-landslide"]) {
          if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis);
        }
      })();

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
    const fc = buildStationFeatures(stations.stations, quarters, lensByKey(lens), quarterIdx);
    // Rebuilds ~1300 features per tick at 350ms play speed; fine for V8
    // young-gen GC, revisit if interval drops below ~100ms.
    (map.getSource("stations") as maplibregl.GeoJSONSource)?.setData(fc);
  }, [mapReady, stations, quarters, lens, quarterIdx]);

  // fly to selection
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedId || !stations) return;
    const s = stations.stations.find(x => x.id === selectedId);
    if (s) map.flyTo({ center: [s.lon, s.lat], zoom: Math.max(map.getZoom(), 12.5) });
  }, [selectedId, stations]);

  // toggle hazard overlay visibility with リスク lens
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapReady) return;
    const vis = lens === "risk" ? "visible" : "none";
    for (const id of ["hazard-flood", "hazard-landslide"]) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", vis);
    }
  }, [mapReady, lens]);

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-container" />
      <LensTabs />
      <Legend />
      <TimeSlider />
      <StationCard />
    </div>
  );
}
