"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

const ALIGN_OPTIONS = ["4/4", "3/4", "2/4"];
const ZONE_PRESETS: { label: string; lo: number; hi: number }[] = [
  { label: "All",        lo: 0,    hi: 100 },
  { label: "38.2 – 50",  lo: 38.2, hi: 50 },
  { label: "50 – 61.8",  lo: 50,   hi: 61.8 },
  { label: "61.8 – 78.6", lo: 61.8, hi: 78.6 },
];
const TIMEFRAMES = [
  { label: "Both", value: "both" },
  { label: "1D",   value: "1d" },
  { label: "4H",   value: "4h" },
  { label: "1H",   value: "1h" },
];

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const timeframe = params.get("timeframe") ?? "both";
  const align = params.getAll("align");
  const zoneLo = Number(params.get("zoneLo") ?? 0);
  const zoneHi = Number(params.get("zoneHi") ?? 100);

  function update(next: Record<string, string | string[] | null>) {
    const q = new URLSearchParams(params.toString());
    for (const [key, val] of Object.entries(next)) {
      q.delete(key);
      if (val === null) continue;
      if (Array.isArray(val)) val.forEach((v) => q.append(key, v));
      else q.set(key, val);
    }
    router.push(`${pathname}?${q.toString()}`);
  }

  function toggleAlign(a: string) {
    const has = align.includes(a);
    const next = has ? align.filter((x) => x !== a) : [...align, a];
    update({ align: next.length ? next : null });
  }

  return (
    <aside className="w-64 shrink-0 border-r border-border bg-panel px-4 py-6">
      <div className="mb-6">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Timeframe
        </h3>
        <div className="flex flex-col gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => update({ timeframe: tf.value === "both" ? null : tf.value })}
              className={`rounded px-3 py-1.5 text-left text-sm ${
                timeframe === tf.value
                  ? "bg-accent/20 text-accent"
                  : "text-gray-300 hover:bg-white/5"
              }`}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Grade
        </h3>
        <div className="flex flex-col gap-1">
          {ALIGN_OPTIONS.map((a) => (
            <label
              key={a}
              className="flex cursor-pointer items-center gap-2 rounded px-3 py-1.5 text-sm text-gray-300 hover:bg-white/5"
            >
              <input
                type="checkbox"
                checked={align.includes(a)}
                onChange={() => toggleAlign(a)}
                className="accent-blue-500"
              />
              {a}
            </label>
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Retracement zone
        </h3>
        <div className="flex flex-col gap-1">
          {ZONE_PRESETS.map((p) => (
            <button
              key={p.label}
              onClick={() =>
                update({
                  zoneLo: p.lo === 0 ? null : String(p.lo),
                  zoneHi: p.hi === 100 ? null : String(p.hi),
                })
              }
              className={`rounded px-3 py-1.5 text-left text-sm ${
                zoneLo === p.lo && zoneHi === p.hi
                  ? "bg-accent/20 text-accent"
                  : "text-gray-300 hover:bg-white/5"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
