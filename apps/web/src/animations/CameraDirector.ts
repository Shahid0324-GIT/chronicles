import gsap from "gsap";
import { CHRONICLE_DESIGN } from "@/features/chronicle/design";
import type { Camera } from "sigma";
import type { CameraPosition } from "@/stores/exploration";
import { reduceMotion } from "./useAtlasMotion";
// GSAP owns one camera tween and one highlight scalar, never per-node DOM animations.
export class CameraDirector {
  private motion: gsap.core.Tween | null = null;
  private emphasis: gsap.core.Tween | null = null;
  private discovery: gsap.core.Tween | null = null;
  constructor(private readonly camera: Camera) {}
  move(target: Partial<CameraPosition>) {
    this.motion?.kill();
    this.camera.cancelAnimation();
    const position = { ...this.camera.getState() };
    this.motion = gsap.to(position, {
      ...target,
      duration: reduceMotion() ? 0 : CHRONICLE_DESIGN.motion.camera,
      ease: CHRONICLE_DESIGN.motion.cameraEase,
      onUpdate: () => this.camera.setState(position),
    });
  }
  highlight(update: (value: number) => void) {
    this.emphasis?.kill();
    const state = { value: 0 };
    this.emphasis = gsap.to(state, {
      value: 1,
      duration: reduceMotion() ? 0 : CHRONICLE_DESIGN.motion.emphasis,
      ease: CHRONICLE_DESIGN.motion.ease,
      onUpdate: () => update(state.value),
    });
  }
  interrupt() {
    this.motion?.kill();
    this.camera.cancelAnimation();
  }
  reveal(update: (value: number) => void) {
    this.discovery?.kill();
    const state = { value: 0 };
    update(0);
    this.discovery = gsap.to(state, {
      value: 1,
      duration: reduceMotion() ? 0 : CHRONICLE_DESIGN.motion.reveal,
      ease: CHRONICLE_DESIGN.motion.ease,
      onUpdate: () => update(state.value),
    });
  }
  dispose() {
    this.interrupt();
    this.emphasis?.kill();
    this.discovery?.kill();
  }
}
