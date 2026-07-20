import { useEffect, useMemo, useRef, useState } from 'react';
import useAppStore, { EMPTY_MESSAGES } from '@/store/useAppStore';

function useTelemetry() {
  const [fps, setFps] = useState(0);
  const isStreaming = useAppStore((state) => state.isStreaming);
  const activeId = useAppStore((state) => state.activeId);
  const messages = useAppStore((state) => {
    if (!state.activeId) {
      return EMPTY_MESSAGES;
    }

    return state.messagesByConversation[state.activeId] ?? EMPTY_MESSAGES;
  });
  const memoryNodeCount = useAppStore((state) => state.lastRetrievedContext.length);
  const apiLatencyMs = useAppStore((state) => state.apiLatencyMs);
  const streamStartedAtRef = useRef<number | null>(null);

  useEffect(() => {
    let frameId = 0;
    let frames = 0;
    let lastTimestamp = performance.now();

    const tick = (timestamp: number) => {
      frames += 1;
      if (timestamp - lastTimestamp >= 1000) {
        setFps(Math.round((frames * 1000) / (timestamp - lastTimestamp)));
        frames = 0;
        lastTimestamp = timestamp;
      }
      frameId = window.requestAnimationFrame(tick);
    };

    frameId = window.requestAnimationFrame(tick);

    return () => {
      window.cancelAnimationFrame(frameId);
    };
  }, []);

  useEffect(() => {
    if (isStreaming && streamStartedAtRef.current === null) {
      streamStartedAtRef.current = performance.now();
      return;
    }

    if (!isStreaming) {
      streamStartedAtRef.current = null;
    }
  }, [isStreaming]);

  const latestAssistantMessage = useMemo(() => {
    return [...messages].reverse().find((message) => message.role === 'assistant') ?? null;
  }, [messages]);

  const streamElapsedSeconds = streamStartedAtRef.current === null ? 0 : Math.max(0.1, (performance.now() - streamStartedAtRef.current) / 1000);
  const tokenVelocity = useMemo(() => {
    if (!isStreaming || !latestAssistantMessage) {
      return 0;
    }

    const approximateTokens = Math.max(1, Math.ceil((latestAssistantMessage.content?.length ?? 0) / 4));
    return Math.round((approximateTokens / streamElapsedSeconds) * 10) / 10;
  }, [isStreaming, latestAssistantMessage, streamElapsedSeconds]);

  const latencyStatus = apiLatencyMs === null ? 'idle' : apiLatencyMs < 220 ? 'healthy' : apiLatencyMs < 700 ? 'warm' : 'slow';

  return {
    activeId,
    fps,
    memoryNodeCount,
    apiLatencyMs,
    latencyStatus,
    tokenVelocity,
  };
}

export { useTelemetry };
