import { ScrollArea } from '@/components/ui/scroll-area';
import { useLastRetrieval } from '@/store/useAppStore';
import { TokenBudgetGauge } from './TokenBudgetGauge';
import { SynapseTrace } from './SynapseTrace';
import { MemoryCard } from './MemoryCard';
import { useMemo } from 'react';

function MemoryPanel() {
  const retrievedContext = useLastRetrieval();
  const hasMemory = retrievedContext.length > 0;

  const groupedMemories = useMemo(() => {
    return retrievedContext.reduce<Record<string, typeof retrievedContext>>((accumulator, memory) => {
      const bucket = memory.memory_type ?? 'working';
      accumulator[bucket] = [...(accumulator[bucket] ?? []), memory];
      return accumulator;
    }, {});
  }, [retrievedContext]);

  return (
    <aside className="flex h-full flex-col gap-3 rounded-panel border border-hairline bg-ink-raised/95 p-3">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-text-muted">Memory panel</p>
        <h2 className="font-display text-2xl text-parchment">Synapse Trace</h2>
      </div>
      <SynapseTrace memories={retrievedContext} />
      <TokenBudgetGauge tokenCount={null} />
      <div className="min-h-0 flex-1">
        <ScrollArea className="h-full">
          {hasMemory ? (
            <div className="space-y-2 pr-2">
              {Object.entries(groupedMemories).map(([group, memories], groupIndex) => (
                <div key={group} className="space-y-2">
                  <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{group}</p>
                  {memories.map((memory, index) => (
                    <MemoryCard key={`${memory.subject}-${index}`} memory={memory} index={groupIndex * 3 + index} />
                  ))}
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-panel border border-hairline bg-ink/70 px-3 py-6 text-center text-sm text-text-muted">
              No memory retrieved for this turn — answered from current context.
            </div>
          )}
        </ScrollArea>
      </div>
    </aside>
  );
}

export { MemoryPanel };
