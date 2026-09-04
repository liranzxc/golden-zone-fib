"use client";

import { useEffect, useRef } from "react";
import type { IChartApi, ISeriesApi } from "lightweight-charts";
import type { Bar, Setup } from "@/lib/types";

interface Props {
  bars: Bar[];
  setup: Setup;
  height?: number;
}

const LEVEL_COLORS: Record<string, string> = {
  lvl_382: "#fbbf24",
  lvl_500: "#ffffff",
  lvl_618: "#fbbf24",
  lvl_786: "#ffffff",
};

export default function CandleChart({ bars, setup, height = 260 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || !bars.length) return;

    let disposed = false;
    let chart: IChartApi | null = null;

    const sortedBars = [...bars].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

    import("lightweight-charts").then(({ createChart, ColorType }) => {
      if (disposed || !containerRef.current) return;

      chart = createChart(containerRef.current, {
        width: containerRef.current.clientWidth,
        height,
        layout: {
          background: { type: ColorType.Solid, color: "transparent" },
          textColor: "#9ca3af",
          fontSize: 11,
        },
        grid: {
          vertLines: { color: "#1c2130" },
          horzLines: { color: "#1c2130" },
        },
        rightPriceScale: { borderColor: "#232838" },
        timeScale: { borderColor: "#232838", timeVisible: false, rightOffset: 20 },
        crosshair: { mode: 0 },
      });
      chartRef.current = chart;

      // Gold band between 38.2% and 61.8% fib levels
      const zoneBand = chart.addBaselineSeries({
        baseValue: { type: "price", price: setup.lvl_618 },
        topLineColor: "transparent",
        topFillColor1: "rgba(251,191,36,0.10)",
        topFillColor2: "rgba(251,191,36,0.10)",
        bottomLineColor: "transparent",
        bottomFillColor1: "transparent",
        bottomFillColor2: "transparent",
        lineWidth: 1,
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
      });
      zoneBand.setData(sortedBars.map((b) => ({ time: b.date, value: setup.lvl_382 })));

      const series: ISeriesApi<"Candlestick"> = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderVisible: false,
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
      });

      series.setData(
        sortedBars.map((b) => ({
          time: b.date,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }))
      );

      // Leg anchors (solid purple)
      series.createPriceLine({
        price: setup.leg_high,
        color: "#a855f7",
        lineStyle: 0,
        lineWidth: 1,
        title: "",
      });
      series.createPriceLine({
        price: setup.leg_low,
        color: "#a855f7",
        lineStyle: 0,
        lineWidth: 1,
        title: "",
      });

      // Fib levels — golden lines solid+thick, 78.6% dashed red
      (["lvl_382", "lvl_500", "lvl_618", "lvl_786"] as const).forEach((key) => {
        if (!setup[key]) return;
        series.createPriceLine({
          price: setup[key],
          color: LEVEL_COLORS[key],
          lineStyle: 0,
          lineWidth: 1,
          title: (parseInt(key.replace("lvl_", ""), 10) / 10) + "%",
        });
      });

      // Swing point markers
      const swingHighIdx = sortedBars.length - 1 - setup.bars_off_high;
      const swingHighBar = sortedBars[swingHighIdx];

      // Swing low: lowest bar after the swing high
      let swingLowIdx = swingHighIdx;
      for (let i = swingHighIdx + 1; i < sortedBars.length; i++) {
        if (sortedBars[i].low < sortedBars[swingLowIdx].low) swingLowIdx = i;
      }
      const swingLowBar = sortedBars[swingLowIdx];

      type Marker = {
        time: string;
        position: "aboveBar" | "belowBar";
        color: string;
        shape: "arrowDown" | "arrowUp";
        text: string;
      };
      const markers: Marker[] = [];
      if (swingHighBar) {
        markers.push({
          time: swingHighBar.date,
          position: "aboveBar",
          color: "#f87171",
          shape: "arrowDown",
          text: "",
        });
      }
      if (swingLowBar && swingLowBar.date !== swingHighBar?.date) {
        markers.push({
          time: swingLowBar.date,
          position: "belowBar",
          color: "#22c55e",
          shape: "arrowUp",
          text: "",
        });
      }
      markers.sort((a, b) => (a.time < b.time ? -1 : 1));
      series.setMarkers(markers);

      // Zoom to the setup leg: a few bars before the swing high through to the end
      chart.timeScale().setVisibleLogicalRange({
        from: Math.max(0, swingHighIdx - 10),
        to: sortedBars.length - 1 + 20,
      });
    });

    const onResize = () => {
      if (chartRef.current && containerRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", onResize);

    return () => {
      disposed = true;
      window.removeEventListener("resize", onResize);
      chartRef.current?.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bars, setup.ticker, setup.anchor]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
