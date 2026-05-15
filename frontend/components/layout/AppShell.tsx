import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-surface">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <TopBar />
        <main className="w-full px-4 py-5 sm:px-6 lg:px-8 xl:px-10">{children}</main>
      </div>
    </div>
  );
}
