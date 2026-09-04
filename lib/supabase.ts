import { createClient } from "@supabase/supabase-js";

// Publishable key only — RLS on `setups` / `bars` grants SELECT and nothing
// else. This client is only ever imported from server components (see
// lib/data.ts), so the plain (non NEXT_PUBLIC_) env vars are fine here —
// if you later add a "use client" component that queries Supabase directly,
// mirror these two into NEXT_PUBLIC_-prefixed vars first, or the browser
// bundle won't have them.
export const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_PUBLISHABLE_KEY!,
  { auth: { persistSession: false } }
);
