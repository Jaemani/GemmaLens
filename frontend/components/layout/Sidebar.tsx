import Link from "next/link";
import { BookOpen, FileText, LayoutDashboard } from "lucide-react";

const items = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/dictionary", label: "Dictionary", icon: BookOpen }
];

export function Sidebar() {
  return (
    <aside className="hidden w-64 shrink-0 border-r border-line bg-panel px-4 py-5 md:block">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">PaperLens</p>
        <h1 className="mt-2 text-xl font-semibold">Learning harness</h1>
      </div>
      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href} className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium hover:bg-surface">
              <Icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
