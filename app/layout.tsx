import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Golden Zone Dashboard",
  description: "Fibonacci pullback setups, scanned daily",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-bg text-white">{children}</body>
    </html>
  );
}
