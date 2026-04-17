import type { Metadata } from "next";
import { Sidebar } from "@/components/Sidebar";
import "./globals.css";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Zylo Admin",
  description: "Claims review & trigger management dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn("dark", "font-sans")}>
      <body className="min-h-screen antialiased" style={{ background: "var(--bg-base)", color: "var(--text-primary)" }}>
        {/* Deep background layers */}
        <div className="fixed inset-0 -z-20" style={{ background: "#000000" }} />
        {/* Very subtle grid */}
        <div
          className="fixed inset-0 -z-10 pointer-events-none"
          style={{
            backgroundImage:
              "linear-gradient(rgba(255,255,255,0.01) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.01) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            maskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
            WebkitMaskImage: "radial-gradient(ellipse 80% 60% at 50% 0%, black 40%, transparent 100%)",
          }}
        />

        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 min-w-0">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
