import { act, renderHook } from "@testing-library/react";
import { StrictMode, useRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NEAR_START, TRIGGER_START } from "./playback";
import { useChapterPlayback } from "./useChapterPlayback";

interface TriggerConfig {
  start: string;
  onEnter?: () => void;
  onToggle?: (self: { isActive: boolean; direction: number }) => void;
}
interface TweenVars {
  duration: number;
  ease: string;
  onUpdate: () => void;
}

const created: TriggerConfig[] = [];
const tweens: { target: { value: number }; vars: TweenVars; killed: boolean }[] = [];

vi.mock("./gsap", () => ({
  ScrollTrigger: {
    create: (config: TriggerConfig) => {
      created.push(config);
      return { kill: () => undefined };
    },
  },
  gsap: {
    to: (target: { value: number }, vars: TweenVars) => {
      const tween = { target, vars, killed: false };
      tweens.push(tween);
      return {
        kill: () => {
          tween.killed = true;
        },
      };
    },
  },
}));

type Options = Parameters<typeof useChapterPlayback>[1];

function setup(options: Options) {
  return renderHook(
    (props: Options) => {
      const ref = useRef<HTMLElement>(document.createElement("section"));
      return useChapterPlayback(ref, props);
    },
    { initialProps: options },
  );
}

const trigger = () => created.find((c) => c.start === TRIGGER_START);
const near = () => created.find((c) => c.start === NEAR_START);
const enter = (direction = 1) => act(() => trigger()?.onToggle?.({ isActive: true, direction }));

beforeEach(() => {
  created.length = 0;
  tweens.length = 0;
  vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

describe("useChapterPlayback", () => {
  it("con enabled false devuelve el estado final sin crear disparadores", () => {
    const { result } = setup({ durationMs: 3000, enabled: false, ready: true });
    expect(result.current.progress).toBe(1);
    expect(created).toHaveLength(0);
  });

  it("no avanza antes de entrar", () => {
    const { result } = setup({ durationMs: 3000, enabled: true, ready: true });
    expect(result.current.progress).toBe(0);
    expect(tweens).toHaveLength(0);
  });

  it("al entrar con los cuadros listos se reproduce en la duración del capítulo", () => {
    const { result } = setup({ durationMs: 3000, enabled: true, ready: true });
    enter();
    expect(tweens).toHaveLength(1);
    expect(tweens[0]!.vars.duration).toBe(3);
    expect(tweens[0]!.vars.ease).toBe("power2.out");
    act(() => {
      tweens[0]!.target.value = 1;
      tweens[0]!.vars.onUpdate();
    });
    expect(result.current.progress).toBe(1);
  });

  it("entrar desde abajo también reproduce", () => {
    setup({ durationMs: 3000, enabled: true, ready: true });
    enter(-1);
    expect(tweens).toHaveLength(1);
  });

  it("una sola reproducción por carga", () => {
    setup({ durationMs: 3000, enabled: true, ready: true });
    enter();
    enter(-1);
    expect(tweens).toHaveLength(1);
  });

  it("sin cuadros, espera el tope y reproduce igual", () => {
    setup({ durationMs: 3000, enabled: true, ready: false });
    enter();
    act(() => vi.advanceTimersByTime(2499));
    expect(tweens).toHaveLength(0);
    act(() => vi.advanceTimersByTime(1));
    expect(tweens).toHaveLength(1);
  });

  it("si los cuadros llegan antes del tope, empieza en ese momento", () => {
    const { rerender } = setup({ durationMs: 3000, enabled: true, ready: false });
    enter();
    expect(tweens).toHaveLength(0);
    rerender({ durationMs: 3000, enabled: true, ready: true });
    expect(tweens).toHaveLength(1);
  });

  it("autoplay reproduce al montar", () => {
    const { result } = setup({ durationMs: 4500, enabled: true, ready: true, autoplay: true });
    expect(tweens).toHaveLength(1);
    expect(result.current.near).toBe(true);
  });

  it("acepta otra curva", () => {
    setup({ durationMs: 4500, enabled: true, ready: true, autoplay: true, ease: "none" });
    expect(tweens[0]!.vars.ease).toBe("none");
  });

  it("near se activa al acercarse", () => {
    const { result } = setup({ durationMs: 3000, enabled: true, ready: false });
    expect(result.current.near).toBe(false);
    act(() => near()?.onEnter?.());
    expect(result.current.near).toBe(true);
  });

  it("en StrictMode queda una reproducción viva", () => {
    renderHook(
      () => {
        const ref = useRef<HTMLElement>(document.createElement("section"));
        return useChapterPlayback(ref, {
          durationMs: 4500,
          enabled: true,
          ready: true,
          autoplay: true,
        });
      },
      { wrapper: StrictMode },
    );
    expect(tweens.some((t) => !t.killed)).toBe(true);
  });
});
