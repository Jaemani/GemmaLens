import Link from "next/link";
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
  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col overflow-y-auto border-r border-line bg-panel px-4 py-5 md:flex">
      <div className="mb-7">
        <p className="text-base font-semibold text-ink">GemmaLens</p>
        <h1 className="mt-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">Edge language learning</h1>
      </div>
      <nav className="flex-1 space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-neutral-700 hover:bg-surface hover:text-ink">
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <GlobalStatusDock />
    </aside>
  );
}
