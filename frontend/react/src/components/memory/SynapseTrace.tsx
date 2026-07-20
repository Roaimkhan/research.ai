import { useEffect, useMemo, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import type { RetrievedMemory } from '@/lib/types';
import { playMemorySound } from '@/lib/soundEngine';
import useAppStore from '@/store/useAppStore';

interface SynapseTraceProps {
  memories: RetrievedMemory[];
}

interface ParticleNode {
  id: string;
  memory: RetrievedMemory;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  memory: RetrievedMemory | null;
}

const MAX_NODES = 8;

function getNodeColor(memory: RetrievedMemory) {
  if (memory.memory_type === 'episodic') {
    return 'var(--color-episodic)';
  }

  if (memory.memory_type === 'semantic') {
    return 'var(--color-semantic)';
  }

  if (memory.memory_type === 'procedural') {
    return 'var(--color-procedural)';
  }

  return 'var(--color-signal)';
}

function SynapseTrace({ memories }: SynapseTraceProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const nodesRef = useRef<ParticleNode[]>([]);
  const sizeRef = useRef({ width: 320, height: 320 });
  const prefersReducedMotion = useReducedMotion();
  const soundEnabled = useAppStore((state) => state.soundEnabled);
  const [tooltip, setTooltip] = useState<TooltipState>({ visible: false, x: 0, y: 0, memory: null });

  const visibleMemories = useMemo(() => memories.slice(0, MAX_NODES), [memories]);

  useEffect(() => {
    if (memories.length === 0) {
      return;
    }

    if (soundEnabled) {
      playMemorySound();
    }
  }, [memories, soundEnabled]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;

    if (!canvas || !container) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const resizeCanvas = () => {
      const rect = container.getBoundingClientRect();
      const width = Math.max(280, Math.floor(rect.width));
      const height = Math.max(280, Math.floor(rect.height || rect.width * 0.9));
      sizeRef.current = { width, height };
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    resizeCanvas();

    const handleResize = () => {
      resizeCanvas();
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const { width, height } = sizeRef.current;
    const centerX = width / 2;
    const centerY = height / 2;

    const buildNodes = () => {
      const nextNodes: ParticleNode[] = visibleMemories.map((memory, index) => {
        const angle = (index / Math.max(1, visibleMemories.length)) * Math.PI * 2 - Math.PI / 2;
        const radius = Math.min(110, Math.max(70, width * 0.22));
        const x = centerX + Math.cos(angle) * radius + (index % 2 === 0 ? 24 : -24);
        const y = centerY + Math.sin(angle) * radius + (index % 3 === 0 ? 20 : -16);
        return {
          id: `${memory.subject}-${index}`,
          memory,
          x,
          y,
          vx: 0,
          vy: 0,
          radius: 6 + (index % 3) * 1.2,
          color: getNodeColor(memory),
        };
      });

      nodesRef.current = nextNodes;
    };

    buildNodes();

    let animationFrame = 0;
    let pointer = { x: centerX, y: centerY, active: false };

    const handlePointerMove = (event: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
      pointer.active = true;

      const node = nodesRef.current.find((candidate) => {
        const dx = candidate.x - pointer.x;
        const dy = candidate.y - pointer.y;
        return Math.hypot(dx, dy) < candidate.radius + 16;
      });

      if (node) {
        setTooltip({ visible: true, x: pointer.x + 12, y: pointer.y + 12, memory: node.memory });
      } else {
        setTooltip((current) => ({ ...current, visible: false, memory: null }));
      }
    };

    const handlePointerLeave = () => {
      pointer.active = false;
      setTooltip({ visible: false, x: 0, y: 0, memory: null });
    };

    container.addEventListener('mousemove', handlePointerMove);
    container.addEventListener('mouseleave', handlePointerLeave);

    let lastTime = performance.now();
    const render = (time: number) => {
      const delta = Math.min(1.6, (time - lastTime) / 16.67);
      lastTime = time;
      context.clearRect(0, 0, width, height);

      context.fillStyle = 'rgba(11, 14, 19, 0.14)';
      context.fillRect(0, 0, width, height);

      context.save();
      context.strokeStyle = 'rgba(111, 255, 192, 0.18)';
      context.lineWidth = 1;
      context.setLineDash([3, 6]);
      context.beginPath();
      context.moveTo(width * 0.5, height * 0.5);
      context.lineTo(width * 0.2, height * 0.2);
      context.lineTo(width * 0.8, height * 0.3);
      context.stroke();
      context.restore();

      const nodes = nodesRef.current;

      for (let index = 0; index < nodes.length; index += 1) {
        const node = nodes[index];
        if (!node) {
          continue;
        }
        const targetX = centerX + Math.cos((index / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2) * Math.min(110, Math.max(70, width * 0.22)) + (index % 2 === 0 ? 24 : -24);
        const targetY = centerY + Math.sin((index / Math.max(1, nodes.length)) * Math.PI * 2 - Math.PI / 2) * Math.min(110, Math.max(70, width * 0.22)) + (index % 3 === 0 ? 20 : -16);

        node.vx += (targetX - node.x) * 0.0012 * delta;
        node.vy += (targetY - node.y) * 0.0012 * delta;

        if (pointer.active) {
          const dx = node.x - pointer.x;
          const dy = node.y - pointer.y;
          const distance = Math.hypot(dx, dy);
          if (distance < 120) {
            const force = (120 - distance) / 120;
            node.vx += (dx / Math.max(1, distance)) * force * 0.04 * delta;
            node.vy += (dy / Math.max(1, distance)) * force * 0.04 * delta;
          }
        }

        node.vx *= prefersReducedMotion ? 0.92 : 0.94;
        node.vy *= prefersReducedMotion ? 0.92 : 0.94;
        node.x += node.vx * delta;
        node.y += node.vy * delta;

        node.x = Math.max(node.radius + 6, Math.min(width - node.radius - 6, node.x));
        node.y = Math.max(node.radius + 6, Math.min(height - node.radius - 6, node.y));
      }

      for (let index = 0; index < nodes.length; index += 1) {
        const node = nodes[index];
        const nextNode = nodes[(index + 1) % nodes.length];
        if (!node || !nextNode) {
          continue;
        }

        const lineAlpha = 0.24 + 0.08 * Math.sin(time / 600 + index);
        context.beginPath();
        context.moveTo(node.x, node.y);
        context.lineTo(nextNode.x, nextNode.y);
        context.strokeStyle = `rgba(111, 255, 192, ${lineAlpha.toFixed(3)})`;
        context.lineWidth = 1.2;
        context.stroke();

        const packetProgress = ((time / 1000) * 0.38 + index * 0.16) % 1;
        const packetX = node.x + (nextNode.x - node.x) * packetProgress;
        const packetY = node.y + (nextNode.y - node.y) * packetProgress;
        context.beginPath();
        context.arc(packetX, packetY, 2.4, 0, Math.PI * 2);
        context.fillStyle = 'rgba(237, 239, 242, 0.95)';
        context.fill();
      }

      for (const node of nodes) {
        const glow = pointer.active ? 16 : 10;
        const isHovered = tooltip.memory?.subject === node.memory.subject && tooltip.memory?.predicate === node.memory.predicate;
        context.beginPath();
        context.arc(node.x, node.y, isHovered ? node.radius + 2 : node.radius, 0, Math.PI * 2);
        context.fillStyle = node.color;
        context.shadowBlur = isHovered ? glow + 8 : glow;
        context.shadowColor = `${node.color}`;
        context.fill();
      }

      animationFrame = window.requestAnimationFrame(render);
    };

    animationFrame = window.requestAnimationFrame(render);

    return () => {
      window.cancelAnimationFrame(animationFrame);
      container.removeEventListener('mousemove', handlePointerMove);
      container.removeEventListener('mouseleave', handlePointerLeave);
    };
  }, [prefersReducedMotion, tooltip.memory?.predicate, tooltip.memory?.subject, visibleMemories]);

  return (
    <div className="rounded-panel border border-hairline bg-ink-raised/80 p-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="font-display text-lg text-parchment">Synapse Trace</p>
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-text-muted">{visibleMemories.length} nodes</span>
      </div>
      <div ref={containerRef} className="relative h-[320px] w-full overflow-hidden rounded-panel border border-hairline/70 bg-ink/70">
        <canvas ref={canvasRef} className="h-full w-full" role="img" aria-label={`Synapse trace visualization with ${visibleMemories.length} memory nodes`} />
        {tooltip.visible && tooltip.memory ? (
          <div className="pointer-events-none absolute z-10 max-w-[220px] rounded-pill border border-signal/30 bg-ink/90 px-3 py-2 text-[11px] font-mono uppercase tracking-[0.24em] text-text">
            <div className="text-signal">{tooltip.memory.memory_type ?? 'memory'}</div>
            <div className="mt-1 normal-case tracking-[0.16em] text-text-muted">{tooltip.memory.subject}</div>
          </div>
        ) : null}
        {visibleMemories.length === 0 ? (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center px-4 text-center text-sm font-sans text-text-muted">
            No memory retrieved for this turn yet.
          </div>
        ) : null}
      </div>
      <p className="sr-only">{visibleMemories.length} memory nodes are shown around the current turn. The center node represents the current turn.</p>
    </div>
  );
}

export { SynapseTrace };
