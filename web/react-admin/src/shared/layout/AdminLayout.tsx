import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { ChevronRight, GraduationCap, LogOut, ShieldCheck } from "lucide-react";
import { groupedModuleRegistry, moduleGroups, moduleRegistry } from "@/shared/module-registry";
import { useAuth } from "@/shared/auth/auth-context";
import { cn } from "@/shared/ui/cn";

function initials(name?: string, email?: string) {
  const source = (name?.trim() || email?.split("@")[0] || "U").trim();
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export function AdminLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const activePath = location.pathname.split("/").filter(Boolean)[0] ?? "dashboard";
  const activeModule = moduleRegistry.find((module) => module.path === activePath) ?? moduleRegistry[0];
  const activeGroup = moduleGroups.find((group) => group.id === activeModule.group) ?? moduleGroups[0];
  const roleLabel = user?.role || "UNRESOLVED";
  const ActiveIcon = activeModule.icon;

  return (
    <div className="grid min-h-screen grid-cols-[304px_minmax(0,1fr)] bg-surface-canvas text-slate-800 max-lg:grid-cols-[272px_minmax(0,1fr)] max-md:grid-cols-1">
      <aside className="sticky top-0 flex h-screen flex-col border-r border-black/10 bg-brand-900 text-white max-md:hidden">
        <div className="border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-md bg-white/12">
              <GraduationCap size={22} />
            </span>
            <div>
              <p className="text-lg font-bold">CourseFlow LMS</p>
              <p className="text-xs text-white/55">Trung tâm vận hành học tập</p>
            </div>
          </div>
          <div className="mt-5 rounded-md border border-white/10 bg-white/[0.06] p-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-white/45">
              <ShieldCheck size={14} />
              Admin console
            </div>
            <p className="mt-2 text-sm font-semibold text-white">{activeGroup.label}</p>
            <p className="mt-1 text-xs leading-5 text-white/55">{activeGroup.description}</p>
          </div>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-5">
          {groupedModuleRegistry.map((group) => (
            <section key={group.id} className="space-y-1.5">
              <div className="flex items-center justify-between px-2">
                <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-white/38">{group.label}</p>
                <span className="rounded-full bg-white/8 px-2 py-0.5 text-[11px] font-semibold text-white/42">
                  {group.modules.length}
                </span>
              </div>
              <div className="space-y-0.5">
                {group.modules.map((module) => (
                  <NavLink
                    key={module.path}
                    to={module.path}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition",
                        isActive
                          ? "bg-white text-brand-900 shadow-[0_14px_32px_rgba(0,0,0,0.22)]"
                          : "text-white/68 hover:bg-white/10 hover:text-white"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <span
                          className={cn(
                            "grid size-8 shrink-0 place-items-center rounded-md transition",
                            isActive ? "bg-brand-100 text-brand-700" : "bg-white/8 text-white/62 group-hover:bg-white/12"
                          )}
                        >
                          <module.icon size={17} />
                        </span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold">{module.label}</span>
                          <span
                            className={cn(
                              "block truncate text-xs",
                              isActive ? "text-brand-900/70" : "text-white/38 group-hover:text-white/55"
                            )}
                          >
                            {module.description}
                          </span>
                        </span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </section>
          ))}
        </nav>
      </aside>

      <div className="flex min-h-screen min-w-0 flex-col">
        <header className="sticky top-0 z-30 border-b border-black/10 bg-white/88 px-5 py-3 backdrop-blur md:px-7">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-md border border-brand-100 bg-brand-50 text-brand-700">
                <ActiveIcon size={20} />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold text-slate-400">
                  <span>Không gian quản trị</span>
                  <ChevronRight size={14} />
                  <span>{activeGroup.label}</span>
                </div>
                <h1 className="truncate text-lg font-bold text-slate-950">{activeModule.label}</h1>
                <p className="truncate text-xs text-slate-500">{activeModule.description}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={activeModule.path}
                onChange={(event) => navigate(`/${event.target.value}`)}
                className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none focus:border-brand-500 focus:ring-4 focus:ring-brand-100 md:hidden"
                aria-label="Chọn khu vực quản trị"
              >
                {groupedModuleRegistry.map((group) => (
                  <optgroup key={group.id} label={group.label}>
                    {group.modules.map((module) => (
                      <option key={module.path} value={module.path}>
                        {module.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              {user && (
                <div className="hidden items-center gap-2 sm:flex">
                  {user.avatarUrl ? (
                    <img
                      src={user.avatarUrl}
                      alt=""
                      className="size-9 rounded-md object-cover"
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <span className="grid size-9 place-items-center rounded-md bg-brand-900 text-xs font-bold text-white">
                      {initials(user.fullName, user.email)}
                    </span>
                  )}
                  <div className="text-right">
                    <p className="text-sm font-semibold text-slate-800">{user.fullName}</p>
                    <p className="text-xs text-slate-400">
                      {roleLabel} · {user.email}
                    </p>
                  </div>
                </div>
              )}
              <button
                onClick={logout}
                className="inline-flex h-10 items-center gap-1.5 rounded-md border border-black/10 bg-white px-3 text-sm font-semibold text-slate-600 shadow-sm transition hover:bg-brand-50 hover:text-brand-700"
              >
                <LogOut size={16} />
                Đăng xuất
              </button>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-5 py-6 md:px-7">
          <div className="mx-auto w-full max-w-[1500px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
