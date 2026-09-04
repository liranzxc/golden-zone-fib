export type Anchor = "fixed" | "pine";
export type Grade = "A" | "B" | "C" | "F";

export interface Setup {
  id: number;
  ticker: string;
  anchor: Anchor;
  date: string;
  price: number;
  leg_low: number;
  leg_high: number;
  leg_pct: number;
  leg_atr: number;
  bars_off_high: number;
  retrace: number;
  deepest: number;
  lvl_382: number;
  lvl_500: number;
  lvl_618: number;
  lvl_786: number;
  grade: Grade;
  score: number;
  align: string; // e.g. "4/4"
  trend_ok: boolean;
  atr_pct: number;
  stop: number;
  stop_atr: number;
  t1: number;
  t2: number;
  qty: number;
  rr_to_high: number;
  pass: boolean;
}

export interface Bar {
  ticker: string;
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface Filters {
  anchor: Anchor | "both";
  align: string[]; // subset of ["4/4","3/4","2/4"]
  zoneLo: number;
  zoneHi: number;
}
