import { Metadata } from "next";
import Link from "next/link";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Scientific | MYCA",
  description: "MYCA Autonomous Scientific Architecture",
};

const scientificNav = [
  { href: "/scientific", label: "Overview" },
  { href: "/scientific/lab", label: "Laboratory" },
  { href: "/scientific/simulation", label: "Simulations" },
  { href: "/scientific/experiments", label: "Experiments" },
  { href: "/scientific/bio", label: "Bio Interfaces" },
  { href: "/scientific/devices", label: "Devices" },
  { href: "/scientific/memory", label: "Memory" },
];

export default function ScientificLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r bg-muted/40 p-4 hidden lg:block">
        <div className="mb-6">
          <h2 className="text-lg font-semibold">Scientific</h2>
          <p className="text-sm text-muted-foreground">MYCA Research Platform</p>
        </div>
        <nav className="space-y-1">
          {scientificNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-8 p-3 border rounded-lg bg-background">
          <h3 className="text-sm font-medium mb-2">Quick Stats</h3>
          <div className="space-y-1 text-xs text-muted-foreground">
            <p>Active Experiments: 3</p>
            <p>Running Simulations: 2</p>
            <p>Connected Devices: 21</p>
            <p>FCI Sessions: 2</p>
          </div>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
