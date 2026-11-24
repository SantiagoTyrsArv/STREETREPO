# Revisión de accesibilidad — fase 8

> 2026-11-24 · guía, sección 10.3 (WCAG 2.2 AA) · bitácora, filas 143 a 145

## Alcance y herramientas

| Cliente | Herramienta | Qué revisa | Dónde |
|---|---|---|---|
| Panel web | axe-core 4.14 con Playwright, reglas WCAG 2.0, 2.1 y 2.2 en niveles A y AA | 11 pantallas contra la API y la base reales del stack de E2E | `admin-web/e2e/accesibilidad.spec.ts` |
| App móvil | Pautas de `flutter_test`: área táctil (`iOSTapTargetGuideline`) y etiqueta de lo tocable (`labeledTapTargetGuideline`) | 18 estados de pantalla del flujo ciudadano | grupos «Pautas de accesibilidad (fase 8)» en las pruebas de cada función; ayuda en `mobile/test/support/accessibility.dart` |
| App móvil | Cálculo exacto del contraste WCAG (1.4.3) sobre los tokens de color | 21 pares de texto y fondo de la guía 10.1 | `mobile/test/core/theme/token_contrast_test.dart` |

Ya existían, y siguen: las reglas `jsx-a11y` de ESLint en el panel; las pruebas de la app con el
texto del sistema al doble; chips con texto y no solo color; atribución de OSM en los mapas.

## Panel web

**0 hallazgos de cualquier gravedad** en las 11 pantallas (axe, 2026-11-24):

| Pantalla | Reglas cumplidas |
|---|---|
| Inicio de sesión | 14 |
| Inicio de sesión con el error de credenciales | 18 |
| Priorización (mapa de calor y ranking) | 30 |
| Detalle y estado | 28 |
| Pesos del modelo | 26 |
| Pesos del modelo con el error de suma ≠ 1,00 | 29 |
| Comparación · Zonas | 27 |
| Comparación · Rondas (ronda abierta) | 26 |
| Comparación · Resultados (ronda cerrada) | 26 |
| Mis evaluaciones (evaluador) | 21 |
| Vista a ciegas (evaluador) | 25 |

La prueba falla con hallazgos serios o críticos; se comprobó insertando una imagen sin texto
alternativo (`image-alt`). Se repite con `infra/scripts/e2e-panel.sh e2e/accesibilidad.spec.ts`;
con `A11Y_LIST=1` imprime el detalle por pantalla.

## App móvil

**Pantallas revisadas** (pautas de área táctil y etiqueta): Bienvenida, Registro, Política de
datos, Iniciar sesión con el aviso de error, Mis reportes (con reportes y vacío), Detalle del
reporte, Perfil y privacidad, Editar datos y la hoja de contraseña, Eliminar mis datos y la
constancia, Mapa y la ficha abierta, Nuevo reporte · Foto y ubicación, Severidad, Posible
duplicado y Reporte enviado.

**Hallazgo corregido:** la superficie del **mapa** se podía tocar y arrastrar, pero el lector
de pantalla la anunciaba sin nombre. Ahora se anuncia «Mapa de reportes. Toca un marcador para
ver su ficha» (`report_map_screen.dart`); cada marcador ya tenía su propia etiqueta.

**Contraste de los tokens:** 20 de 21 pares de texto cumplen 4,5:1 (por ejemplo, tinta sobre
papel 14,1:1; texto secundario sobre papel 5,3:1; chips de estado entre 6,3:1 y 7,8:1). El título
grande de la constancia (40 px) cumple 3:1. **No cumple:** el texto del chip de severidad
**«Media»**: 3,93:1 sobre una tarjeta blanca (3,56:1 sobre papel), y «Baja» queda en 4,19:1 si el
chip va sobre papel. Cambiarlo es cambiar los tokens de la guía 10.1: va como **propuesta 144**
(abajo) y su prueba queda omitida con `TODO(propuesta-144)`.

### Decisiones sobre las herramientas

- **Área táctil de 44 y no de 48.** La pauta de Android pide 48 dp; el diseño aprobado y la guía
  10.3 fijan 44 px, que es lo que pide iOS y bastante más que el mínimo de WCAG 2.2 AA (24 px,
  criterio 2.5.8). Las pestañas «Iniciar sesión» y «Registrarme» miden 44 de alto. Se aplica la pauta de iOS; subir a 48 sería cambiar el diseño y no se propone
  porque no hay incumplimiento de WCAG AA.
- **Contraste exacto en vez de la pauta de Flutter.** `textContrastGuideline` mide sobre una
  captura y, en la pantalla Política de datos, comparó el blanco de las tarjetas con su borde
  (1,34:1) en vez del texto (9,4:1). Por esos falsos positivos se calcula el contraste sobre los
  tokens con la fórmula de WCAG.

## Propuesta 144

```
Propuesta: contraste del chip de severidad «Media»
Dónde: guía 10.1 (tokens) y diseño en Figma; app (SeverityChip). El panel cumple: su chip va
  sobre blanco con borde y «Media» da 4,58:1
Situación actual: el texto del chip usa el color de severidad (#B45F06) sobre ese mismo color al
  12 %: 3,93:1 sobre tarjeta blanca y 3,56:1 sobre papel. WCAG 2.2 AA (1.4.3) pide 4,5:1 para
  texto de ese tamaño. «Baja» (#2B6CB0) llega a 4,19:1 sobre papel.
Mejora sugerida: un tono de texto más oscuro solo para el texto del chip, como ya hacen los chips
  de estado (p. ej. #8A4A05 para «Media»: 5,88:1 sobre tarjeta y 5,32:1 sobre papel; el color de
  severidad se mantiene en el punto y el fondo). Ajustar también el texto de «Baja» si el chip va sobre papel.
Justificación: WCAG 2.2 AA 1.4.3; la guía 10.3 pide 4,5:1 en texto; los chips de estado del
  mismo diseño ya separan el color del texto (p. ej. Priorizado #7A4E00 sobre #FDF0C4).
Impacto: uno o dos tokens nuevos y un componente de la app; sin cambios de API; la tesis no
  menciona estos valores. Esfuerzo bajo; hay que actualizar el Figma.
Recomendación: aplicar
```

## Pendiente para el responsable

Una revisión corta con **TalkBack** en su celular, que las pruebas automáticas no reemplazan:

1. Registro: cada campo se anuncia con su nombre y el error de la contraseña se lee al aparecer.
2. Nuevo reporte: los botones de foto y ubicación, la severidad elegida y «Enviar reporte».
3. Mapa: tocar un marcador, oír la ficha y llegar a «Confirmar este daño».
4. Tamaño de letra del sistema al máximo en esas tres pantallas: nada se corta.
