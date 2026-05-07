import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <TopBar />
        <main className="mx-auto max-w-6xl px-5 py-6">{children}</main>
      </div>
    </div>
  );
}
