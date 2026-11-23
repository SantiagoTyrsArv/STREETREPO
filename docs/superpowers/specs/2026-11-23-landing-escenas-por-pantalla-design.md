# Página de presentación: escenas por pantalla y portada prerenderizada

Fecha: 2026-11-23 · Estado: **aprobado por el responsable el 2026-11-23** (revisado por un constructor; sus 4 preguntas se resolvieron en 4.1, 4.3 y 5) · Rama sugerida: `feat/landing-escenas-por-pantalla`
Fuentes: pedido del responsable (2026-11-23), propuesta de la fila 124 de la bitácora (prerenderizar
la portada, aprobada), diseños `2026-11-19-landing-descarga-apk-design.md` y
`2026-11-20-landing-textos-reportar-video-design.md`.

## 1. Intención

Hoy la página pide demasiado scroll. Cada capítulo queda fijo durante 2,5 a 4 pantallas, y lo que
pasa dentro (el video de la escena, los textos, el teléfono, la fórmula, el panel) solo avanza
mientras se sigue bajando. En total son unas 20 pantallas (unos 20 000 px en el celular). El
responsable quiere un recorrido más limpio: **al llegar a una sección, esta se reproduce sola**, y un
gesto corto lleva a la siguiente.

Además se aplica la propuesta aprobada de la fila 124: **prerenderizar la portada** para que el
elemento LCP (el texto «STREETREPO» de la máscara) se pinte sin esperar al JavaScript. Hoy el LCP es
de 3,1 s con 4G lento y CPU ×4; la meta del diseño es < 2,5 s.

## 2. Metas, no metas y anti-metas

**Metas**
- Cada capítulo ocupa **una pantalla** (`100svh`). La página total queda en unas 9 pantallas.
- Al entrar en un capítulo, su animación corre **sola, en el tiempo** (no con el scroll) y queda en
  su estado final.
- **Imán suave:** al soltar el scroll cerca de un capítulo, la página se acomoda en él (opción 1,
  elegida por el responsable).
- **Portada prerenderizada:** el HTML servido ya contiene la portada (y el resto de la página), y
  React la hidrata. LCP < 2,5 s en la misma medición (Chrome DevTools, «Slow 4G», CPU ×4, móvil
  412×915, sin caché, sobre la vista previa o producción).
- Se conservan: Lighthouse móvil ≥ 90 en accesibilidad y buenas prácticas, el presupuesto de peso
  de la CI, la barra de capítulos con sus anclas y el modo de movimiento reducido.

**No metas**
- Cambiar textos, escenas, capturas, colores o el orden de los capítulos.
- La entrega 2 («Reportar» como video real de la app); queda para después.
- Reducir GSAP o cambiar de librería.

**Anti-metas** (sería un fracaso aunque funcione)
- **Secuestrar el scroll:** que un gesto obligue a saltar exactamente una sección, que no se pueda
  bajar rápido a «Descarga» o que el teclado y el lector de pantalla queden atrapados. El imán es
  de **proximidad**, no obligatorio.
- Animaciones que se repiten en bucle o que tapan el texto mientras se lee.
- Contenido que solo existe con JavaScript: con el JS bloqueado o lento debe verse el texto de cada
  capítulo (el prerenderizado lo garantiza).
- Un salto visible cuando React hidrata la portada prerenderizada (parpadeo o desplazamiento: CLS > 0,1).

## 3. Enfoques considerados (elegido por el responsable: 1)

| Enfoque | Qué es | A favor | En contra |
|---|---|---|---|
| **1. Una pantalla por capítulo, con imán (elegido)** | Cada capítulo mide una pantalla; al entrar, su animación corre sola; imán de proximidad al soltar | Mucho menos scroll y sensación de «escenas»; scroll libre, accesible | Las escenas dejan de responder al dedo; hay que precargar cuadros antes de reproducir |
| 2. Lo mismo sin imán | Igual, sin acomodar al soltar | Más simple | Se puede quedar a medio camino entre dos escenas; menos limpio |
| 3. Diapositivas | Cada gesto salta una sección exacta | Lo más limpio a la vista | Secuestra el scroll; rígido en el celular; choca con el lector de pantalla y con bajar rápido |

