// Vitest setup: provide a functional localStorage for jsdom environments
// that may not implement the full Web Storage API.
if (typeof localStorage === "object" && typeof localStorage.clear !== "function") {
  let store: Record<string, string> = {};
  const impl: Storage = {
    get length() { return Object.keys(store).length; },
    key(i) { return Object.keys(store)[i] ?? null; },
    getItem(k) { return store[k] ?? null; },
    setItem(k, v) { store[k] = String(v); },
    removeItem(k) { delete store[k]; },
    clear() { store = {}; },
  };
  Object.defineProperty(window, "localStorage", { value: impl, writable: true });
}
