/**
 * Shaders del fondo ambiental (GLSL ES 1.0, sirve en WebGL 1 y 2).
 *
 * Un triángulo que cubre la pantalla y, en el fragmento, un degradado de seda: ruido con
 * deformación de dominio que reparte cuatro colores en bandas diagonales anchas, con un brillo
 * que recorre las bandas. El puntero curva el campo como una lente blanda y deja una estela de
 * luz; un toque o clic abre una onda que se expande y se apaga.
 */

export const VERTEX_SOURCE = `
attribute vec2 a_position;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

export const FRAGMENT_SOURCE = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif

uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_pointer;   // -1..1, y hacia abajo (como el DOM)
uniform float u_strength; // 0..1: cuánto manda el puntero (más con gestos rápidos)
uniform vec3 u_ripple;    // x, y en -1..1; z = edad en s (negativa = sin onda)
uniform vec3 u_colors[4];
uniform float u_veil;     // 0..1: cuánto del degradado atraviesa el velo de noche

// Ruido de valor suave (barato en celulares de gama media).
float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 3; i++) {
    v += a * noise(p);
    p = p * 2.03 + vec2(1.7, 9.2);
    a *= 0.5;
  }
  return v;
}

vec2 toScene(vec2 ndc, float aspect) {
  return vec2(ndc.x * 0.5 * aspect, -ndc.y * 0.5);
}

void main() {
  float aspect = u_resolution.x / u_resolution.y;
  vec2 uv = gl_FragCoord.xy / u_resolution;
  vec2 p = vec2((uv.x - 0.5) * aspect, uv.y - 0.5);
  float t = u_time;

  // El puntero como lente blanda: atrae el campo hacia sí.
  vec2 ptr = toScene(u_pointer, aspect);
  vec2 d = p - ptr;
  float lens = exp(-dot(d, d) * 4.0) * u_strength;
  p -= d * lens * 0.35;

  // Onda de un toque: un anillo que empuja el campo hacia fuera y se apaga en 1,2 s.
  float ring = 0.0;
  if (u_ripple.z >= 0.0 && u_ripple.z < 1.2) {
    vec2 rp = toScene(u_ripple.xy, aspect);
    vec2 rd = p - rp;
    float dist = length(rd);
    float radius = u_ripple.z * 0.75;
    float fade = 1.0 - u_ripple.z / 1.2;
    ring = exp(-pow((dist - radius) * 12.0, 2.0)) * fade * fade;
    p += rd / max(dist, 0.001) * ring * 0.03;
  }

  // Seda: ruido con deformación de dominio que fluye en diagonal, muy despacio.
  vec2 q = vec2(fbm(p * 1.1 + vec2(0.0, t * 0.035)), fbm(p * 1.1 + vec2(5.2, 1.3) - t * 0.03));
  float n = fbm(p * 1.3 + q * 1.8 + vec2(t * 0.02, -t * 0.015));
  float band = (p.x * 0.55 + p.y * 0.95) + n * 1.1 + sin((p.x - p.y) * 2.2 + t * 0.12) * 0.12;
  float v = band * 0.9 + 0.55;

  // La luz viene del lado de los visuales: el texto va a la izquierda en pantallas anchas y
  // arriba en el celular, así que esa zona queda en penumbra y conserva el contraste.
  float side = aspect >= 1.0 ? smoothstep(0.5, 0.95, uv.x) : smoothstep(0.45, 0.05, uv.y);
  float light = 0.02 + 0.98 * side;

  // Mucha noche y tinta; el acento solo en las crestas más altas.
  vec3 col = u_colors[0];
  col = mix(col, u_colors[1], smoothstep(0.1, 0.65, v));
  col = mix(col, u_colors[2], smoothstep(0.6, 1.0, v) * 0.9 * light);
  col = mix(col, u_colors[3], smoothstep(1.05, 1.4, v) * 0.7 * light);

  // Cintas de luz que recorren las bandas, como reflejos sobre seda (el sello del fondo).
  float sheen = pow(1.0 - abs(sin(band * 3.14159 * 1.6 - t * 0.25)), 14.0);
  float ribbon = smoothstep(0.35, 1.1, v);
  col += u_colors[3] * sheen * ribbon * 0.32 * light;

  // Viñeta: los bordes se hunden en la noche.
  float vignette = smoothstep(1.25, 0.25, length((uv - 0.5) * vec2(1.25, 1.0)));
  col = mix(u_colors[0], col, 0.55 + 0.45 * vignette);

  // Velo de noche: el fondo queda en penumbra y el texto conserva el contraste en toda la página
  // (las secciones son transparentes, así no hay costuras entre ellas).
  col = mix(u_colors[0], col, u_veil);

  // Estela de luz del puntero y del toque, por encima del velo para que se sienta la respuesta.
  col += u_colors[3] * (lens * 0.16 + ring * 0.4) * light;

  // Tramado mínimo para que el degradado no se vea en escalones.
  col += (hash(gl_FragCoord.xy + t) - 0.5) / 255.0;

  gl_FragColor = vec4(col, 1.0);
}
`;
