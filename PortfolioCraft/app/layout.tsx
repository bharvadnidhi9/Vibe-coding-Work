import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "PortfolioCraft", description: "Build and preview a professional portfolio without code." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body className="bg-white text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100 antialiased">{children}</body></html>);
}
