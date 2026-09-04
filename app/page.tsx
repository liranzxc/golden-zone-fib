import NavBar from "@/components/NavBar";
import Sidebar from "@/components/Sidebar";
import TickerCard from "@/components/TickerCard";
import { fetchBars, fetchSetups } from "@/lib/data";
import type { Filters } from "@/lib/types";

export const revalidate = 300; // 5 min — cron writes once a day anyway

interface PageProps {
  searchParams: { [key: string]: string | string[] | undefined };
}

function parseFilters(sp: PageProps["searchParams"]): Filters {
  const timeframe = (sp.timeframe as string) ?? "both";
  const align = sp.align ? (Array.isArray(sp.align) ? sp.align : [sp.align]) : [];
  const zoneLo = sp.zoneLo ? Number(sp.zoneLo) : 0;
  const zoneHi = sp.zoneHi ? Number(sp.zoneHi) : 100;
  return { anchor: "both", timeframe, align, zoneLo, zoneHi };
}

export default async function DashboardPage({ searchParams }: PageProps) {
  const filters = parseFilters(searchParams);
  const setups = await fetchSetups(filters);
  const barsByKey = await fetchBars(setups.map((s) => s.ticker));

  return (
    <div className="flex min-h-screen flex-col">
      <NavBar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6">
          <h1 className="mb-4 text-xl font-semibold">
            Golden-zone setups
            <span className="ml-2 text-sm font-normal text-gray-500">
              {setups.length} matching
            </span>
          </h1>

          {setups.length === 0 ? (
            <p className="text-sm text-gray-500">
              No setups match these filters today.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {setups.map((s) => (
                <TickerCard
                  key={`${s.ticker}-${s.anchor}-${s.timeframe}`}
                  setup={s}
                  bars={barsByKey[`${s.ticker}:${s.timeframe}`] ?? []}
                />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
