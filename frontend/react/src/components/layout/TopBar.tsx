import { motion, useReducedMotion } from 'framer-motion';
import { Menu, PanelRightClose } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import useAppStore from '@/store/useAppStore';
import { playToggleSound, playTabSound } from '@/lib/soundEngine';
import { useTelemetry } from '@/hooks/useTelemetry';

interface TopBarProps {
  title: string;
  status: 'connected' | 'idle' | 'error';
  className?: string;
  onToggleSidebar?: () => void;
  onToggleMemory?: () => void;
}

function TopBar({ title, status, className, onToggleSidebar, onToggleMemory }: TopBarProps) {
  const shouldReduceMotion = useReducedMotion();
  const soundEnabled = useAppStore((state) => state.soundEnabled);
  const toggleSoundEnabled = useAppStore((state) => state.toggleSoundEnabled);
  const { fps, memoryNodeCount, apiLatencyMs, latencyStatus, tokenVelocity } = useTelemetry();
  const dotColor = status === 'connected' ? 'bg-signal' : status === 'error' ? 'bg-danger' : 'bg-text-muted';

  return (
    <div className={cn('flex items-center justify-between gap-2 rounded-panel border border-hairline bg-ink-raised/90 px-4 py-3', className)}>
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          className="px-2 py-1 lg:hidden"
          sound="none"
          onClick={() => {
            playTabSound();
            onToggleSidebar?.();
          }}
          aria-label="Open conversation sidebar"
        >
          <Menu className="size-4" />
        </Button>
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-text-muted">Active transcript</p>
          <h2 className="font-display text-xl text-parchment">{title}</h2>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div className="mr-1 hidden items-center gap-2 rounded-pill border border-hairline bg-ink/70 px-3 py-1 sm:flex">
          <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">fps</span>
          <span className="font-mono text-[11px] text-text">{fps || '—'}</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">nodes</span>
          <span className="font-mono text-[11px] text-text">{memoryNodeCount}</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">lat</span>
          <span className="font-mono text-[11px] text-text">{apiLatencyMs === null ? '—' : `${apiLatencyMs}ms`}</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">vel</span>
          <span className="font-mono text-[11px] text-text">{tokenVelocity.toFixed(1)}t/s</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="px-2 py-1"
          sound="none"
          onClick={() => {
            playToggleSound();
            toggleSoundEnabled();
          }}
          aria-label="Toggle sound effects"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.24em]">{soundEnabled ? 'snd on' : 'snd off'}</span>
        </Button>
        <Button variant="ghost" size="sm" className="px-2 py-1 lg:hidden" sound="none" onClick={() => {
          playTabSound();
          onToggleMemory?.();
        }} aria-label="Open memory panel">
          <PanelRightClose className="size-4" />
        </Button>
        <motion.span
          className={cn('size-2 rounded-full', dotColor)}
          animate={shouldReduceMotion ? { opacity: 1 } : status === 'connected' ? { opacity: [0.5, 1, 0.5] } : { opacity: 1 }}
          transition={shouldReduceMotion ? { duration: 0.01 } : { type: 'spring', stiffness: 320, damping: 24, delay: 0.08, repeat: status === 'connected' ? Infinity : 0 }}
        />
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{latencyStatus}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{status}</span>
      </div>
    </div>
  );
}

export { TopBar };
