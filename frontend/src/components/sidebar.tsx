"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "◆" },
  { href: "/research/new", label: "New Research", icon: "+" },
  { href: "/history", label: "History", icon: "☰" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-950 flex flex-col">
      <div className="px-5 py-5">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-lg font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            ResearchForge
          </span>
          <span className="rounded bg-blue-600 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-white">
            AI
          </span>
        </Link>
      </div>

      <nav className="flex-1 px-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon }) => {
          const active = href === "/"
            ? pathname === "/"
            : pathname.startsWith(href);

          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                  : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
              }`}
            >
              <span className="text-base">{icon}</span>
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-200 px-5 py-4 dark:border-zinc-800">
        <p className="text-xs text-zinc-400">
          Research. Verify. Debate. Synthesize.
        </p>
      </div>
    </aside>
  );
}
