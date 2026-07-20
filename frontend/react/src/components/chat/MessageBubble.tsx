import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import type { Message } from '@/lib/types';

interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  index?: number;
}

function MessageBubble({ message, isStreaming = false, index = 0 }: MessageBubbleProps) {
  const shouldReduceMotion = useReducedMotion();

  if (message.role === 'user') {
    return (
      <motion.div
        layout
        initial={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
        animate={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
        transition={shouldReduceMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 380, damping: 30, delay: index * 0.04 }}
        className="flex justify-end px-2 py-2"
      >
        <div className="max-w-[78%] rounded-panel border border-parchment/20 bg-parchment px-3 py-2 text-sm leading-6 text-ink">
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      layout
      initial={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 }}
      animate={shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 }}
      transition={shouldReduceMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 380, damping: 30, delay: index * 0.04 }}
      className="px-2 py-2"
    >
      <div className={cn('border-l-2 border-transparent pl-3 pr-2 text-base leading-7 text-text', isStreaming && 'border-signal')}>
        <span className="whitespace-pre-wrap">{message.content}</span>
        {isStreaming ? <span className="ml-1 inline-block h-4 w-2 translate-y-[2px] bg-signal" /> : null}
      </div>
    </motion.div>
  );
}

export { MessageBubble };
