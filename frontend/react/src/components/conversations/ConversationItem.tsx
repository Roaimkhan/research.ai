import { useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { formatRelativeTime, truncate } from '@/lib/utils';
import { cn } from '@/lib/utils';
import useAppStore from '@/store/useAppStore';
import type { Conversation } from '@/lib/types';

interface ConversationItemProps {
  conversation: Conversation;
  index?: number;
}

function ConversationItem({ conversation, index = 0 }: ConversationItemProps) {
  const shouldReduceMotion = useReducedMotion();
  const activeId = useAppStore((state) => state.activeId);
  const setActive = useAppStore((state) => state.setActive);
  const isActive = activeId === conversation.id;

  const relativeTime = useMemo(() => formatRelativeTime(conversation.updated_at), [conversation.updated_at]);

  const motionProps = shouldReduceMotion
    ? {}
    : {
        whileTap: { scale: 0.98 },
        transition: { type: 'spring' as const, stiffness: 380, damping: 30 },
      };

  return (
    <motion.button
      type="button"
      layout
      initial={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
      animate={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
      transition={shouldReduceMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 380, damping: 30, delay: index * 0.04 }}
      onClick={() => setActive(conversation.id)}
      aria-pressed={isActive}
      className={cn(
        'group w-full rounded-panel border border-transparent px-3 py-3 text-left transition-colors duration-200 hover:bg-parchment/10',
        isActive && 'border-l-2 border-signal bg-parchment/10',
      )}
      {...motionProps}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="truncate font-sans text-sm text-text">{truncate(conversation.title, 36)}</p>
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{relativeTime}</span>
      </div>
      <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{conversation.workspace_id ?? 'workspace'}</p>
    </motion.button>
  );
}

export { ConversationItem };
