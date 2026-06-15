"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Compass, LogIn, LogOut, Search } from "lucide-react";
import { learnerSession, type StoredSession } from "@/shared/api/client";
import { Badge, Button, cn } from "@/shared/ui";
import { redirectToKeycloakLogout } from "./keycloak-auth";

const navLinks = [
  { href: "/", label: "Dashboard" },
  { href: "/search", label: "Tìm kiếm" },
  { href: "/learning-paths", label: "Lộ trình" },
  { href: "/deadlines", label: "Deadline" },
  { href: "/loyalty", label: "Ưu đãi" },
  { href: "/gradebook", label: "Bảng điểm" },
  { href: "/notifications", label: "Thông báo" },
  { href: "/certificates", label: "Chứng chỉ" }
];

function initials(name?: string, email?: string) {
  const source = (name?.trim() || email?.split("@")[0] || "U").trim();
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function LearnerHeader() {
  const pathname = usePathname();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [currentHref, setCurrentHref] = useState(pathname);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    setSession(learnerSession.read());
    setHydrated(true);
    return learnerSession.subscribe((nextSession) => {
      setSession(nextSession);
      setHydrated(true);
    });
  }, []);

  useEffect(() => {
    const updateCurrentHref = () => {
      setCurrentHref(`${window.location.pathname}${window.location.search}`);
    };
    const historyWithPatch = window.history as History & { __courseflowLocationPatched?: boolean };

    if (!historyWithPatch.__courseflowLocationPatched) {
      const pushState = historyWithPatch.pushState.bind(historyWithPatch);
      const replaceState = historyWithPatch.replaceState.bind(historyWithPatch);
      const notifyLocationChanged = () => window.dispatchEvent(new Event("courseflow.location.changed"));

      historyWithPatch.pushState = (...args) => {
        const result = pushState(...args);
        notifyLocationChanged();
        return result;
      };
      historyWithPatch.replaceState = (...args) => {
        const result = replaceState(...args);
        notifyLocationChanged();
        return result;
      };
      historyWithPatch.__courseflowLocationPatched = true;
    }

    updateCurrentHref();
    window.addEventListener("popstate", updateCurrentHref);
    window.addEventListener("courseflow.location.changed", updateCurrentHref);
    return () => {
      window.removeEventListener("popstate", updateCurrentHref);
      window.removeEventListener("courseflow.location.changed", updateCurrentHref);
    };
  }, [pathname]);

  const nextHref = useMemo(() => {
    if (pathname === "/login" || pathname === "/register") return "/";
    return currentHref || pathname;
  }, [currentHref, pathname]);

  async function handleLogout() {
    const current = learnerSession.read();
    setLoggingOut(true);
    learnerSession.clear();
    redirectToKeycloakLogout(current);
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/88 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-5 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-3 font-bold text-ink-900">
            <span className="grid size-10 place-items-center rounded-xl bg-brand-600 text-sm text-white shadow-[0_10px_25px_rgba(15,111,95,0.22)]">
              CF
            </span>
            <span className="min-w-0">
              <span className="block text-base">CourseFlow Learn</span>
              <span className="block text-xs font-medium text-ink-500">Learner workspace</span>
            </span>
          </Link>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/search"
              className="hidden h-10 min-w-64 items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-ink-500 transition hover:border-brand-200 hover:bg-brand-50/60 md:inline-flex"
            >
              <Search className="size-4" />
              Tìm khóa học, kỹ năng, nội dung
            </Link>

            {!hydrated ? (
              <span
                className="h-10 w-44 animate-pulse rounded-xl border border-slate-200 bg-slate-50"
                aria-label="Đang kiểm tra phiên đăng nhập"
              />
            ) : session ? (
              <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-2 py-1.5 text-ink-700 shadow-sm">
                {session.user.avatarUrl ? (
                  <img
                    src={session.user.avatarUrl}
                    alt=""
                    className="size-8 rounded-lg object-cover"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <span className="grid size-8 place-items-center rounded-lg bg-ink-900 text-xs font-bold text-white">
                    {initials(session.user.fullName, session.user.email)}
                  </span>
                )}
                <div className="hidden max-w-[180px] sm:block">
                  <p className="truncate text-sm font-semibold text-ink-900">
                    {session.user.fullName || session.user.email}
                  </p>
                  <p className="truncate text-xs text-ink-500">{session.user.email}</p>
                </div>
                <Button asChild variant="ghost" size="sm" className="h-8 w-8 px-0">
                  <Link href="/notifications" aria-label="Mở thông báo">
                    <Bell className="size-4" />
                  </Link>
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  disabled={loggingOut}
                  className="h-8 px-2"
                >
                  <LogOut className="size-4" />
                  <span className="hidden sm:inline">{loggingOut ? "Đang thoát" : "Đăng xuất"}</span>
                </Button>
              </div>
            ) : (
              <>
                <Button asChild variant="ghost" size="sm">
                  <Link href={`/login?next=${encodeURIComponent(nextHref)}`}>
                    <span className="inline-flex items-center gap-2">
                      <LogIn className="size-4" />
                      <span>Đăng nhập</span>
                    </span>
                  </Link>
                </Button>
                <Button asChild size="sm">
                  <Link href={`/login?next=${encodeURIComponent(nextHref)}`}>
                    <span className="inline-flex items-center gap-2">
                      <LogIn className="size-4" />
                      <span>IAM</span>
                    </span>
                  </Link>
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5 text-sm text-ink-500">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-lg px-3 py-2 font-medium transition hover:bg-brand-50 hover:text-brand-700",
                  pathname === link.href && "bg-brand-50 text-brand-700"
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>
          <div className="hidden items-center gap-2 lg:flex">
            <Badge tone="neutral">
              <Compass className="mr-1 size-3.5" />
              Catalog, learning path, player
            </Badge>
          </div>
        </div>
      </div>
    </nav>
  );
}
