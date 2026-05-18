"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { BookOpen, FileQuestion, FileText, HelpCircle, Languages, LayoutDashboard, Settings, Video } from "lucide-react";
import { GlobalStatusDock } from "./GlobalStatusDock";

const items = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/video", label: "Video", icon: Video },
  { href: "/translate", label: "Translate", icon: Languages },
  { href: "/quiz", label: "Quiz", icon: FileQuestion },
  { href: "/dictionary", label: "Library", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/guide", label: "Guide", icon: HelpCircle }
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 overflow-y-auto border-r border-line bg-panel px-3 py-5 md:flex md:flex-col">
      {/* Brand */}
      <div className="mb-7 flex items-center gap-3 px-3">
        <Image src="/gemmalens_icon.png" alt="GemmaLens" width={32} height={32} className="shrink-0" />
        <span className="text-[18px] font-bold tracking-tight text-ink">GemmaLens</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1.5">
        {items.map((item) => {
          const Icon = item.icon;
          const isActive = item.href === "/" ? pathname === "/" : pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`relative flex items-center gap-3.5 rounded-lg px-3.5 py-3 text-[15.5px] font-medium transition-colors ${
                isActive
                  ? "bg-accent-soft font-bold text-accent"
                  : "text-[#374151] hover:bg-subtle hover:text-ink"
              }`}
            >
              {isActive && (
                <span className="absolute inset-y-2 left-0 w-[3px] rounded-r-full bg-accent" />
              )}
              <Icon size={20} className="shrink-0" />
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Status */}
      <div className="mt-4 pt-4 border-t border-line">
        <GlobalStatusDock />
      </div>
    </aside>
  );
}
