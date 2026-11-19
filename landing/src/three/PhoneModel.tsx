import { Environment, Lightformer, RoundedBox, useTexture } from "@react-three/drei";
import { useMemo } from "react";
import { SRGBColorSpace, type Texture } from "three";
import type { PhoneScreen } from "./types";

/** Proporción de las capturas (1080 × 2264). */
const SCREEN_ASPECT = 1080 / 2264;
const SCREEN_WIDTH = 0.92;
const SCREEN_HEIGHT = SCREEN_WIDTH / SCREEN_ASPECT;
const BEZEL = 0.065;
const BODY = { width: SCREEN_WIDTH + BEZEL * 2, height: SCREEN_HEIGHT + BEZEL * 2, depth: 0.1 };
/** Color de la carcasa: el token --ink (#1B2430). */
const INK = "#1b2430";

function easeOutCubic(t: number): number {
  return 1 - (1 - Math.min(1, Math.max(0, t))) ** 3;
}

interface PhoneModelProps {
  progress: number;
  screens: readonly PhoneScreen[];
  index: number;
}

/** Teléfono hecho en código (sin modelos externos) con la captura como textura de la pantalla. */
export function PhoneModel({ progress, screens, index }: PhoneModelProps) {
  const textures = useTexture(screens.map((s) => s.src)) as Texture[];
  useMemo(() => {
    for (const texture of textures) {
      texture.colorSpace = SRGBColorSpace;
      texture.anisotropy = 4;
    }
  }, [textures]);

  // Entra desde abajo y girado; a mitad del recorrido queda casi de frente y sigue girando suave.
  const enter = easeOutCubic(progress / 0.18);
  const rotationY = -0.75 + enter * 0.6 + progress * 0.35;
  const rotationX = 0.18 - enter * 0.12;
  const positionY = -2.6 * (1 - enter);

  return (
    <>
      <ambientLight intensity={0.35} />
      <directionalLight position={[2.5, 3, 4]} intensity={1.6} />
      {/* Reflejos locales: sin mapas HDR descargados de terceros. */}
      <Environment resolution={128}>
        <Lightformer form="rect" intensity={2.2} position={[0, 2, 3]} scale={[4, 1, 1]} />
        <Lightformer
          form="rect"
          intensity={1.4}
          color="#4c8dff"
          position={[-3, 0, 1]}
          scale={[1, 4, 1]}
        />
      </Environment>
      <group rotation={[rotationX, rotationY, 0]} position={[0, positionY, 0]}>
        <RoundedBox
          args={[BODY.width, BODY.height, BODY.depth]}
          radius={0.11}
          smoothness={6}
          creaseAngle={0.4}
        >
          <meshStandardMaterial color={INK} metalness={0.55} roughness={0.32} />
        </RoundedBox>
        <mesh position={[0, 0, BODY.depth / 2 + 0.001]}>
          <planeGeometry args={[SCREEN_WIDTH, SCREEN_HEIGHT]} />
          <meshBasicMaterial map={textures[index]} toneMapped={false} />
        </mesh>
      </group>
    </>
  );
}
