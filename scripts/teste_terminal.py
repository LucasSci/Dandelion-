import argparse
import base64
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI


# ----------------------------
# Helpers
# ----------------------------

def slugify(text: str, max_len: int = 80) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_-]+", "-", text, flags=re.UNICODE).strip("-")
    return text[:max_len] if text else "sem-nome"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class Row:
    id: int
    nome: str
    prompt: str
    imagem_url: Optional[str]


def fetch_next_rows(
    con: sqlite3.Connection,
    table: str,
    id_col: str,
    name_col: str,
    prompt_col: str,
    image_col: str,
    only_missing: bool,
    start_id: Optional[int],
    limit: int,
) -> list[Row]:
    cur = con.cursor()

    where = []
    params: list[object] = []

    if only_missing:
        where.append(f"({image_col} IS NULL OR TRIM({image_col}) = '')")

    where.append(f"({prompt_col} IS NOT NULL AND TRIM({prompt_col}) <> '')")

    if start_id is not None:
        where.append(f"{id_col} >= ?")
        params.append(start_id)

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT {id_col}, {name_col}, {prompt_col}, {image_col}
        FROM {table}
        WHERE {where_sql}
        ORDER BY {id_col} ASC
        LIMIT ?
    """
    params.append(limit)

    cur.execute(sql, params)
    rows: list[Row] = []
    for rid, nome, prompt, img in cur.fetchall():
        rows.append(Row(id=int(rid), nome=str(nome or ""), prompt=str(prompt or ""), imagem_url=img))
    return rows


def update_image_url(
    con: sqlite3.Connection,
    table: str,
    id_col: str,
    image_col: str,
    row_id: int,
    image_url: str,
) -> None:
    cur = con.cursor()
    cur.execute(
        f"UPDATE {table} SET {image_col} = ? WHERE {id_col} = ?",
        (image_url, row_id),
    )
    con.commit()


def generate_image_with_retry(
    client: OpenAI,
    model: str,
    prompt: str,
    size: str,
    quality: str,
    output_format: str,
    retries: int,
    base_sleep: float,
) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            img = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                quality=quality,
                output_format=output_format,
            )
            b64 = img.data[0].b64_json
            return base64.b64decode(b64)
        except Exception as e:
            last_err = e
            if attempt >= retries:
                break
            time.sleep(base_sleep * (2 ** attempt))

    raise RuntimeError(f"Falhou ao gerar imagem após retries. Erro: {last_err}") from last_err


# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Gera imagens a partir de prompts no SQLite e atualiza a coluna imagem_url."
    )
    ap.add_argument("--db", default="bestiario.db", help="Caminho do SQLite .db")
    ap.add_argument("--outdir", default="imagens/criaturas", help="Pasta para salvar imagens")
    ap.add_argument("--table", default="criaturas", help="Tabela fonte")
    ap.add_argument("--id-col", default="id", help="Coluna ID")
    ap.add_argument("--name-col", default="nome", help="Coluna nome (para nomear arquivo)")
    ap.add_argument("--prompt-col", default="descricao", help="Coluna prompt (texto)")
    ap.add_argument("--image-col", default="imagem_url", help="Coluna para salvar o caminho/URL da imagem")
    ap.add_argument("--only-missing", action="store_true", help="Só gera onde imagem_url estiver vazio/NULL")
    ap.add_argument("--start-id", type=int, default=None, help="Começar a partir deste ID (inclusive)")
    ap.add_argument("--limit", type=int, default=50, help="Quantos registros processar neste lote")
    ap.add_argument("--model", default="gpt-image-1.5", help="Modelo de imagem (ex: gpt-image-1.5)")
    ap.add_argument("--size", default="1024x1024", help="1024x1024, 1536x1024, 1024x1536, ou auto")
    ap.add_argument("--quality", default="high", help="high/medium/low/auto (para GPT Image)")
    ap.add_argument("--format", default="png", help="png/jpeg/webp (para GPT Image)")
    ap.add_argument("--style-prefix", default="", help="Texto prefixado ao prompt (estilo/consistência)")
    ap.add_argument("--dry-run", action="store_true", help="Não gera nem atualiza, só lista o que faria")
    ap.add_argument("--retries", type=int, default=3, help="Retries em falhas temporárias")
    ap.add_argument("--base-sleep", type=float, default=2.0, help="Backoff base (segundos)")
    ap.add_argument(
        "--env-file",
        default=None,
        help="Caminho do .env. Se omitido, procura automaticamente no diretório do script e acima.",
    )
    args = ap.parse_args()

    # ---- Load .env (adaptado) ----
    if args.env_file:
        env_path = Path(args.env_file).expanduser().resolve()
        if not env_path.exists():
            print(f"ERRO: .env não encontrado em: {env_path}", file=sys.stderr)
            sys.exit(1)
        load_dotenv(dotenv_path=env_path)
    else:
        # Procura automaticamente (cwd e diretório do arquivo)
        load_dotenv()
        # Garantia extra: tenta no mesmo diretório do script
        load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=False)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERRO: OPENAI_API_KEY não encontrada no .env ou variáveis de ambiente.", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.db).expanduser().resolve()
    if not db_path.exists():
        print(f"ERRO: DB não encontrado: {db_path}", file=sys.stderr)
        sys.exit(1)

    outdir = Path(args.outdir).expanduser().resolve()
    ensure_dir(outdir)

    client = OpenAI()  # lê OPENAI_API_KEY do ambiente

    con = sqlite3.connect(str(db_path))
    try:
        rows = fetch_next_rows(
            con=con,
            table=args.table,
            id_col=args.id_col,
            name_col=args.name_col,
            prompt_col=args.prompt_col,
            image_col=args.image_col,
            only_missing=args.only_missing,
            start_id=args.start_id,
            limit=args.limit,
        )

        if not rows:
            print("Nada para processar com os filtros atuais.")
            return

        print(f"Encontrados {len(rows)} registros para processar.\n")

        for idx, row in enumerate(rows, start=1):
            base_name = slugify(f"{row.id}-{row.nome}") if row.nome else f"{row.id}"
            filename = f"{base_name}.{args.format}"
            filepath = outdir / filename

            style_prefix = args.style_prefix.strip()
            prompt_text = row.prompt.strip()
            full_prompt = (style_prefix + "\n\n" + prompt_text).strip() if style_prefix else prompt_text

            print(f"[{idx}/{len(rows)}] ID={row.id} Nome='{row.nome}' -> {filepath.name}")

            if args.dry_run:
                continue

            try:
                img_bytes = generate_image_with_retry(
                    client=client,
                    model=args.model,
                    prompt=full_prompt,
                    size=args.size,
                    quality=args.quality,
                    output_format=args.format,
                    retries=args.retries,
                    base_sleep=args.base_sleep,
                )
                filepath.write_bytes(img_bytes)

                rel_path = os.path.relpath(filepath, db_path.parent).replace("\\", "/")
                update_image_url(
                    con=con,
                    table=args.table,
                    id_col=args.id_col,
                    image_col=args.image_col,
                    row_id=row.id,
                    image_url=rel_path,
                )

                print(f"  ✅ Salvo e atualizado no DB: {rel_path}\n")
            except Exception as e:
                print(f"  ❌ Falhou no ID={row.id}: {e}\n", file=sys.stderr)

    finally:
        con.close()


if __name__ == "__main__":
    main()
