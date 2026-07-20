function EmptyState() {
  return (
    <div className="flex h-full min-h-[320px] flex-col items-center justify-center px-6 text-center">
      <svg viewBox="0 0 200 120" className="mb-6 h-20 w-28 opacity-40" aria-hidden="true">
        <path d="M18 68C43 40 69 38 90 59C107 76 134 81 182 52" stroke="var(--color-signal)" strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M18 80C35 76 57 81 72 94" stroke="var(--color-text-muted)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      </svg>
      <h3 className="font-display text-2xl italic text-parchment">No transcript yet.</h3>
      <p className="mt-3 max-w-md font-sans text-sm leading-6 text-text-muted">
        This surface preserves the working thread, the retrieved context, and the procedural memory in a single flowing record.
      </p>
    </div>
  );
}

export { EmptyState };
