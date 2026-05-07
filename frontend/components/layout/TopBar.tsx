export function TopBar() {
  return (
    <header className="flex min-h-16 items-center justify-between border-b border-line bg-panel px-5">
      <div>
        <p className="text-sm font-medium text-accent">Local-first prototype</p>
        <p className="text-xs text-neutral-600">Mock model ready without external setup</p>
      </div>
    </header>
  );
}
