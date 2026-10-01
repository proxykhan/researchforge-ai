"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import type { Theme } from "@/lib/theme";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/history", label: "History" },
];

const THEME_CYCLE: Record<Theme, Theme> = {
  system: "light",
  light: "dark",
  dark: "system",
};

const THEME_LABELS: Record<Theme, string> = {
  system: "System",
  light: "Light",
  dark: "Dark",
};

export function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const isAuthPage = pathname === "/login" || pathname === "/signup";

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent">
            <span className="text-sm font-bold text-white">R</span>
          </div>
          <span className="text-lg font-semibold tracking-tight text-foreground">
            ResearchForge
          </span>
        </Link>

        <nav className="flex items-center gap-4 sm:gap-6">
          {user && !isAuthPage && (
            <>
              {NAV_LINKS.map(({ href, label }) => {
                const active =
                  href === "/" ? pathname === "/" : pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`hidden text-sm font-medium transition-colors sm:block ${
                      active
                        ? "text-accent"
                        : "text-muted hover:text-foreground"
                    }`}
                  >
                    {label}
                  </Link>
                );
              })}
              <Link
                href="/research/new"
                className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover sm:px-5"
              >
                New Research
              </Link>
              <div className="hidden items-center gap-3 sm:flex">
                <span className="text-sm text-muted">{user.name}</span>
                <button
                  onClick={logout}
                  className="text-sm font-medium text-muted transition-colors hover:text-foreground"
                >
                  Sign Out
                </button>
              </div>
            </>
          )}

          {!user && !isAuthPage && (
            <>
              <Link
                href="/login"
                className="text-sm font-medium text-muted transition-colors hover:text-foreground"
              >
                Sign In
              </Link>
              <Link
                href="/signup"
                className="rounded-full bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover sm:px-5"
              >
                Sign Up
              </Link>
            </>
          )}

          <button
            onClick={() => setTheme(THEME_CYCLE[theme])}
            className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-foreground"
            title={`Theme: ${THEME_LABELS[theme]}`}
            aria-label={`Switch theme (current: ${THEME_LABELS[theme]})`}
          >
            {theme === "light" && <SunIcon />}
            {theme === "dark" && <MoonIcon />}
            {theme === "system" && <MonitorIcon />}
          </button>
        </nav>
      </div>
    </header>
  );
}

function SunIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

function MonitorIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  );
}
