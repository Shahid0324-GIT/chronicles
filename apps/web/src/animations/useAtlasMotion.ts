"use client";
import { useRef, type RefObject } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
gsap.registerPlugin(useGSAP);
export const reduceMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
// One scoped controller for overlay entry, mode changes, story cards and discoveries.
export function useAtlasMotion(
  scope: RefObject<HTMLElement | null>,
  dependency: unknown,
  kind: "entry" | "card" | "mode" = "entry",
) {
  useGSAP(
    () => {
      const media = gsap.matchMedia();
      media.add(
        {
          full: "(prefers-reduced-motion: no-preference)",
          reduced: "(prefers-reduced-motion: reduce)",
        },
        (context) => {
          const target = kind === "entry" ? ".entry-motion" : scope.current;
          if (!target) return;
          gsap.fromTo(
            target,
            {
              autoAlpha: context.conditions?.reduced ? 1 : 0,
              y: kind === "card" ? 14 : 8,
            },
            {
              autoAlpha: 1,
              y: 0,
              duration: context.conditions?.reduced ? 0 : 0.55,
              stagger: kind === "entry" ? 0.05 : 0,
              ease: "power2.out",
              overwrite: true,
            },
          );
        },
      );
      return () => media.revert();
    },
    { scope, dependencies: [dependency, kind], revertOnUpdate: true },
  );
}
export function useExitMotion(
  scope: RefObject<HTMLElement | null>,
  action: () => void,
  dependency?: unknown,
) {
  const tween = useRef<gsap.core.Tween | null>(null);
  const { contextSafe } = useGSAP(
    () => () => {
      tween.current?.kill();
    },
    { scope, dependencies: [dependency], revertOnUpdate: true },
  );
  return () =>
    contextSafe(() => {
      tween.current?.kill();
      tween.current = gsap.to(scope.current, {
        autoAlpha: 0,
        y: 8,
        duration: reduceMotion() ? 0 : 0.18,
        overwrite: true,
        onComplete: action,
      });
    })();
}
