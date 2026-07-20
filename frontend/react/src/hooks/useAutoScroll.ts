import { useEffect, useRef, useState } from 'react';

interface UseAutoScrollOptions {
  enabled: boolean;
  dependency: unknown;
}

export function useAutoScroll<T extends HTMLElement>({ enabled, dependency }: UseAutoScrollOptions) {
  const ref = useRef<T | null>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }

    const handleScroll = () => {
      const distanceFromBottom = element.scrollHeight - (element.scrollTop + element.clientHeight);
      setShouldAutoScroll(distanceFromBottom <= 80);
    };

    element.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => element.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const element = ref.current;
    if (!element || !shouldAutoScroll || !enabled) {
      return;
    }

    element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' });
  }, [dependency, enabled, shouldAutoScroll]);

  return ref;
}
