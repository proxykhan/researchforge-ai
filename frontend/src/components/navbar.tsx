"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/history", label: "History" },
];

export function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isAuthPage = pathname === "/login" || pathname === "/signup";

  return (
    <header className="border-b border-border bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-accent">
            <span className="text-sm font-bold text-white">R</span>
          </div>
          <span className="text-lg font-semibold tracking-tight text-foreground">
            ResearchForge
          </span>
        </Link>

        <nav className="flex items-center gap-4 sm:gap-8">
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
        </nav>
      </div>
    </header>
  );
}
