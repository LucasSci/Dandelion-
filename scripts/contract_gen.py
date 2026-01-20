from PIL import Image, ImageDraw, ImageFont
import io
import os
import aiohttp

# URL de um pergaminho em branco (hospedado no imgur ou similar)
BG_URL = "https://i.imgur.com/3p2W0fA.jpeg" 

async def gerar_imagem_contrato(titulo: str, descricao: str, recompensa: str) -> io.BytesIO:
    """Gera uma imagem de pergaminho com o texto da quest escrito"""
    
    async with aiohttp.ClientSession() as session:
        async with session.get(BG_URL) as resp:
            if resp.status != 200: return None
            data = await resp.read()

    # Abre a imagem base
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    upscale = 2
    if upscale > 1:
        img = img.resize((img.width * upscale, img.height * upscale), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(img)

    def _load_font(size: int) -> ImageFont.ImageFont:
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in paths:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def _wrap_text(text: str, max_width: int, font: ImageFont.ImageFont) -> list[str]:
        lines: list[str] = []
        for paragraph in text.splitlines():
            if not paragraph.strip():
                lines.append("")
                continue
            line = ""
            for word in paragraph.split():
                test_line = f"{line} {word}".strip()
                text_width = draw.textlength(test_line, font=font)
                if text_width <= max_width:
                    line = test_line
                else:
                    if line:
                        lines.append(line)
                    line = word
            if line:
                lines.append(line)
        return lines

    def _fit_fonts() -> tuple[ImageFont.ImageFont, ImageFont.ImageFont, list[str]]:
        base_title = 56 * upscale
        base_text = 34 * upscale
        max_width = W - (margin * 2)
        for step in range(0, 8):
            font_title = _load_font(max(base_title - (step * 4), 24))
            font_text = _load_font(max(base_text - (step * 2), 18))
            lines = _wrap_text(descricao, max_width, font_text)
            line_height = int(font_text.size * 1.2)
            content_height = (
                title_gap
                + (len(lines) * line_height)
                + reward_gap
                + int(font_text.size * 1.4)
            )
            if content_height <= (H - (margin * 2)):
                return font_title, font_text, lines
        return font_title, font_text, _wrap_text(descricao, max_width, font_text)

    # Configurações de Layout (Ajuste conforme a imagem de fundo escolhida)
    W, H = img.size
    margin = 80 * upscale
    current_h = 150 * upscale # Altura inicial
    title_gap = 70 * upscale
    reward_gap = 50 * upscale

    font_title, font_text, lines = _fit_fonts()
    
    # 1. Título
    # No PIL simples o load_default não escala bem. O ideal é baixar uma fonte .ttf.
    # Vou assumir uso básico aqui, mas recomendo fortemente usar uma .ttf
    draw.text((margin, current_h), titulo.upper(), fill="black", font=font_title, stroke_width=1, stroke_fill="#000000")
    current_h += title_gap

    # 2. Descrição (Wrap de texto)
    line_height = int(font_text.size * 1.2)
    for line in lines:
        draw.text((margin, current_h), line, fill="black", font=font_text, stroke_width=1, stroke_fill="#000000")
        current_h += line_height
    
    current_h += reward_gap
    
    # 3. Recompensa
    draw.text(
        (margin, current_h),
        f"RECOMPENSA: {recompensa}",
        fill="#8B0000",
        font=font_text,
        stroke_width=1,
        stroke_fill="#4a0000",
    )

    # Salva em buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
