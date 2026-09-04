import CandleChart from "./CandleChart";
import type { Bar, Setup } from "@/lib/types";

const GRADE_COLOR: Record<string, string> = {
  A: "bg-up/15 text-up",
  B: "bg-accent/15 text-accent",
  C: "bg-yellow-500/15 text-yellow-400",
  F: "bg-down/15 text-down",
};

export default function TickerCard({ setup, bars }: { setup: Setup; bars: Bar[] }) {
  return (
    <div className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-3 flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <a
              href={`https://www.tradingview.com/chart/?symbol=${setup.ticker}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-lg font-semibold hover:text-blue-400 transition-colors"
            >
              {setup.ticker}
            </a>
            <span className="text-xs text-gray-500">{setup.anchor}</span>
            <span className="rounded bg-white/10 px-1.5 py-0.5 text-xs font-medium text-gray-300">
              {setup.timeframe.toUpperCase()}
            </span>
          </div>
          <div className="text-sm text-gray-400">${setup.price.toFixed(2)}</div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <span
            className={`rounded px-2 py-0.5 text-xs font-semibold ${GRADE_COLOR[setup.grade]}`}
          >
            {setup.grade} · {setup.align}
          </span>
          <span className="text-xs text-gray-500">retrace {setup.retrace.toFixed(1)}%</span>
        </div>
      </div>

      <CandleChart bars={bars} setup={setup} />

      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
        <Stat label="stop" value={setup.stop} />
        <Stat label="t1" value={setup.t1} />
        <Stat label="t2" value={setup.t2} />
        <Stat label="R:R" value={setup.rr_to_high} decimals={2} />
      </div>
    </div>
  );
}

function Stat({ label, value, decimals = 2 }: { label: string; value: number; decimals?: number }) {
  return (
    <div className="rounded bg-white/5 py-1.5">
      <div className="text-gray-500">{label}</div>
      <div className="font-medium text-gray-200">{value.toFixed(decimals)}</div>
    </div>
  );
}
