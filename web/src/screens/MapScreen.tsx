import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { INITIAL_CENTER, INITIAL_ZOOM, MAP_STYLE } from "../config";
import { buildStationFeatures } from "../lib/mapData";
import { lensByKey } from "../lib/lenses";
import { useApp } from "../store";
import { Legend } from "../components/Legend";
import { LensTabs } from "../components/LensTabs";
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
    return () => { map.remove(); mapRef.current = null; };
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

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-container" />
      <LensTabs />
      <Legend />
      <TimeSlider />
    </div>
  );
}
