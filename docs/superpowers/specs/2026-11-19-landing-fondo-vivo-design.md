# Página de presentación: fondo vivo y microinteracciones — diseño

Fecha: 2026-11-19 · Proyecto: `landing/` (decisión 99, Linear ARE-46) · Estado: propuesta para aprobar

## 1. Intención

El responsable siente que la página «se queda quieta o apagada» cuando se deja de hacer *scroll*:
hoy todo responde solo al *scroll* y, al detenerse, las escenas se congelan en un cuadro y las
secciones lisas son casi negras. Quiere que la página se sienta **viva en general**, con un fondo
en movimiento interactivo como el de stripe.com y microinteracciones que respondan al **mouse** en
el portátil y al **tacto** en el celular.

Público: el jurado de la sustentación (diseño de la página, sección 1).

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**
1. Que ninguna pantalla quede totalmente quieta en reposo: siempre hay un movimiento lento y sutil.
2. Un fondo de degradado ondulante estilo Stripe, que reacciona al puntero o al dedo.
3. Microinteracciones con el mouse y con el tacto en las piezas principales.

**No objetivos**
- Regenerar o cambiar las escenas aprobadas (fila 107) ni sus secuencias.
- Giroscopio del celular (en iOS pide permiso y en Android no aporta lo bastante para el costo).
- Sonido, cursores personalizados, partículas 3D.

**Anti-objetivos (fracaso aunque «funcione»)**
- Que la página se trabe o baje de fluidez en un Android de gama media o en el portátil.
- Que el movimiento distraiga del texto o le quite contraste.
- Que se vea como una plantilla genérica de «degradado de startup».
- Que alguien con movimiento reducido vea animaciones.

## 3. Restricciones

- Paleta y regla de acentos del diseño (sección 5.1): `--night` de base; un acento dominante por
  escena: ámbar (problema y acción), azul `--signal` (priorizar y panel), verde `--repair` (reparado).
- Ya hay un elemento WebGL en vivo (el teléfono 3D, three.js). El fondo no debe sumar otra
  instancia de three.js ni otro bucle pesado.
- `prefers-reduced-motion: reduce`: todo quieto (fondo en un cuadro fijo, sin paralaje ni imán).
- Accesibilidad: el contraste del texto se mantiene ≥ 4,5:1; nada se comunica solo con movimiento.
- Sin dependencias nuevas salvo que hagan falta (decisión menor documentada).
- Lighthouse móvil sigue en 100 en accesibilidad, buenas prácticas y SEO.

## 4. Enfoques considerados

| Enfoque | Qué es | A favor | En contra |
|---|---|---|---|
| **A. Capa ambiental + microinteracciones (elegido por el responsable)** | Degradado WebGL fijo detrás de toda la página que cambia de color por capítulo y se curva hacia el puntero; las escenas «respiran» y tienen paralaje; imán, inclinación y onda al tocar | Ataca la quietud en todas las secciones; no toca las tomas aprobadas; costo acotado (un *shader* a baja resolución) | Es la opción con más piezas |
| B. Escenas que se mueven solas | En reposo, la secuencia va y vuelve unos cuadros alrededor del actual | Sin descargas nuevas | Las tomas son movimientos de cámara: el vaivén se lee como temblor |
| C. Partículas 3D que siguen el cursor | Campo de puntos con three.js | Llamativo | Más pesado en gama media; se ve genérico |

## 5. Diseño

### 5.1 Fondo ambiental (`AmbientBackground`)

- Un `<canvas>` fijo (`position: fixed; inset: 0`) detrás de `<main>` (por debajo del contenido y
  del grano), con un *shader* de fragmento propio en **WebGL puro** (sin three.js): ruido suave en
  movimiento lento que mezcla 3–4 colores en bandas diagonales, como el degradado de Stripe pero
  con la paleta nocturna de la página (mucho `--night`, acentos con poca saturación).
- **Color por capítulo:** la paleta objetivo cambia según la sección visible y se interpola en
  ~1 s: Apertura/Problema/Reportar → ámbar; Priorizar/Panel → azul; Reparado → verde;
  Descarga → ámbar. Los colores se toman de `tokens.css`.
