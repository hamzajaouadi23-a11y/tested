"""Compositions graphiques locales 1080x1920 (PIL) — assets ORIGINAUX (provenance=composition).

Langage visuel : fond dégradé sombre, barre d'accent, gros titre en DejaVu Bold,
puce d'étape, pied de page discret. Aucune fausse photo : ce sont des panneaux graphiques.
"""
import os

W, H = 1080, 1920
SAFE = 90            # marge safe-zone (UI des plateformes)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

PALETTES = [
    ((15, 23, 42), (30, 64, 175), (56, 189, 248)),
    ((20, 33, 26), (22, 101, 52), (134, 239, 172)),
    ((38, 20, 20), (153, 27, 27), (252, 165, 165)),
    ((30, 27, 46), (124, 58, 237), (196, 181, 253)),
    ((36, 28, 12), (180, 83, 9), (253, 230, 138)),
]


def _font(size, bold=True):
    from PIL import ImageFont
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def wrap_text(draw, text, font, max_w):
    """Coupe le texte en lignes mesurées (jamais de débordement)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            # mot trop long → coupe dure
            while draw.textlength(w, font=font) > max_w and len(w) > 1:
                k = len(w)
                while k > 1 and draw.textlength(w[:k] + "…", font=font) > max_w:
                    k -= 1
                lines.append(w[:k] + "…")
                w = w[k + 1:]
            cur = w
    if cur:
        lines.append(cur)
    return lines


def gradient_bg(c1, c2):
    from PIL import Image
    img = Image.new("RGB", (W, H), c1)
    px = img.load()
    for y in range(H):
        t = y / H
        row = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = row
    return img


def render_panel(out_path, title, subtitle, index=1, total=5, footer="TESTÉ & PROPRE"):
    """Paneau vertical 1080x1920. Retourne le chemin."""
    from PIL import Image, ImageDraw
    pal = PALETTES[(index - 1) % len(PALETTES)]
    img = gradient_bg(pal[0], (max(0, pal[1][0] - 60), max(0, pal[1][1] - 60), max(0, pal[1][2] - 60)))
    d = ImageDraw.Draw(img)

    # barre d'accent + puce étape
    d.rectangle([0, 0, W, 26], fill=pal[2])
    chip = f"ÉTAPE {index}/{total}"
    f_chip = _font(44)
    cw = d.textlength(chip, font=f_chip) + 56
    d.rounded_rectangle([SAFE, 150, SAFE + cw, 236], 40, fill=pal[2])
    d.text((SAFE + 28, 178), chip, font=f_chip, fill=(10, 10, 10))

    # titre (gros, wrappé, centré verticalement zone haute)
    f_title = _font(96)
    lines = wrap_text(d, title, f_title, W - 2 * SAFE)
    y = 420
    for ln in lines[:6]:
        # ombre
        d.text((SAFE + 4, y + 4), ln, font=f_title, fill=(0, 0, 0))
        d.text((SAFE, y), ln, font=f_title, fill=(255, 255, 255))
        y += 116

    # sous-titre / visual
    f_sub = _font(52, bold=False)
    sub_lines = wrap_text(d, subtitle, f_sub, W - 2 * SAFE)
    y2 = 1250
    for ln in sub_lines[:5]:
        d.text((SAFE, y2), ln, font=f_sub, fill=(226, 232, 240))
        y2 += 68

    # pied de page
    f_foot = _font(38, bold=False)
    fw = d.textlength(footer, font=f_foot)
    d.text(((W - fw) / 2, H - SAFE - 50), footer, font=f_foot, fill=(148, 163, 184))

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


def caption_overlay(out_path, text, tag=None, disclosure=False, w=W, h=H):
    """Overlay PNG transparent : bandeau bas + texte de caption centré, safe zones respectées."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font(64)
    lines = wrap_text(d, text, f, w - 2 * SAFE - 80)
    lines = lines[:4]
    block_h = len(lines) * 84 + 48
    y0 = h - SAFE - 320 - block_h
    # bandeau sombre arrondi (contraste garanti par construction)
    d.rounded_rectangle([SAFE - 10, y0, w - SAFE + 10, y0 + block_h], 34, fill=(2, 6, 23, 216))
    y = y0 + 24
    for ln in lines:
        tw = d.textlength(ln, font=f)
        d.text(((w - tw) / 2, y), ln, font=f, fill=(255, 255, 255))
        y += 84
    if tag:
        ft = _font(40)
        tw = d.textlength(tag, font=ft) + 44
        d.rounded_rectangle([SAFE, SAFE + 40, SAFE + tw, SAFE + 108], 30, fill=(56, 189, 248, 235))
        d.text((SAFE + 22, SAFE + 58), tag, font=ft, fill=(2, 6, 23))
    if disclosure:
        fd = _font(32, bold=False)
        txt = "Visuels / voix IA"
        tw = d.textlength(txt, font=fd) + 36
        d.rounded_rectangle([w - SAFE - tw, SAFE + 40, w - SAFE, SAFE + 96], 26, fill=(148, 163, 184, 160))
        d.text((w - SAFE - tw + 18, SAFE + 53), txt, font=fd, fill=(15, 23, 42))
    img.save(out_path, "PNG")
    return out_path


def measure_overlay(text, tag=None):
    """Métriques pour la QA : nb de lignes, hauteur bloc, dépassements (par construction=0)."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    f = _font(64)
    lines = wrap_text(d, text, f, W - 2 * SAFE - 80)
    maxw = max((d.textlength(ln, font=f) for ln in lines), default=0)
    return {"lines": min(len(lines), 4), "raw_lines": len(lines),
            "max_width": maxw, "limit": W - 2 * SAFE, "overflow": maxw > (W - 2 * SAFE),
            "font_px": 64, "block_below_y": H - SAFE - 320}
