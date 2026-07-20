import { motion, useReducedMotion } from 'framer-motion';
import { formatRelativeTime } from '@/lib/utils';
import type { RetrievedMemory } from '@/lib/types';
import { MemoryTypeBadge } from './MemoryTypeBadge';

interface MemoryCardProps {
  memory: RetrievedMemory;
  index?: number;
}

function MemoryCard({ memory, index = 0 }: MemoryCardProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      layout
      initial={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
      animate={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
      transition={shouldReduceMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 380, damping: 30, delay: index * 0.04 }}
      className="rounded-panel border border-hairline bg-ink/70 px-3 py-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="truncate font-sans text-sm text-text">{memory.subject}</p>
            <MemoryTypeBadge memoryType={memory.memory_type ?? 'working'} />
          </div>
          <p className="mt-1 font-sans text-sm text-text-muted">{memory.predicate} · {memory.object}</p>
          <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{formatRelativeTime(memory.timestamp)}</p>
        </div>
        {memory.score !== undefined ? (
          <div className="rounded-gauge border border-hairline bg-ink-raised px-2 py-1 font-mono text-[11px] text-text">
            {memory.score.toFixed(2)}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}

export { MemoryCard };
