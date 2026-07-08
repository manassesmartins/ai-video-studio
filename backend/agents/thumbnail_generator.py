import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

ROOT = Path(__file__).parent.parent.parent


class ThumbnailGenerator:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self._action_callback = None

    def on_action(self, callback):
        self._action_callback = callback

    def _report(self, action: str, progress: int = 0):
        if self._action_callback:
            self._action_callback("YouTube Publisher", action, progress)

    def _get_font(self, size: int, bold: bool = True):
        families = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        if bold:
            search = families[::2]
        else:
            search = families[1::2]

        for path in search:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def generate(self, title: str, source_image: str = None,
                 output_path: str = None, channel_name: str = "AI Studio") -> str:
        self._report("Criando thumbnail...", 10)

        thumb_dir = ROOT / "output" / "thumbnails"
        os.makedirs(thumb_dir, exist_ok=True)
        output_path = output_path or str(thumb_dir / "thumbnail.jpg")

        w, h = 1280, 720

        if source_image and os.path.exists(source_image):
            self._report("Usando imagem como fundo...", 30)
            try:
                bg = Image.open(source_image).convert("RGB")
                bg = bg.resize((w, h), Image.LANCZOS)
                bg = ImageEnhance.Brightness(bg).enhance(0.5)
                bg = bg.filter(ImageFilter.GaussianBlur(radius=4))
            except Exception:
                bg = self._create_gradient_background(w, h)
        else:
            bg = self._create_gradient_background(w, h)

        self._report("Adicionando overlay e texto...", 60)
        draw = ImageDraw.Draw(bg)

        bar_h = 100
        bar_color = (255, 0, 0) if not self._is_dark((0, 0, 0)) else (220, 40, 40)
        for i in range(bar_h):
            alpha = int(180 * (1 - i / bar_h))
            overlay = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle([(0, h - bar_h + i), (w, h - bar_h + i + 1)],
                                   fill=(bar_color[0], bar_color[1], bar_color[2], alpha))
            bg.paste(overlay, (0, 0), overlay)

        gradient = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        grad_draw = ImageDraw.Draw(gradient)
        for i in range(h):
            alpha = int(60 * (1 - i / h))
            grad_draw.line([(0, i), (w, i)], fill=(0, 0, 0, alpha))
        bg.paste(gradient, (0, 0), gradient)

        channel_text = channel_name.upper()
        font_small = self._get_font(28)
        if font_small:
            tx_bbox = draw.textbbox((0, 0), channel_text, font=font_small)
            draw.text((30, h - bar_h + 20), channel_text,
                      fill=(255, 255, 200), font=font_small)
            line_y = h - bar_h + 20 + (tx_bbox[3] - tx_bbox[1]) + 6
            draw.line([(30, line_y), (30 + (tx_bbox[2] - tx_bbox[0]) + 20, line_y)],
                      fill=(255, 50, 50), width=4)

        words = title.split()
        lines = []
        current = ""
        font_main = self._get_font(56)
        if not font_main:
            font_main = self._get_font(48)

        max_w = w - 80
        for word in words:
            test = current + " " + word if current else word
            try:
                tw = draw.textlength(test, font=font_main)
            except AttributeError:
                tw = len(test) * 30
            if tw > max_w and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)

        y_start = h // 2 - (len(lines) * 60) // 2 - 30
        for i, line in enumerate(lines):
            try:
                tw = draw.textlength(line, font=font_main)
            except AttributeError:
                tw = len(line) * 30
            x = (w - tw) // 2
            y = y_start + i * 65

            draw.text((x + 3, y + 3), line, fill=(0, 0, 0, 180), font=font_main)
            draw.text((x, y), line, fill=(255, 255, 255), font=font_main)

            accent_y = y + 60
            accent_w = min(tw + 40, w - 40)
            draw.rectangle([(w // 2 - accent_w // 2, accent_y),
                           (w // 2 + accent_w // 2, accent_y + 4)],
                          fill=(255, 50, 50))

        self._report("Salvando thumbnail...", 90)
        bg.save(output_path, "JPEG", quality=92)
        self._report("Thumbnail pronta!", 100)
        return output_path

    def _create_gradient_background(self, w: int, h: int) -> Image.Image:
        palettes = [
            [(20, 30, 60), (60, 20, 40)],
            [(30, 20, 50), (20, 50, 40)],
            [(40, 20, 30), (20, 30, 60)],
            [(10, 10, 30), (50, 10, 20)],
            [(20, 40, 60), (60, 40, 20)],
        ]
        colors = random.choice(palettes)
        bg = Image.new("RGB", (w, h), colors[0])
        draw = ImageDraw.Draw(bg)
        for i in range(h):
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * i / h)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * i / h)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * i / h)
            draw.line([(0, i), (w, i)], fill=(r, g, b))

        for _ in range(random.randint(3, 6)):
            cx = random.randint(0, w)
            cy = random.randint(0, h)
            r = random.randint(100, 300)
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                                 fill=(255, 255, 255, random.randint(5, 15)))
            bg.paste(overlay, (0, 0), overlay)

        return bg

    def _is_dark(self, color: tuple) -> bool:
        return (color[0] * 0.299 + color[1] * 0.587 + color[2] * 0.114) < 128
