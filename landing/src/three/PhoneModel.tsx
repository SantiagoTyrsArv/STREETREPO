import { Environment, Lightformer, RoundedBox, useTexture } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import gsap from "gsap";
import { useEffect, useMemo, useRef } from "react";
import { SRGBColorSpace, type Group, type Texture } from "three";
import { damp, tiltFromPointer } from "../interaction/motion";
import { pointer } from "../interaction/pointer";
import type { PhoneScreen } from "./types";

/** Proporción de las capturas (1080 × 2264). */
const SCREEN_ASPECT = 1080 / 2264;
const SCREEN_WIDTH = 0.92;
const SCREEN_HEIGHT = SCREEN_WIDTH / SCREEN_ASPECT;
const BEZEL = 0.065;
const BODY = { width: SCREEN_WIDTH + BEZEL * 2, height: SCREEN_HEIGHT + BEZEL * 2, depth: 0.1 };
/** Inclinación máxima hacia el puntero o el dedo (rad), sumada al giro del scroll. */
const PHONE_TILT = 0.12;
const TILT_LAMBDA = 5;
/** Por debajo de esta diferencia (rad) el teléfono se considera quieto y deja de pedir cuadros. */
const SETTLED = 1e-4;

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

  // Inclinación hacia el puntero. El lienzo dibuja «a demanda»: se piden cuadros solo mientras el
  // puntero se mueve o el teléfono aún no se asienta, así en reposo no gasta batería.
  const tiltRef = useRef<Group>(null);
  const invalidate = useThree((state) => state.invalidate);
  useEffect(() => {
    let last = "";
    const wake = () => {
      const now = `${pointer.active}:${pointer.x}:${pointer.y}`;
      if (now !== last) {
        last = now;
        invalidate();
      }
    };
    gsap.ticker.add(wake);
    return () => gsap.ticker.remove(wake);
  }, [invalidate]);
  useFrame((_state, delta) => {
    const group = tiltRef.current;
    if (!group) return;
    const goal = pointer.active
      ? tiltFromPointer(pointer.x, pointer.y, PHONE_TILT)
      : { rx: 0, ry: 0 };
    const dt = Math.min(delta, 0.1);
    group.rotation.x = damp(group.rotation.x, goal.rx, TILT_LAMBDA, dt);
    group.rotation.y = damp(group.rotation.y, goal.ry, TILT_LAMBDA, dt);
    const moving =
      Math.abs(group.rotation.x - goal.rx) > SETTLED ||
      Math.abs(group.rotation.y - goal.ry) > SETTLED;
    if (moving) invalidate();
  });

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
      <group ref={tiltRef}>
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
      </group>
    </>
  );
}
