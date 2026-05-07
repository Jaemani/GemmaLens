import Link from "next/link";
import { ArrowRight, BookMarked, FileText } from "lucide-react";
import { ModelStatusCard } from "@/components/common/ModelStatusCard";
import { AppShell } from "@/components/layout/AppShell";
import { api } from "@/lib/api";
import type { ModelStatus } from "@/lib/types";

export default async function DashboardPage() {
  let modelStatus: ModelStatus | null = null;
  try {
    modelStatus = await api.getModelStatus();
  } catch {
    modelStatus = null;
  }

  return (
    <AppShell>
      <section className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <div className="rounded-lg border border-line bg-panel p-6 shadow-material">
          <h1 className="text-3xl font-semibold tracking-normal">Turn difficult documents into personalized language lessons.</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-neutral-700">
            Analyze academic papers and reports by domain, vocabulary, sentence structure, and learning priority.
          </p>
          <Link href="/documents" className="mt-6 inline-flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white">
            Start analysis
            <ArrowRight size={16} />
          </Link>
        </div>
        <div className="grid gap-4">
          <ModelStatusCard status={modelStatus} />
          <Stat icon={<FileText size={20} />} label="Pipeline" value="Document to learning object" />
          <Stat icon={<BookMarked size={20} />} label="Dictionary" value="Save terms and structures" />
        </div>
      </section>
    </AppShell>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-panel p-5 shadow-material">
      <div className="text-accent">{icon}</div>
      <p className="mt-3 text-sm text-neutral-500">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
