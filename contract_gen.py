from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
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
    draw = ImageDraw.Draw(img)
    
    # Tenta carregar uma fonte manuscrita, ou usa padrão
    # Para produção, coloque um arquivo .ttf na pasta e use: ImageFont.truetype("font.ttf", 40)
    try:
        # Se você tiver uma fonte na pasta do bot:
        # font_title = ImageFont.truetype("utils/witcher_font.ttf", 60)
        # font_text = ImageFont.truetype("utils/witcher_font.ttf", 35)
        font_title = ImageFont.load_default() # Fallback simples
        font_text = ImageFont.load_default()
    except:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Configurações de Layout (Ajuste conforme a imagem de fundo escolhida)
    W, H = img.size
    margin = 80
    current_h = 150 # Altura inicial
    
    # 1. Título
    # No PIL simples o load_default não escala bem. O ideal é baixar uma fonte .ttf.
    # Vou assumir uso básico aqui, mas recomendo fortemente usar uma .ttf
    draw.text((margin, current_h), titulo.upper(), fill="black", font=font_title)
    current_h += 80

    # 2. Descrição (Wrap de texto)
    lines = textwrap.wrap(descricao, width=40) # Ajuste width conforme tamanho da fonte
    for line in lines:
        draw.text((margin, current_h), line, fill="black", font=font_text)
        current_h += 30
    
    current_h += 50
    
    # 3. Recompensa
    draw.text((margin, current_h), f"RECOMPENSA: {recompensa}", fill="#8B0000", font=font_text)

    # Salva em buffer
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer