import Link from "next/link";
import { BookOpen, FileQuestion, FileText, FlaskConical, HelpCircle, Languages, LayoutDashboard, Settings, Video } from "lucide-react";

const items = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/video", label: "Video", icon: Video },
  { href: "/translate", label: "Translate", icon: Languages },
  { href: "/quiz", label: "Quiz", icon: FileQuestion },
  { href: "/experiments", label: "Experiments", icon: FlaskConical },
  { href: "/dictionary", label: "Dictionary", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
  { href: "/guide", label: "Guide", icon: HelpCircle }
];

export function Sidebar() {
  return (
    <aside className="hidden w-60 shrink-0 border-r border-line bg-panel px-4 py-5 md:block">
      <div className="mb-7">
        <p className="text-base font-semibold text-accent">GemmaLens</p>
        <h1 className="mt-1 text-sm font-medium text-neutral-600">Edge language learning</h1>
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
