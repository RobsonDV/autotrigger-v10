"""
Gera o ícone do MaisNova Sport Trigger — bola de futebol clássica.
Salva em assets/icon.ico com múltiplos tamanhos (16 a 256px).

Uso:
    python create_icon.py
"""
import math
import os
from PIL import Image, ImageDraw


def _polygon(cx: float, cy: float, r: float, sides: int, start_deg: float = 0):
    """Retorna lista de pontos de um polígono regular."""
    pts = []
    for i in range(sides):
        angle = math.radians(start_deg + i * 360 / sides)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _draw_ball(size: int) -> Image.Image:
    """Desenha uma bola de futebol em alta resolução e faz downscale para `size`."""
    scale = 4  # supersample para suavizar bordas
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx = cy = s / 2.0
    r = s / 2.0 * 0.88  # margem para sombra

    # ── Sombra oval sob a bola ────────────────────────────────────────────
    sx, sy = cx + s * 0.04, cy + r * 0.98
    sr, sh = r * 0.75, r * 0.18
    for i in range(8, 0, -1):
        a = int(8 * i)
        ex = sr + i * s * 0.005
        ey = sh + i * s * 0.003
        draw.ellipse([sx - ex, sy - ey, sx + ex, sy + ey], fill=(0, 0, 0, a))

    # ── Corpo da bola — gradiente radial branco → cinza ───────────────────
    steps = int(r)
    for i in range(steps, 0, -1):
        t = i / r  # 1 = borda, 0 = centro
        gray = int(255 - 90 * (t ** 1.8))
        draw.ellipse([cx - i, cy - i, cx + i, cy + i],
                     fill=(gray, gray, gray, 255))

    # ── Brilho (specular highlight) ───────────────────────────────────────
    hl_cx = cx - r * 0.28
    hl_cy = cy - r * 0.28
    hl_r = r * 0.33
    for i in range(int(hl_r), 0, -1):
        t = i / hl_r
        alpha = int(220 * (t ** 2.2))
        draw.ellipse(
            [hl_cx - i, hl_cy - i, hl_cx + i, hl_cy + i],
            fill=(255, 255, 255, alpha),
        )

    # ── Pentagons pretos — padrão clássico ────────────────────────────────
    if size >= 20:
        pr = r * 0.215  # raio de cada pentágono
        BLACK = (18, 18, 18, 255)
        lw = max(1, int(s * 0.004))

        # Pentágono central (topo da bola, ligeiramente acima do centro)
        top_x, top_y = cx, cy - r * 0.16
        pts = _polygon(top_x, top_y, pr, 5, -90)
        draw.polygon(pts, fill=BLACK)
        if size >= 32:
            draw.polygon(pts, outline=(0, 0, 0, 255), width=lw)

        if size >= 32:
            # 5 pentágonos na faixa intermediária
            ring_r = r * 0.57
            for i in range(5):
                angle_deg = -90.0 + 36.0 + i * 72.0
                angle = math.radians(angle_deg)
                px = cx + ring_r * math.cos(angle)
                # compressão vertical para dar perspectiva de esfera
                py = cy + ring_r * math.sin(angle) * 0.78
                pts2 = _polygon(px, py, pr * 0.82, 5, angle_deg - 72)
                draw.polygon(pts2, fill=BLACK)
                draw.polygon(pts2, outline=(0, 0, 0, 255), width=lw)

    # ── Borda circular da bola ────────────────────────────────────────────
    bw = max(2, int(s * 0.018))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                 outline=(15, 15, 15, 255), width=bw)

    # ── Downscale com LANCZOS ─────────────────────────────────────────────
    return img.resize((size, size), Image.LANCZOS)


def create_icon(output_path: str = "assets/icon.ico"):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [_draw_ball(s) for s in sizes]

    frames[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"Ícone gerado: {output_path}  ({len(frames)} tamanhos)")


if __name__ == "__main__":
    create_icon("assets/icon.ico")
    # Gera também uma prévia PNG para conferência
    preview = _draw_ball(256)
    preview.save("assets/icon_preview.png")
    print("Prévia gerada: assets/icon_preview.png")
