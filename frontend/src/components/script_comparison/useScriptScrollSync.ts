import { useState, useRef, useCallback } from 'react';

export type ScrollMode = 'independent' | 'sync';

export function useScriptScrollSync() {
  const [scrollMode, setScrollMode] = useState<ScrollMode>('independent');
  const containersRef = useRef<Map<string, HTMLElement>>(new Map());
  const isSyncingRef = useRef<boolean>(false);
  const lastLeaderIdRef = useRef<string | null>(null);

  const registerScrollContainer = useCallback((videoId: string, element: HTMLElement | null) => {
    if (element) {
      containersRef.current.set(videoId, element);
    } else {
      containersRef.current.delete(videoId);
    }
  }, []);

  const handleScroll = useCallback((leaderId: string) => {
    if (scrollMode !== 'sync' || isSyncingRef.current) return;

    lastLeaderIdRef.current = leaderId;
    const leader = containersRef.current.get(leaderId);
    if (!leader) return;

    const maxScroll = leader.scrollHeight - leader.clientHeight;
    if (maxScroll <= 0) return;

    const progress = Math.max(0, Math.min(1, leader.scrollTop / maxScroll));

    isSyncingRef.current = true;
    requestAnimationFrame(() => {
      containersRef.current.forEach((el, id) => {
        if (id !== leaderId && el) {
          const targetMax = el.scrollHeight - el.clientHeight;
          if (targetMax > 0) {
            el.scrollTop = progress * targetMax;
          }
        }
      });

      // Release guard in the next frame
      requestAnimationFrame(() => {
        isSyncingRef.current = false;
      });
    });
  }, [scrollMode]);

  const resetScrollPositions = useCallback(() => {
    isSyncingRef.current = true;
    containersRef.current.forEach((el) => {
      if (el) {
        el.scrollTop = 0;
      }
    });
    setTimeout(() => {
      isSyncingRef.current = false;
    }, 50);
  }, []);

  const changeScrollMode = useCallback((newMode: ScrollMode, referenceLeaderId?: string | null) => {
    setScrollMode(newMode);
    if (newMode === 'sync') {
      // Find reference leader (pinned video, last interacted, or first available)
      const leaderId = referenceLeaderId || lastLeaderIdRef.current || containersRef.current.keys().next().value;
      if (leaderId) {
        const leader = containersRef.current.get(leaderId);
        if (leader) {
          const maxScroll = leader.scrollHeight - leader.clientHeight;
          const progress = maxScroll > 0 ? Math.max(0, Math.min(1, leader.scrollTop / maxScroll)) : 0;
          
          isSyncingRef.current = true;
          containersRef.current.forEach((el, id) => {
            if (id !== leaderId && el) {
              const targetMax = el.scrollHeight - el.clientHeight;
              if (targetMax > 0) {
                el.scrollTop = progress * targetMax;
              }
            }
          });
          setTimeout(() => {
            isSyncingRef.current = false;
          }, 50);
        }
      }
    }
  }, []);

  return {
    scrollMode,
    setScrollMode: changeScrollMode,
    registerScrollContainer,
    handleScroll,
    resetScrollPositions
  };
}
