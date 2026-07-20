import { cn } from '@/lib/utils';
import type { MemoryType } from '@/lib/types';

interface MemoryTypeBadgeProps {
  memoryType: MemoryType | 'working';
}

const typeStyles: Record<MemoryType | 'working', { border: string; text: string; fill: string }> = {
  working: { border: 'border-signal', text: 'text-signal', fill: 'bg-signal/15' },
  episodic: { border: 'border-episodic', text: 'text-episodic', fill: 'bg-episodic/15' },
  semantic: { border: 'border-semantic', text: 'text-semantic', fill: 'bg-semantic/15' },
  procedural: { border: 'border-procedural', text: 'text-procedural', fill: 'bg-procedural/15' },
};

function MemoryTypeBadge({ memoryType }: MemoryTypeBadgeProps) {
  const style = typeStyles[memoryType];

  return (
    <span className={cn('inline-flex items-center rounded-pill border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.24em]', style.border, style.fill, style.text)}>
      {memoryType}
    </span>
  );
}

export { MemoryTypeBadge };
