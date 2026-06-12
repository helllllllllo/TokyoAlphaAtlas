export function lerpColor(a: string, b: string, t: number): string {
  const pa = parseInt(a.replace(/^#/, ""), 16);
  const pb = parseInt(b.replace(/^#/, ""), 16);
  if (Number.isNaN(pa) || Number.isNaN(pb)) {
    if (import.meta.env.DEV) throw new Error(`lerpColor: malformed hex color (${a}, ${b})`);
    return a;
  }
  const ch = (sh: number) => {
    const va = (pa >> sh) & 0xff;
    const vb = (pb >> sh) & 0xff;
    return Math.round(va + (vb - va) * t);
  };
  const hex = (v: number) => v.toString(16).padStart(2, "0");
  return `#${hex(ch(16))}${hex(ch(8))}${hex(ch(0))}`;
}

/** Map t in [0,1] onto a multi-stop ramp. */
export function rampColor(stops: string[], t: number): string {
  const x = Math.min(Math.max(t, 0), 1) * (stops.length - 1);
  const i = Math.min(Math.floor(x), stops.length - 2);
  return lerpColor(stops[i], stops[i + 1], x - i);
}
