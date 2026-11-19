# Página de presentación y descarga de la app — diseño

> Fecha: 2026-11-19 · Estado: **borrador para aprobación del responsable**
> Rama: `docs/landing-pagina-descarga` · Bitácora: fila 99

## 1. Intención

Una página web pública que presente Street Repo y aloje, más adelante, la descarga e instalación
del APK de la app ciudadana.

- **Hoy** el público es el **jurado de la sustentación**. Debe sentir **asombro e impacto**, quedar
  enganchado de principio a fin y llevarse la impresión de que Street Repo **es y se siente como
  un producto hecho por una corporación**.
- **Después** el público serán los **ciudadanos de Pasto**: la misma página debe llevarlos a
  instalar la app, sin rehacerla.
- Referencia de tono y técnica: Moooi, «A Life Extraordinary»
  (https://www.moooi.com/en/a-life-extraordinary): recorrido cinematográfico guiado por el
  desplazamiento, video que avanza con el *scroll*, revelados y desvanecidos, tipografía editorial.

## 2. Objetivos, no objetivos y anti-objetivos

**Objetivos**
1. Un recorrido narrativo de principio a fin, guiado por el *scroll*, con escenas generadas con
   **Higgsfield** (imágenes y video) de calidad máxima: no se escatima en generación ni en tiempo.
2. Estilo **minimalista, inmersivo 3D y editorial**, con una identidad visual evolucionada solo
   para esta página (sección 5).
3. Un elemento **3D en tiempo real**: un teléfono que gira con el *scroll* y muestra **capturas
   reales** de la app.
4. Sección final de **descarga e instalación** preparada, con el enlace del APK como dato
   configurable (hoy «Próximamente»).
5. Desplegada en **Vercel**, fluida en un celular Android de gama media y en un portátil.

**No objetivos (quedan para después, por decisión del responsable)**
- Publicar el APK, firmarlo con llave propia y alojarlo (GitHub Releases u otro).
- Desplegar la API con HTTPS para que el APK funcione fuera del computador del responsable (HU-17).
- La condición de la decisión 71 (prueba de la supresión antes de abrir la app a terceros).
- Analítica, formularios, inicio de sesión, CMS, varios idiomas, iOS.

**Anti-objetivos (fracaso aunque «funcione»)**
- Que la página se trabe, tarde en cargar o salte frente al jurado.
- Que parezca una plantilla genérica.
- **Cifras o datos inventados** («+10.000 reportes», ciudades atendidas, testimonios): guía 0.2 y 16.
- Que una imagen generada se confunda con una foto de un daño real o con evidencia de campo
  (decisiones 85 y 90), o que se muestren pantallas de la app que no existen.
- Romper la CI existente o mezclar la página con el código de la app o del panel.

## 3. Restricciones

- **Stack:** React + TypeScript `strict`, como `admin-web`. Vercel es una herramienta nueva fuera
  de la tabla de la guía 3: se registra en la bitácora (fila 99) y se añade a `AGENTS.md`.
- **Repositorio:** carpeta nueva `landing/` en la raíz del monorrepo, con su propio
  `package.json`; proyecto de Vercel con *Root Directory* `landing/`.
- **Idioma:** español de Colombia; decimales con coma en la interfaz (guía 9.2).
- **Accesibilidad:** WCAG 2.2 AA (guía 10.3): contraste ≥ 4,5:1, foco visible, navegación por
  teclado, texto alternativo, `prefers-reduced-motion` respetado.
- **Seguridad:** cabeceras desde `vercel.json` (CSP, HSTS, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`); fuentes y medios servidos desde el propio dominio
  (sin peticiones a terceros); sin secretos.
- **Privacidad:** sin datos personales. Las capturas de la app se toman con los datos de
  demostración (`seed-demo`), nunca con los reportes reales del responsable.
- **Mapas:** si una captura muestra teselas de OpenStreetMap, lleva su atribución.
- **Trazabilidad:** no hay una historia de usuario de la tesis que cubra la página. Se registra
  como decisión del responsable y se anota en `docs/ajustes-tesis.md` por si la tesis debe
  mencionarla.

## 4. Enfoques considerados

| Enfoque | Qué es | A favor | En contra |
|---|---|---|---|
| A. Cine con el *scroll* | Videos de Higgsfield convertidos en secuencias de cuadros dibujadas en `<canvas>` según el desplazamiento (GSAP ScrollTrigger + Lenis) | Máxima calidad visual por esfuerzo; fluido en cualquier celular | El 3D es una ilusión: no se puede rotar ni tocar |
| B. 3D en tiempo real | Escena completa en React Three Fiber con modelos generados (`generate_3d`) | Interactividad genuina | Pesada, frágil en celulares modestos, más lenta de construir; los modelos generados lucen menos que un video |
| **C. Híbrido (elegido)** | A para el recorrido narrativo + **un** elemento 3D en tiempo real: el teléfono con capturas reales de la app | Asombro de los videos + credibilidad del producto real; el 3D en vivo queda acotado a una pieza optimizable | Dos técnicas que coordinar en la misma línea de tiempo |

**Elegido por el responsable: C** (2026-11-19). Motivo: impacto sin arriesgar que la página se
trabe, y mostrar la app verdadera pesa más ante el jurado que cualquier imagen generada.

## 5. Identidad visual de la página

El responsable autorizó evolucionar la identidad **solo en esta página** hacia un estilo
minimalista, inmersivo 3D y editorial, sin limitar el acento al ámbar. La app y el panel no
cambian.

### 5.1 Paleta (propuesta del asistente, con fundamento)

Fundamento: Labrecque y Milne (2012, *Journal of the Academy of Marketing Science*): el azul eleva
la percepción de **competencia y confianza** y es el color preferido por hombres y mujeres; los
tonos cálidos (rojo, naranja, amarillo) generan **excitación y atención**; el negro se asocia con
lo **moderno y sofisticado**. Elliot (2015, *Frontiers in Psychology*) advierte que los acentos
cálidos deben usarse con moderación para no generar ansiedad.

Cada acento tiene un papel en la historia, y coincide con los colores de estado de la app
(Evaluado azul, Reparado verde):

| Token | Valor | Papel |
|---|---|---|
| `--night` | `#0A0E13` | Fondo base: negro azulado, profundidad cinematográfica |
| `--ink` | `#1B2430` | Superficies y tarjetas (la tinta de la marca) |
| `--paper` | `#F5F3EE` | Texto principal sobre oscuro; secciones claras de respiro editorial |
| `--mist` | `#8A94A3` | Texto secundario sobre oscuro (≥ 4,5:1 sobre `--night`) |
| `--amber` | `#F5B800` | **El problema y la acción**: el daño, la alerta, el botón de descarga |
| `--signal` | `#4C8DFF` | **La inteligencia del sistema**: datos, priorización, la fórmula U |
| `--repair` | `#3DD68C` | **La solución**: el momento «Reparado» |

Regla: un solo acento dominante por escena; el ámbar se reserva para el problema y la llamada a
la acción.

### 5.2 Tipografía (propuesta del asistente)

- **Titulares editoriales:** una serif de alto contraste (candidata: *Instrument Serif*, licencia
  OFL) en tamaños muy grandes, para el tono de revista.
- **Etiquetas, cifras y marca:** *Archivo* 700/800, la de la marca.
- **Cuerpo:** *Manrope* 400–600, la de la marca.
- Fuentes autoalojadas (`woff2`, subconjunto latino), sin Google Fonts en tiempo de ejecución.

### 5.3 Marca: símbolo + logotipo (decidido por el responsable, opción B)

Street Repo no tenía logotipo (la app y el panel escriben el nombre en Archivo).

1. **Exploración:** propuestas de símbolo generadas con Higgsfield a partir de un brief (ideas de
   partida: punto de ubicación, grieta o bache estilizado, señal vial, la «S» y la «R»; geometría
   simple, legible a 24 px, funciona en un solo color).
2. **Elección:** el responsable elige una propuesta (o pide otra ronda).
3. **Vectorización:** el asistente redibuja la elegida como **SVG limpio** (no se usa la imagen
   generada como logo final) y compone el logotipo: símbolo + «Street Repo» con espaciado ajustado.
4. **Entregables:** versión horizontal y apilada, solo símbolo (favicon e ícono), en claro, oscuro
   y monocromo, con área de reserva y tamaño mínimo, en `landing/src/assets/brand/` y una hoja de
   uso breve en `landing/media/README.md`.
5. **Alcance:** la marca se usa en esta página. Llevarla a la app (ícono del lanzador) y al panel
   es una decisión posterior, con el protocolo 0.3.

### 5.4 Lenguaje visual

Mucho espacio negativo; una idea por pantalla; texto que entra por líneas o palabras con
máscara; transiciones por desvanecimiento, desenfoque y profundidad (*shadow vanishing*,
paralaje); grano fílmico sutil; iluminación cinematográfica en las escenas generadas.

## 6. Recorrido narrativo (guion)

La vida de un daño vial en Pasto, de principio a fin. Cada capítulo es una escena fijada
(*pinned*) que se recorre con el *scroll*.

| # | Capítulo | Qué se ve | Técnica | Acento |
|---|---|---|---|---|
| 0 | Apertura | Noche sobre Pasto y el volcán Galeras; aparece «Street Repo» | Secuencia de cuadros + revelado tipográfico | — |
| 1 | El problema | Una calle de Pasto; la cámara desciende hasta un bache bajo la lluvia | Secuencia de cuadros | Ámbar |
| 2 | Reportar | El teléfono 3D entra en escena y gira: foto, ubicación, severidad (capturas reales) | **3D en tiempo real** | Ámbar → azul |
| 3 | Priorizar | El reporte se vuelve datos: líneas de luz sobre la ciudad; la fórmula U = 0,5·S + 0,3·F + 0,2·P se construye | Secuencia de cuadros + tipografía | Azul |
| 4 | El panel | La captura real del panel (mapa de calor y ranking) en perspectiva | Imagen real en 3D CSS / paralaje | Azul |
| 5 | Reparado | La misma calle de la escena 1, ahora reparada, al amanecer | Secuencia de cuadros | Verde |
| 6 | Descarga | Llamada final, botón, QR, pasos de instalación y requisitos | Sección estática editorial | Ámbar |
| — | Pie | Proyecto de grado, Ingeniería de Software, UCC Pasto; aviso de medios generados con IA; atribución de OSM si aplica | Estático | — |

**Reglas del contenido:**
- Las cifras que aparezcan son **solo** las reales y verificables del proyecto (p. ej. la fórmula,
  los radios de 25 m y 500 m). Ninguna métrica de uso inventada.
- Las escenas generadas son **ilustración**; el pie lo dice con discreción («Imágenes y videos
  ilustrativos generados con IA»).
- Lo que se muestre de la app y del panel son **capturas reales** con datos de demostración.

## 7. Arquitectura técnica

### 7.1 Proyecto `landing/`

- **Vite + React 18 + TypeScript `strict`** (mismas herramientas que `admin-web`: `eslint`,
  `prettier`, `vitest` + Testing Library). Página única, salida estática.
- **Desplazamiento y animación:** GSAP + ScrollTrigger (línea de tiempo por capítulo) y Lenis
  (*scroll* suave, desactivado con `prefers-reduced-motion`).
- **Secuencias de cuadros:** componente `FrameSequence` que dibuja en `<canvas>` el cuadro
  correspondiente al progreso del capítulo; precarga progresiva (primero el cuadro 0 y uno de
  cada N, luego el resto) y solo del capítulo actual y el siguiente.
- **Teléfono 3D:** `@react-three/fiber` + `@react-three/drei`; modelo del teléfono construido en
  código (caja redondeada + pantalla) o generado, con la textura de la pantalla cambiando entre
  capturas reales; se monta solo cuando el capítulo 2 está cerca y se desmonta al salir.
- **Datos configurables:** `src/config/release.ts` con versión del APK, URL, tamaño, SHA-256 y
  requisitos; vacío hoy → la sección 6 muestra «Próximamente».

### 7.2 Medios

- **Generación (Higgsfield, plan Ultra):** por cada escena, primero **cuadros clave** (imágenes)
  con una biblia de estilo común (paleta, luz, lente, grano), que **el responsable aprueba**;
  después, video a partir de esos cuadros (imagen → video) y, si hace falta, reescalado. Se
  elige el mejor modelo disponible con `models_explore` al momento de generar.
- **Postproceso (ffmpeg, local):** video → secuencia de cuadros en **WebP/AVIF** a dos
  resoluciones (escritorio ~1920 px, móvil ~1080 px), 24–30 cuadros por segundo de escena.
- **Presupuesto de peso (decisión del asistente):** ≤ 6 MB antes del primer capítulo interactivo;
  ≤ 45 MB en total para escritorio y ≤ 25 MB para móvil, cargados por capítulo.
- **Dónde viven:** los medios optimizados en `landing/public/media/` (versionados); los
  originales de Higgsfield **fuera del repositorio** (carpeta local del responsable y el
  historial de Higgsfield), con un `landing/media/README.md` que lista cada pieza, su prompt,
  modelo y fecha, para que sean reproducibles.

### 7.3 Respaldo sin movimiento

Con `prefers-reduced-motion` (o si el canvas o WebGL fallan): cada capítulo muestra su cuadro
clave como imagen fija con desvanecidos simples; el teléfono se muestra como imagen. El contenido
y la descarga siguen completos.

### 7.4 Despliegue

- Proyecto de Vercel conectado al repositorio de GitHub, *Root Directory* `landing/`, salida
  `dist/`. Cada rama genera una vista previa; `main` publica producción.
- `vercel.json` con cabeceras de seguridad y caché larga (`immutable`) para `media/` y los
  recursos con *hash*.
- Dominio: el `*.vercel.app` por defecto; uno propio queda a decisión posterior.

### 7.5 Calidad

- CI: un trabajo nuevo `landing` en `.github/workflows/ci.yml` (lint, `tsc --noEmit`, `vitest`,
  `vite build`), solo cuando cambia `landing/`.
- Pruebas unitarias de la lógica: cálculo de cuadro según progreso, plan de precarga, configuración
  de la versión («Próximamente» vs. enlace), respaldo sin movimiento.
- Metas: Lighthouse ≥ 90 en accesibilidad y buenas prácticas; LCP < 2,5 s en 4G simulado (el LCP
  es el cuadro inicial de la apertura); 60 fps en escritorio y sin saltos visibles en un Android
  de gama media (prueba en el celular del responsable).

## 8. Qué decidió el responsable

- Construir primero la página; el APK y lo que necesita para funcionar, después.
- Público: jurado hoy, ciudadanos después; sensación de asombro, impacto y producto corporativo.
- Enfoque C (híbrido).
- Identidad evolucionada solo para la página: minimalista, inmersiva 3D y editorial, con más de un
  acento.
- Higgsfield para imágenes y videos, sin escatimar; despliegue en Vercel.
- Marca nueva con símbolo + logotipo (opción B), explorada con Higgsfield y elegida por él.

## 9. Decisiones del asistente (para revisión)

1. Carpeta `landing/` en el monorrepo, Vite + React + TS como el panel (no Next.js: no hace falta
   servidor y mantiene una sola forma de trabajar).
2. Paleta de la sección 5.1 y tipografía de la 5.2.
3. Guion de la sección 6 (la vida de un bache en Pasto).
4. Cuadros clave aprobados por el responsable antes de generar cada video.
5. Presupuesto de peso y medios optimizados versionados; originales fuera del repositorio.
6. Teléfono 3D construido en código, con capturas reales tomadas con `seed-demo`.
7. Sin analítica ni cookies.
8. Aviso discreto de medios generados con IA en el pie.
9. Los textos de la página los redacta el asistente y los revisa el responsable antes de publicar.
10. Las capturas reales de la app se toman en el emulador o el celular con `seed-demo`; las del
    panel pueden partir de `docs/capturas/objetivo-3/` si sirven en calidad.
11. Vincular el repositorio con Vercel lo hace el responsable con su cuenta (paso explícito del
    plan); el asistente prepara la configuración.

## 10. Lo que queda al constructor

Nombres internos de componentes, la duración exacta de cada capítulo, las curvas de animación,
el número de cuadros por escena dentro del presupuesto, los prompts concretos de Higgsfield (a
partir de la biblia de estilo) y el orden de las tareas del plan.
