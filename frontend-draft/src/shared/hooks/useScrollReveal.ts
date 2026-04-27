/**
 * useScrollReveal — IntersectionObserver-based one-shot reveal hook.
 * /Oliviercontribution.
 *
 * Returns a ref. Attach to any element. When the element first enters the
 * viewport, the hook adds the `revealed` class. Disconnects after the first
 * trigger so the animation never re-fires on scroll-back-up.
 *
 * Pure CSS does the actual animating — see `.scroll-reveal` / `.scroll-reveal-stagger`
 * in globals.css. This hook just toggles the class.
 *
 * Respects prefers-reduced-motion: those users get the `revealed` class
 * immediately so they see the content without animation.
 */

import { useEffect, useRef } from "react";

type Options = {
  /** 0–1, fraction of element that must be visible to trigger. Default 0.15. */
  threshold?: number;
  /** Optional root margin string passed to IntersectionObserver. */
  rootMargin?: string;
};

export function useScrollReveal<T extends HTMLElement>(options: Options = {}) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const reduceMotion =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion) {
      node.classList.add("revealed");
      return;
    }

    if (typeof IntersectionObserver === "undefined") {
      // Older browsers — show immediately, no animation
      node.classList.add("revealed");
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("revealed");
            observer.disconnect();
            break;
          }
        }
      },
      {
        threshold: options.threshold ?? 0.15,
        rootMargin: options.rootMargin ?? "0px 0px -40px 0px",
      },
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [options.threshold, options.rootMargin]);

  return ref;
}
