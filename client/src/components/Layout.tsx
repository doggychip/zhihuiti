import { Link, useLocation } from "wouter";
import {
  Brain, LayoutDashboard, Bot, Lightbulb, Package, BarChart3, Settings,
  ChevronLeft, ChevronRight, Sun, Moon, Menu, Atom, Zap,
} from "lucide-react";
import { useState, useEffect } from "react";
import { useTheme } from "@/App";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/agents", label: "Agents", icon: Bot },
  { path: "/strategies", label: "Strategies", icon: Lightbulb },
  { path: "/theories", label: "Theories", icon: Atom },
  { path: "/collisions", label: "Collisions", icon: Zap },
  { path: "/products", label: "Products", icon: Package },
  { path: "/analytics", label: "Analytics", icon: BarChart3 },
  { path: "/settings", label: "Settings", icon: Settings },
];

function ZhihuitiLogo({ collapsed }: { collapsed: boolean }) {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <Brain className="w-6 h-6 text-cyan-400 flex-shrink-0" />
      {!collapsed && (
        <span className="font-semibold text-sm tracking-tight">
          <span className="text-cyan-400">zhihu</span>
          <span className="text-foreground">iti</span>
        </span>
      )}
    </div>
  );
}

export default function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const { dark, toggle } = useTheme();

  // Close mobile sidebar on navigation
  useEffect(() => {
    setMobileOpen(false);
  }, [location]);

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile top bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 h-12 bg-sidebar border-b border-sidebar-border flex items-center px-3 gap-3">
        <button onClick={() => setMobileOpen(o => !o)} className="text-muted-foreground hover:text-foreground">
          <Menu className="w-5 h-5" />
        </button>
        <ZhihuitiLogo collapsed={false} />
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/60" onClick={() => setMobileOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        ${collapsed ? "w-16" : "w-56"} flex-shrink-0 flex flex-col
        bg-sidebar border-r border-sidebar-border transition-all duration-200
        fixed md:static inset-y-0 left-0 z-50
        ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
      `}>
        <div className={`h-14 flex items-center ${collapsed ? "justify-center" : "px-4"} border-b border-sidebar-border`}>
          <ZhihuitiLogo collapsed={collapsed} />
        </div>

        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {navItems.map((item) => {
            const isActive = item.path === "/"
              ? location === "/"
              : location === item.path || location.startsWith(item.path + "/");
            const Icon = item.icon;
            return (
              <Link key={item.path} href={item.path}>
                <div
                  className={`
                    flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm font-medium cursor-pointer
                    transition-colors duration-150
                    ${isActive
                      ? "bg-cyan-500/10 text-cyan-400"
                      : "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent"
                    }
                  `}
                >
                  <Icon className="w-4 h-4 flex-shrink-0" />
                  {!collapsed && <span>{item.label}</span>}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="px-2 pb-3 space-y-1">
          <button
            onClick={toggle}
            className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
          >
            {dark ? <Sun className="w-4 h-4 flex-shrink-0" /> : <Moon className="w-4 h-4 flex-shrink-0" />}
            {!collapsed && <span>{dark ? "Light Mode" : "Dark Mode"}</span>}
          </button>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center py-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto pt-12 md:pt-0">
        <div className="min-h-full animate-in">
          {children}
        </div>
      </main>
    </div>
  );
}