## 4. Comportamiento

### 4.1 Disparo y reproducción
- Un capítulo **se dispara** cuando entra lo suficiente en la ventana (decisión del asistente:
  cuando su borde superior pasa del 60 % del alto de la ventana, es decir, ya ocupa ~40 %). La
  portada se dispara al cargar.
- Al dispararse, un progreso de 0 a 1 avanza **en el tiempo** con una curva suave (`power2.out` o
  similar), durante la duración del capítulo. Los componentes hijos siguen recibiendo `progress`
  igual que hoy, así que no cambian sus fórmulas internas.
- Duraciones (decisión del asistente, ajustables en una constante por capítulo): Portada 2,5 s ·
  Problema 3 s · Reportar 6 s (tres pasos de 2 s: foto, ubicación, severidad) · Priorizar 3,5 s ·
  Gestionar 2,5 s · Reparado 3 s.
- **Disparo en cualquier dirección:** un capítulo se reproduce la primera vez que ocupa ~40 % de la
  ventana, se llegue bajando, subiendo o tras un ancla. Los capítulos por los que se salta con un
  ancla (sin quedar visibles) no se disparan; se reproducen cuando se llega a ellos.
- **Sin desvanecido final:** hoy, entre 0,9 y 1 la escena se desenfoca y el texto se apaga
  (`VANISH_FROM` en `SequenceChapter.tsx`). Con la reproducción en el tiempo eso dejaría cada
  capítulo en blanco, así que se quita: el estado final es la escena en su último cuadro con el
  texto visible. El cambio de capítulo lo da el scroll (decisión del asistente).
- **Una vez por carga:** al volver a un capítulo ya reproducido, se ve en su estado final, sin
  repetir (decisión del asistente: repetir al subir y bajar cansa y distrae).
- La calculadora «Pruébalo» y la Descarga no tienen animación ligada al scroll; solo se ajusta su
  alto si hace falta.

### 4.2 Secuencias de cuadros (videos de las escenas)
- `FrameSequence` sigue dibujando el cuadro que corresponde al `progress`. Como ahora el progreso
  avanza solo, la escena **espera a tener sus cuadros**: se precargan los del capítulo siguiente
  cuando el actual se dispara, y la reproducción de un capítulo empieza cuando sus cuadros están
  listos (o cuando están listos los necesarios para no saltarse más de unos pocos). Mientras tanto
  se ve `key.webp`.
- Si los cuadros no llegan en un tiempo razonable (red lenta), la escena se queda en su cuadro final
  o en `key.webp` y el texto se muestra igual. El texto nunca espera al video.

### 4.3 Alto de los capítulos
Cada capítulo mide una pantalla (`100svh`) y su contenido se ajusta para caber en ella.
**«Pruébalo» se compacta para caber en una pantalla** (decisión del responsable: ajustarla al imán
en lugar de quitarla). Medida el 2026-11-23 en 412×915: 1.101 px (introducción 184 + panel 615 +
márgenes). Se reducen los márgenes, las opciones de severidad van en una fila y el bloque del
resultado se compacta, hasta caber en 412×915 y en escritorio. En celulares con menos de ~700 px de
alto útil puede pasarse un poco: ahí el imán la acomoda por su borde superior y el resto se recorre
con scroll normal. La Descarga ya cabe (661 px en 412×915). Todos los capítulos, incluidas
«Pruébalo» y la Descarga, son puntos de imán. La meta de «unas 9 pantallas» es aproximada.

### 4.4 Imán
- Imán de **proximidad** con el paquete de snap de Lenis (`lenis/snap`, ya incluido en `lenis`
  1.3.27; no es una dependencia nueva). Puntos de imán: el inicio de cada capítulo.
