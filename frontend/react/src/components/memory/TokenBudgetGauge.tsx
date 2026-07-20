import { cn } from '@/lib/utils';

interface TokenBudgetGaugeProps {
  tokenCount?: number | null;
  className?: string;
}

function TokenBudgetGauge({ tokenCount, className }: TokenBudgetGaugeProps) {
  const isPlaceholder = tokenCount === null || tokenCount === undefined;

  return (
    <div className={cn('rounded-panel border border-hairline bg-ink-raised/80 p-3', className)}>
      <div className="mb-2 flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">Token budget</p>
        <span className="font-mono text-[11px] uppercase tracking-[0.24em] text-text-muted">instrument</span>
      </div>
      <div className="overflow-hidden rounded-gauge border border-hairline bg-ink">
        <div className="h-2 rounded-gauge bg-signal" style={{ width: isPlaceholder ? '40%' : `${Math.min(100, Math.max(12, tokenCount! / 20))}%` }} />
      </div>
      <div className="mt-2 text-[11px] font-mono uppercase tracking-[0.24em] text-text-muted">
        {isPlaceholder ? 'Token cost not yet reported by backend' : `${tokenCount} tok`}
      </div>
    </div>
  );
}

export { TokenBudgetGauge };
