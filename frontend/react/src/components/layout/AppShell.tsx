import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ChatWindow } from '@/components/chat/ChatWindow';
import { MemoryPanel } from '@/components/memory/MemoryPanel';
import { cn } from '@/lib/utils';
import Sidebar from './Sidebar';

function AppShell() {
  const shouldReduceMotion = useReducedMotion();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);

  const initialState = shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 18 };
  const animateState = shouldReduceMotion ? { opacity: 1, y: 0 } : { opacity: 1, y: 0 };
  const springTransition = shouldReduceMotion ? { duration: 0.01 } : { type: 'spring' as const, stiffness: 380, damping: 30 };

  return (
    <div className="relative min-h-screen overflow-hidden bg-ink text-text">
      <div className="grain" aria-hidden="true" />
      <div className="relative z-10 mx-auto flex min-h-screen max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <motion.header
          initial={initialState}
          animate={animateState}
          transition={{ ...springTransition, delay: shouldReduceMotion ? 0 : 0.02 }}
          className="rounded-panel border border-hairline bg-ink-raised/85 px-5 py-4"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-text-muted">Synapse</p>
              <h1 className="font-display text-2xl text-parchment">Persistent memory workspace</h1>
            </div>
            <div className="rounded-pill border border-signal/30 bg-signal/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.24em] text-signal">
              live trace
            </div>
          </div>
        </motion.header>

        <main className="flex flex-1 flex-col gap-4 lg:grid lg:grid-cols-[280px_minmax(0,1fr)_340px]">
          <motion.aside
            initial={initialState}
            animate={animateState}
            transition={{ ...springTransition, delay: shouldReduceMotion ? 0 : 0.08 }}
            className="hidden overflow-hidden rounded-panel border border-hairline bg-ink-raised lg:block"
          >
            <Sidebar />
          </motion.aside>

          <motion.section
            initial={initialState}
            animate={animateState}
            transition={{ ...springTransition, delay: shouldReduceMotion ? 0 : 0.16 }}
            className="order-2 min-h-0 overflow-hidden rounded-panel border border-hairline bg-ink lg:order-none"
          >
            <ChatWindow onToggleSidebar={() => setIsSidebarOpen(true)} onToggleMemory={() => setIsMemoryOpen(true)} />
          </motion.section>

          <motion.aside
            initial={initialState}
            animate={animateState}
            transition={{ ...springTransition, delay: shouldReduceMotion ? 0 : 0.24 }}
            className="hidden overflow-hidden rounded-panel border border-hairline bg-ink lg:block"
          >
            <MemoryPanel />
          </motion.aside>
        </main>

        <motion.div
          initial={false}
          animate={isSidebarOpen || isMemoryOpen ? { opacity: 1 } : { opacity: 0 }}
          transition={springTransition}
          className={cn(
            'fixed inset-0 z-30 bg-ink/80 lg:hidden',
            isSidebarOpen || isMemoryOpen ? 'pointer-events-auto' : 'pointer-events-none',
          )}
          onClick={() => {
            setIsSidebarOpen(false);
            setIsMemoryOpen(false);
          }}
          aria-hidden="true"
        />

        <motion.div
          initial={false}
          animate={isSidebarOpen ? { x: 0, opacity: 1 } : { x: '-100%', opacity: 0.96 }}
          transition={springTransition}
          className="fixed inset-y-0 left-0 z-40 w-[84vw] max-w-[320px] lg:hidden"
        >
          <Sidebar />
        </motion.div>

        <motion.div
          initial={false}
          animate={isMemoryOpen ? { x: 0, opacity: 1 } : { x: '100%', opacity: 0.96 }}
          transition={springTransition}
          className="fixed inset-y-0 right-0 z-40 w-[84vw] max-w-[340px] lg:hidden"
        >
          <MemoryPanel />
        </motion.div>
      </div>
    </div>
  );
}

export default AppShell;
