import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { PhoneModel } from "./PhoneModel";
import type { PhoneScreen } from "./types";

/** Resolución máxima del lienzo: menor en el celular para cuidar la batería y los fps. */
const MAX_DPR_MOBILE = 1.5;
const MAX_DPR_DESKTOP = 2;
const MOBILE_QUERY = "(max-width: 767px)";

interface PhoneCanvasProps {
  progress: number;
  screens: readonly PhoneScreen[];
  index: number;
  fan: readonly PhoneScreen[];
  opening: number;
  isVisible: () => boolean;
}

export default function PhoneCanvas({
  progress,
  screens,
  index,
  fan,
  opening,
  isVisible,
}: PhoneCanvasProps) {
  const maxDpr = window.matchMedia(MOBILE_QUERY).matches ? MAX_DPR_MOBILE : MAX_DPR_DESKTOP;
  return (
    <Canvas
      className="phone-stage__canvas"
      // Solo dibuja cuando cambian las props (el progreso del scroll), no a 60 fps en reposo.
      frameloop="demand"
      dpr={[1, maxDpr]}
      camera={{ position: [0, 0, 3.7], fov: 35 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      aria-hidden="true"
    >
      <Suspense fallback={null}>
        <PhoneModel
          progress={progress}
          screens={screens}
          index={index}
          fan={fan}
          opening={opening}
          isVisible={isVisible}
        />
      </Suspense>
    </Canvas>
  );
}
