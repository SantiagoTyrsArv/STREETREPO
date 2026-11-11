"""Genera las fotos de demostración de ``backend/app/demo/photos`` (decisión 76).

Son imágenes sintéticas dibujadas con Pillow (pavimento, hueco, grietas), con una franja
que dice «DEMO · imagen generada»: no son fotos de campo y no tienen autor ni licencia de terceros.
Con la misma semilla produce siempre los mismos archivos.

    cd backend && uv run python ../infra/scripts/generate_demo_photos.py
"""

import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "backend" / "app" / "demo" / "photos"
SIZE = (1280, 960)
JPEG_QUALITY = 82
BANNER_HEIGHT = 84
# Sin tildes: la fuente incluida en Pillow no las tiene.
BANNER_TEXT = "DEMO · imagen generada, no es una foto de campo"
LANE_YELLOW = (214, 170, 40)

# (nombre, semilla, gris base del pavimento, huecos, grietas, línea de carril)
SCENES = (
    ("demo-01-hueco", 11, 92, 1, 2, False),
    ("demo-02-grietas", 23, 108, 0, 7, True),
    ("demo-03-huecos", 37, 80, 3, 3, False),
    ("demo-04-borde", 51, 100, 2, 4, True),
)


def _asphalt(base: int) -> Image.Image:
    fine = Image.effect_noise(SIZE, 38).filter(ImageFilter.GaussianBlur(0.8))
    coarse = Image.effect_noise((SIZE[0] // 16, SIZE[1] // 16), 60).resize(
        SIZE, Image.Resampling.BICUBIC
    )
    texture = ImageChops.add(fine, coarse, scale=2.0, offset=base - 128)
    return Image.merge("RGB", (texture, texture, texture.point(lambda value: int(value * 0.97))))


def _blob(
    rng: random.Random, center: tuple[float, float], radius: float
) -> list[tuple[float, float]]:
    points = []
    for step in range(28):
        angle = 2 * math.pi * step / 28
        reach = radius * rng.uniform(0.72, 1.18)
        points.append(
            (center[0] + reach * math.cos(angle) * 1.35, center[1] + reach * math.sin(angle))
        )
    return points


def _pothole(image: Image.Image, rng: random.Random) -> None:
    center = (rng.uniform(300, SIZE[0] - 300), rng.uniform(220, SIZE[1] - 320))
    radius = rng.uniform(70, 150)
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.polygon(_blob(rng, center, radius * 1.12), fill=(150, 142, 128, 150))
    draw.polygon(_blob(rng, center, radius), fill=(34, 31, 28, 235))
    draw.polygon(
        _blob(rng, (center[0] + radius * 0.15, center[1] + radius * 0.12), radius * 0.55),
        fill=(18, 17, 16, 220),
    )
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(3.5)))


def _crack(image: Image.Image, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image)
    x, y = rng.uniform(80, SIZE[0] - 80), rng.uniform(60, SIZE[1] - 260)
    heading = rng.uniform(0, 2 * math.pi)
    for _ in range(rng.randint(18, 40)):
        heading += rng.uniform(-0.6, 0.6)
        length = rng.uniform(14, 36)
        end = (x + length * math.cos(heading), y + length * math.sin(heading))
        draw.line([(x, y), end], fill=(26, 24, 22, 255), width=rng.randint(2, 4))
        x, y = end


def _lane_line(image: Image.Image, rng: random.Random) -> None:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x = rng.uniform(140, 320)
    draw.polygon(
        [(x, 0), (x + 46, 0), (x + 190, SIZE[1]), (x + 120, SIZE[1])], fill=(*LANE_YELLOW, 190)
    )
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.5)))


def _banner(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    top = SIZE[1] - BANNER_HEIGHT
    draw.rectangle([(0, top), SIZE], fill=(27, 36, 48, 255))
    draw.rectangle([(0, top), (SIZE[0], top + 6)], fill=(245, 184, 0, 255))
    font = ImageFont.load_default(size=34)
    draw.text(
        (SIZE[0] / 2, top + 6 + (BANNER_HEIGHT - 6) / 2),
        BANNER_TEXT,
        font=font,
        fill=(245, 243, 238, 255),
        anchor="mm",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, seed, base, potholes, cracks, lane in SCENES:
        rng = random.Random(seed)  # noqa: S311 - dibujo reproducible, no criptografía
        image = _asphalt(base).convert("RGBA")
        if lane:
            _lane_line(image, rng)
        for _ in range(cracks):
            _crack(image, rng)
        for _ in range(potholes):
            _pothole(image, rng)
        _banner(image)
        path = OUTPUT_DIR / f"{name}.jpg"
        # Sin EXIF: Pillow solo escribe metadatos si se le pasan.
        image.convert("RGB").save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        print(f"{path.name}: {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
