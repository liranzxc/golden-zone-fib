import { supabase } from "./supabase";
import type { Bar, Filters, Setup } from "./types";

/** Most recent scan date present in `setups`. */
export async function latestDate(): Promise<string | null> {
  const { data, error } = await supabase
    .from("setups")
    .select("date")
    .order("date", { ascending: false })
    .limit(1);
  if (error) throw error;
  return data?.[0]?.date ?? null;
}

/** Setups for the latest date, matching the sidebar filters. */
export async function fetchSetups(filters: Filters): Promise<Setup[]> {
  const date = await latestDate();
  if (!date) return [];

  let q = supabase.from("setups").select("*").eq("date", date).eq("pass", true);

  if (filters.anchor !== "both") q = q.eq("anchor", filters.anchor);
  if (filters.align.length) q = q.in("align", filters.align);
  q = q.gte("retrace", filters.zoneLo).lte("retrace", filters.zoneHi);

  const { data, error } = await q.order("score", { ascending: false }).order("ticker");
  if (error) throw error;
  return (data ?? []) as Setup[];
}

/** Trailing OHLCV bars for a set of tickers, oldest first per ticker. */
export async function fetchBars(tickers: string[]): Promise<Record<string, Bar[]>> {
  if (!tickers.length) return {};

  const PAGE = 1000;
  const all: Bar[] = [];
  let from = 0;

  while (true) {
    const { data, error } = await supabase
      .from("bars")
      .select("*")
      .in("ticker", tickers)
      .order("ticker")
      .order("date", { ascending: true })
      .range(from, from + PAGE - 1);
    if (error) throw error;
    const rows = (data ?? []) as Bar[];
    all.push(...rows);
    if (rows.length < PAGE) break;
    from += PAGE;
  }

  const byTicker: Record<string, Bar[]> = {};
  for (const row of all) {
    (byTicker[row.ticker] ??= []).push(row);
  }
  return byTicker;
}
