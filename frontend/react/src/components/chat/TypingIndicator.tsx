import { motion, useReducedMotion } from 'framer-motion';

function TypingIndicator() {
  const shouldReduceMotion = useReducedMotion();

  return (
    <div className="px-2 py-2">
      <div className="flex items-center gap-2 pl-3">
        {[0, 1, 2].map((index) => (
          <motion.span
            key={index}
            className="block size-2 rounded-full bg-text-muted"
            animate={shouldReduceMotion ? { opacity: 0.7 } : { opacity: [0.3, 0.8, 0.3] }}
            transition={shouldReduceMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 380, damping: 30, delay: index * 0.12, repeat: Infinity }}
          />
        ))}
      </div>
    </div>
  );
}

export { TypingIndicator };
