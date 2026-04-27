/**
 * useSectionFocus — re-triggerable section focus tracker. /Oliviercontribution.
 *
 * Unlike useScrollReveal (one-shot), this hook flips `isVisible` every time
 * the element crosses the threshold — so a section's content fades in when
 * scrolled into view, fades out when scrolled away, and fades back in on
 * scroll-back-up. Powers the slide-style focus animations on the signup
 * funnel where each section owns the viewport.
 *
 * Pass `initialVisible: true` for the hero so it starts focused on mount
 * (before the IO has a chance to fire).
 */

import { useEffect, useRef, useState } from "react";

type Options = {
  /** Fraction of element that must be visible to count as focused. Default 0.3. */
  threshold?: number;
  /** Whether the element should be treated as focused before the observer runs. */
  initialVisible?: boolean;
};

export function useSectionFocus<T extends HTMLElement>(options: Options = {}) {
  const ref = useRef<T | null>(null);
  const [isVisible, setIsVisible] = useState(options.initialVisible ?? false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion) {
      setIsVisible(true);
      return;
    }

    if (typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          // One-shot: once a section has been revealed, it stays revealed
          // forever. This prevents the "dead white screen" effect where a
          // section fades out as it leaves the viewport mid-scroll, then the
          // next one hasn't faded in yet.
          observer.disconnect();
        }
      },
      { threshold: options.threshold ?? 0.3 },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [options.threshold]);

  return { ref, isVisible };
}
