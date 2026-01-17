import argparse
import base64
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

from dotenv import load_dotenv
from openai import OpenAI


# =========================
# CONFIG / HELPERS
# =========================

DEFAULT_MODEL = "gpt-image-1"  # recomendado pelos docs :contentReference[oaicite:2]{index=2}
DEFAULT_SIZE = "1024x1024"
DEFAULT_OUTPUT_FORMAT = "png"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"['’]", "", text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    Garante que a tabela images existe (no seu schema já existe),
    mas deixa o script robusto caso rode em DB antigo.
    """
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS images (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      monster_id INTEGER NOT NULL,
      file_path TEXT,
      prompt TEXT,
      model TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      FOREIGN KEY (monster_id) REFERENCES monsters(id) ON DELETE CASCADE
    );
    """)
    conn.commit()


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@dataclass
class MonsterRow:
    id: int
    slug: str
    name: str
    category: str
    origin: Optional[str]
    canon_tier: Optional[str]
    description: Optional[str]
    notes: Optional[str]


def fetch_targets(
    conn: sqlite3.Connection,
    limit: int,
    include_with_images: bool,
    origin_filter: Optional[str],
    category_filter: Optional[str],
) -> List[MonsterRow]:
    cur = conn.cursor()

    where = []
    params: List[object] = []

    if not include_with_images:
        where.append("img.id IS NULL")

    if origin_filter:
        where.append("m.origin = ?")
        params.append(origin_filter)

    if category_filter:
        where.append("m.category = ?")
        params.append(category_filter)

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    sql = f"""
    SELECT
      m.id, m.slug, m.name, m.category, m.origin, m.canon_tier, m.description, m.notes
    FROM monsters m
    LEFT JOIN images img ON img.monster_id = m.id
    {where_sql}
    GROUP BY m.id
    ORDER BY m.category, m.name
    LIMIT ?
    """
    params.append(limit)

    rows = cur.execute(sql, params).fetchall()
    out: List[MonsterRow] = []
    for r in rows:
        out.append(MonsterRow(
            id=r[0],
            slug=r[1],
            name=r[2],
            category=r[3],
            origin=r[4],
            canon_tier=r[5],
            description=r[6],
            notes=r[7],
        ))
    return out


def build_prompt(m: MonsterRow, style: str) -> str:
    """
    Prompt “inteligente”: usa o que tiver no DB, mas não quebra se estiver vazio.
    """
    base_bits = []
    base_bits.append(f"Creature concept art: {m.name}")
    base_bits.append(f"Category: {m.category}")
    if m.origin:
        base_bits.append(f"Source: {m.origin}")
    if m.canon_tier:
        base_bits.append(f"Canon tier: {m.canon_tier}")

    lore = []
    if m.description:
        lore.append(m.description.strip())
    if m.notes:
        lore.append(m.notes.strip())

    lore_text = " ".join(lore)
    if lore_text:
        base_bits.append(f"Notes: {lore_text}")

    # Estilo (você pode trocar por presets depois)
    if style == "witcher3":
        style_block = (
            "Style: dark fantasy, gritty medieval realism, cinematic chiaroscuro lighting, "
            "hyper-detailed textures (skin, fur, armor, grime), photorealistic concept art, "
            "sharp silhouette readability, 8k detail, moody atmosphere, grounded scale."
        )
    elif style == "neutral":
        style_block = (
            "Style: high-detail creature concept art, photorealistic, cinematic lighting, "
            "clean composition, strong silhouette readability."
        )
    else:
        # modo livre: o usuário passou uma string inteira como estilo
        style_block = f"Style: {style}"

    constraints = (
        "Constraints: single creature, full body, centered, no text, no watermark, "
        "no UI, no frame."
    )

    return "\n".join(["; ".join(base_bits), style_block, constraints])


def save_image_bytes(image_bytes: bytes, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(image_bytes)


def insert_image_row(
    conn: sqlite3.Connection,
    monster_id: int,
    file_path: str,
    prompt: str,
    model: str,
) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO images (monster_id, file_path, prompt, model) VALUES (?, ?, ?, ?)",
        (monster_id, file_path, prompt, model),
    )
    conn.commit()