- **Interacción:** el degradado se deforma con suavidad hacia el puntero (mouse) o hacia el dedo
  mientras toca; al soltar, vuelve despacio. Un toque o clic deja una **onda** que se expande y se
  desvanece en ~1,2 s desde ese punto.
- **Dónde se ve:** en las secciones sin video. Reportar, El panel, Descarga y el pie pasan de fondo
  opaco a translúcido para que el degradado se vea; sus resplandores radiales actuales se
  conservan encima. Los capítulos de video siguen opacos (el fondo no compite con las escenas).
- **Costo:** se dibuja a ~⅓ de la resolución de la pantalla y se escala con CSS (el degradado no
  tiene detalle fino); se pausa cuando la pestaña no está visible y cuando ninguna sección sin
  video está en pantalla. Meta: < 2 ms por cuadro en un Android de gama media.
- **Respaldo:** sin WebGL, o con movimiento reducido, se ven los degradados CSS actuales
  (con movimiento reducido, el *canvas* dibuja un solo cuadro fijo o no se monta).

### 5.2 Escenas de video vivas en reposo

- Sobre `.chapter__scene`: una «respiración» muy lenta (escala 1,03 ↔ 1,06 en un ciclo de
  ~14 s) y **paralaje** hacia el puntero o el dedo (desplazamiento máximo ~1,5 % del ancho, con
  suavizado). La escala mínima evita que se vean los bordes.
- El texto del capítulo no se mueve (legibilidad).

### 5.3 Microinteracciones

| Pieza | Mouse (`hover: hover`) | Tacto |
|---|---|---|
| Botones «Descargar» (encabezado y sección) | **Imán**: se acercan al cursor hasta ~8 px dentro de un radio de ~80 px; brillo al pasar | Al presionar: se hunden levemente (escala 0,97) |
| Teléfono 3D (Reportar) | Se inclina hacia el cursor (± ~0,12 rad), sumado al giro del *scroll* | Se inclina hacia el dedo mientras toca; vuelve al soltar |
| Captura del panel | Inclinación 3D sutil hacia el cursor (± 4°) con reflejo que se desplaza | Igual, mientras toca |
| Fondo ambiental | Se curva hacia el cursor | Se curva hacia el dedo; onda al tocar |
| Escenas de video | Paralaje hacia el cursor | Paralaje hacia el dedo mientras toca |

Ninguna microinteracción cambia el contenido ni la navegación; el foco del teclado y los estados
actuales de los botones se mantienen.

### 5.4 Arquitectura

- `src/interaction/pointer.ts`: **un solo** escuchador global de `pointermove`/`pointerdown`/
  `pointerup` que guarda la posición normalizada (−1…1) y si hay un toque activo; las piezas leen
  ese estado y lo suavizan en su propio `requestAnimationFrame` (sin re-renderizar React).
- Funciones puras probables: interpolación de paletas, suavizado (*damping*), desplazamiento del
  imán, inclinación a partir de la posición.
- Todo se apaga con `useReducedMotion` (ya existe).

### 5.5 Pruebas y verificación

- Unitarias (vitest): funciones puras; el escuchador del puntero (normalización, toque activo);
  con movimiento reducido no se monta el *canvas* ni se aplican transformaciones; sin WebGL se
  usa el respaldo.
- Manual: escritorio y celular emulado; fluidez revisada con el panel de rendimiento de Chrome
  (CPU ×4); Lighthouse móvil; prueba en el celular del responsable al cerrar (tarea 9).

## 6. Lo que decidió el responsable

- Enfoque A (2026-11-19).
- Que la página se sienta viva en general, no solo en un momento.

## 7. Decisiones del asistente (para revisión)

- *Shader* en WebGL puro en lugar de three.js o una librería de degradados: un solo bucle ligero.
- Color por capítulo según el acento del diseño; el fondo solo se ve en las secciones sin video.
- Sin giroscopio; el tacto se resuelve con la posición del dedo mientras toca.
- Valores numéricos (radios, ángulos, escalas, tiempos) como punto de partida, ajustables a ojo.

## 8. Lo que queda al constructor

- El *shader* exacto (ruido, bandas, mezcla) dentro de la paleta y las metas de costo.
- Cómo detectar la sección visible (IntersectionObserver o los ScrollTrigger existentes).
- La transparencia exacta de cada sección para mantener el contraste del texto.