- Solo actúa al soltar el scroll y cerca de un punto. No actúa con la navegación por anclas (la
  barra de capítulos y «Saltar a la descarga» siguen saltando de inmediato), ni con movimiento
  reducido (sin Lenis, scroll nativo).

### 4.5 Movimiento reducido
Sin cambios de criterio: con `prefers-reduced-motion` no hay Lenis, ni imán, ni reproducción; cada
capítulo muestra su estado final (`still`), como hoy.

### 4.6 Barra de capítulos
Sigue marcando el capítulo visible (la línea media de la ventana). Con capítulos de una pantalla, la
marca cambia al ritmo del imán.

## 5. Portada prerenderizada

- En la compilación se renderiza `<App />` a HTML (`react-dom/server`) y se inserta en
  `index.html`; `main.tsx` usa `hydrateRoot`. Se prerenderiza la página completa, no solo la
  portada: así todo el texto existe sin JavaScript y el SEO no depende del JS.
- **El HTML muestra el estado inicial** (`progress = 0`), el mismo del primer render del cliente,
  para hidratar sin errores. En ese estado ya se ve la portada con la máscara «STREETREPO» (el LCP).
  Para que **sin JavaScript** se lea el texto de todos los capítulos, `index.html` lleva un
  `<noscript><style>` que fuerza el estado final del texto (permitido por la CSP actual,
  `style-src 'unsafe-inline'`). Con JS lento, el texto de los capítulos aparece al hidratar
  (decisión del asistente).
- El estado inicial del HTML debe coincidir con el primer render del cliente (sin errores de
  hidratación en la consola). Lo que depende del navegador (`window`, `matchMedia`, medidas,
  lienzos, WebGL, `sessionStorage`) se lee en efectos, no durante el render.
- La portada prerenderizada se ve ya en su primer cuadro (`key.webp` de la portada y la máscara
  con «STREETREPO»), y la animación de la portada arranca cuando React hidrata, sin salto.
- Se mantiene la CSP actual (`script-src 'self'`): el prerenderizado no añade scripts en línea.
  Si hiciera falta pasar datos al cliente, se pasan sin `<script>` en línea.
- El paso de prerenderizado corre en `npm run build` (Vercel y la CI lo ejecutan sin cambios de
  configuración).

## 6. Pruebas y verificación

- Pruebas unitarias del nuevo mecanismo de reproducción: se dispara una sola vez, el progreso va
  de 0 a 1 en la duración dada, con movimiento reducido devuelve el estado final, espera a los
  cuadros y tiene un tope de espera.
- Prueba de que el prerenderizado produce HTML con los títulos de todos los capítulos y que
  `index.html` compilado los contiene.
- Las pruebas existentes que dependen del progreso por scroll se adaptan; el número total puede
  cambiar y se informa.
- Verificación manual (Chrome DevTools): alto total de la página ≈ 9 pantallas; sin errores de
  hidratación ni de CSP; LCP < 2,5 s con la medición de la sección 2; CLS < 0,1; Lighthouse móvil
  ≥ 90 en accesibilidad y buenas prácticas; recorrido con teclado (Tab, anclas, «Saltar a la
  descarga»).
- Presupuesto de peso de la CI sin cambios de límites.

## 7. Restricciones

- Guía `AGENTS.md`: rama propia, commits detallados, pruebas en cada cambio, bitácora y Linear
  (ARE-46).
- Sin dependencias nuevas salvo que el prerenderizado lo exija (decisión menor documentada en la
  bitácora si pasa).
- Español de Colombia en los textos; tokens de diseño existentes.

## 8. Lo que queda al constructor

Cómo se organiza el nuevo hook de reproducción (sustituto de `useChapterProgress` con la misma
salida o una variante), la técnica exacta de prerenderizado (script con `vite build --ssr` o
plugin), el umbral exacto de disparo y el tope de espera de los cuadros dentro de lo anterior,
la fuerza del imán y la organización de las pruebas.
