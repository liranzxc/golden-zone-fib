"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
];

export default function NavBar() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-panel/90 px-4 md:px-6 backdrop-blur">
      <div className="flex items-center gap-8">
        <span className="text-sm font-semibold tracking-wide text-white">
          Golden&nbsp;Zone
        </span>
        <nav className="flex gap-5 text-sm">
          {LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={
                pathname === l.href
                  ? "text-white"
                  : "text-gray-400 hover:text-gray-200"
              }
            >
              {l.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