def generate_one_image(
    client: OpenAI,
    prompt: str,
    model: str,
    size: str,
    output_format: str,
    retries: int,
    sleep_base: float,
) -> bytes:
    """
    Usa Images API (client.images.generate) e retorna bytes.
    Docs: base64 em img.data[0].b64_json :contentReference[oaicite:3]{index=3}
    """
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            img = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                output_format=output_format,  # suportado para GPT Image models :contentReference[oaicite:4]{index=4}
            )
            b64 = img.data[0].b64_json
            return base64.b64decode(b64)
        except Exception as e:
            last_err = e
            wait = sleep_base * attempt
            print(f"[WARN] Falhou (tentativa {attempt}/{retries}): {e}\n       aguardando {wait:.1f}s...", file=sys.stderr)
            time.sleep(wait)

    raise RuntimeError(f"Falhou após {retries} tentativas: {last_err}") from last_err


# =========================
# MAIN
# =========================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gera imagens para monstros do bestiario.db e grava na tabela images."
    )
    parser.add_argument("--db", default="bestiario.db", help="Caminho do banco SQLite (bestiario.db).")
    parser.add_argument("--out", default="generated_images", help="Pasta de saída para imagens.")
    parser.add_argument("--limit", type=int, default=20, help="Quantos monstros processar por execução.")
    parser.add_argument("--force", action="store_true", help="Gera mesmo se já existir registro em images.")
    parser.add_argument("--origin", default=None, help="Filtra por origin (ex: tw3, tw2, books, hos, baw).")
    parser.add_argument("--category", default=None, help="Filtra por category (ex: Necrophage, Specter, Ogroid).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Modelo de imagem (default: {DEFAULT_MODEL}).")
    parser.add_argument("--size", default=DEFAULT_SIZE, help=f"Tamanho (default: {DEFAULT_SIZE}).")
    parser.add_argument("--format", default=DEFAULT_OUTPUT_FORMAT, choices=["png", "jpeg", "webp"], help="Formato de saída.")
    parser.add_argument("--style", default="witcher3", help="Preset de estilo: witcher3 | neutral | ou texto livre.")
    parser.add_argument("--dry-run", action="store_true", help="Não chama API nem grava nada; só imprime o que faria.")
    parser.add_argument("--retries", type=int, default=3, help="Tentativas por imagem.")
    parser.add_argument("--sleep-base", type=float, default=2.0, help="Backoff base em segundos.")

    args = parser.parse_args()

    # .env
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERRO: OPENAI_API_KEY não encontrado. Coloque no .env (OPENAI_API_KEY=...) ou no ambiente.", file=sys.stderr)
        return 2

    client = OpenAI(api_key=api_key)

    db_path = args.db
    out_dir = Path(args.out)

    if not Path(db_path).exists():
        print(f"ERRO: DB não encontrado em: {db_path}", file=sys.stderr)
        return 2

    with connect_db(db_path) as conn:
        ensure_schema(conn)

        targets = fetch_targets(
            conn=conn,
            limit=args.limit,
            include_with_images=args.force,
            origin_filter=args.origin,
            category_filter=args.category,
        )

        if not targets:
            print("Nada para processar com os filtros atuais.")
            return 0

        print(f"Alvos: {len(targets)}")
        for i, m in enumerate(targets, start=1):
            # slug fallback (se algum estiver vazio)
            slug = m.slug or slugify(m.name)
            filename = f"{slug}.{args.format}"
            out_path = out_dir / (m.origin or "unknown") / m.category / filename

            prompt = build_prompt(m, args.style)

            print(f"\n[{i}/{len(targets)}] {m.name} ({m.category}) origin={m.origin} slug={slug}")
            print(f"-> arquivo: {out_path}")
            print(f"-> prompt (preview): {prompt[:260]}{'...' if len(prompt) > 260 else ''}")

            if args.dry_run:
                continue

            image_bytes = generate_one_image(
                client=client,
                prompt=prompt,
                model=args.model,
                size=args.size,
                output_format=args.format,
                retries=args.retries,
                sleep_base=args.sleep_base,
            )
            save_image_bytes(image_bytes, out_path)

            # path salvo relativo (melhor pra portability)
            rel_path = str(out_path.as_posix())
            insert_image_row(
                conn=conn,
                monster_id=m.id,
                file_path=rel_path,
                prompt=prompt,
                model=args.model,
            )

            print(f"✅ Gerado e salvo: {rel_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
