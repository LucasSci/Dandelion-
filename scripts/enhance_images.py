import argparse
import asyncio
import logging
import sqlite3
import time
from pathlib import Path
from typing import List

import aiohttp

# ==========================================
# LOGGING SETUP
# ==========================================
def setup_logger(log_file: str) -> logging.Logger:
    logger = logging.getLogger("ImageEnhancer")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Terminal handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    if log_file:
        fh = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger

# ==========================================
# FILE SCANNER
# ==========================================
class FileScanner:
    @staticmethod
    def scan_pngs(input_dir: Path) -> List[Path]:
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        # Encontra todos os arquivos .png recursivamente
        return [p for p in input_dir.rglob("*.png") if p.is_file()]

# ==========================================
# PROGRESS TRACKER (CHECKPOINTING)
# ==========================================
class ProgressTracker:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    filename TEXT PRIMARY KEY,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def is_processed(self, filename: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM processed_files WHERE filename = ?", (filename,))
            row = cursor.fetchone()
            if row and row[0] == "SUCCESS":
                return True
            return False

    def mark_processed(self, filename: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO processed_files (filename, status)
                VALUES (?, ?)
                ON CONFLICT(filename) DO UPDATE SET
                    status=excluded.status,
                    timestamp=CURRENT_TIMESTAMP
            """, (filename, status))
            conn.commit()

# ==========================================
# RATE LIMITED API CLIENT
# ==========================================
class RateLimitedAPIClient:
    def __init__(self, api_url: str, api_key: str, max_rpm: int, max_retries: int = 5):
        self.api_url = api_url
        self.api_key = api_key
        # Limitador de concorrência com base no RPM
        self.semaphore = asyncio.Semaphore(min(max_rpm, 10))
        self.max_retries = max_retries

        # Garante um intervalo mínimo entre requisições para espalhar a carga (Token Bucket simplificado)
        self.min_interval_between_calls = 60.0 / max_rpm if max_rpm > 0 else 0

        self.last_call_time = 0.0
        self.lock = asyncio.Lock()

    async def _wait_for_rate_limit(self):
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_call_time
            if elapsed < self.min_interval_between_calls:
                await asyncio.sleep(self.min_interval_between_calls - elapsed)
            self.last_call_time = time.monotonic()

    def is_valid_png(self, file_path: Path) -> bool:
        """Valida se o arquivo gerado não está corrompido verificando o cabeçalho PNG."""
        if not file_path.exists() or file_path.stat().st_size < 8:
            return False
        try:
            with open(file_path, "rb") as f:
                header = f.read(8)
                # Assinatura de um arquivo PNG válido
                return header == b"\x89PNG\r\n\x1a\n"
        except IOError:
            return False

    async def enhance_image(self, session: aiohttp.ClientSession, input_path: Path, output_path: Path, logger: logging.Logger) -> bool:
        """
        Envia a imagem para a API, salva o resultado e valida.
        Retorna True em caso de sucesso, False caso contrário.
        """
        filename = input_path.name

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            # Outros cabeçalhos necessários pela API
        }

        for attempt in range(1, self.max_retries + 1):
            async with self.semaphore:
                await self._wait_for_rate_limit()

                try:
                    data = aiohttp.FormData()
                    # Placeholder para o endpoint da API de enhancement.
                    data.add_field('image',
                                   open(input_path, 'rb'),
                                   filename=filename,
                                   content_type='image/png')
                    # Adicione outros campos necessários como 'prompt', 'model', etc., aqui.

                    async with session.post(self.api_url, data=data, headers=headers) as response:
                        if response.status == 200:
                            content = await response.read()

                            # Salva a imagem no diretório de saída
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, "wb") as f:
                                f.write(content)

                            if self.is_valid_png(output_path):
                                return True
                            else:
                                logger.error(f"[{filename}] Arquivo gerado corrompido (cabeçalho PNG inválido).")
                                output_path.unlink(missing_ok=True)
                                return False

                        elif response.status in (429, 500, 502, 503):
                            # Exponential Backoff
                            backoff = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s, 40s
                            logger.warning(f"[{filename}] Erro {response.status}. Aguardando {backoff}s para próxima tentativa... (Tentativa {attempt}/{self.max_retries})")
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            text = await response.text()
                            logger.error(f"[{filename}] Erro na API {response.status}: {text}")
                            return False

                except aiohttp.ClientError as e:
                    backoff = 5 * (2 ** (attempt - 1))
                    logger.warning(f"[{filename}] Erro de rede: {e}. Aguardando {backoff}s... (Tentativa {attempt}/{self.max_retries})")
                    await asyncio.sleep(backoff)
                except Exception as e:
                    logger.error(f"[{filename}] Erro inesperado: {e}")
                    return False

        logger.error(f"[{filename}] Falha permanente após {self.max_retries} tentativas.")
        return False

# ==========================================
# MAIN EXECUTION LOOP
# ==========================================
async def process_files(input_dir: Path, output_dir: Path, db_path: str, log_file: str, api_url: str, api_key: str, max_rpm: int):
    logger = setup_logger(log_file)
    tracker = ProgressTracker(db_path)

    try:
        files = FileScanner.scan_pngs(input_dir)
    except FileNotFoundError as e:
        logger.error(e)
        return

    total_files = len(files)
    logger.info(f"Encontrados {total_files} arquivos PNG em {input_dir}.")

    # URL placeholder simulando integração existente caso não seja fornecida
    if not api_url:
        api_url = "https://api.openai.com/v1/images/edits"

    client = RateLimitedAPIClient(
        api_url=api_url,
        api_key=api_key,
        max_rpm=max_rpm
    )

    async with aiohttp.ClientSession() as session:
        tasks = []
        pending_files = []

        # Verifica quais arquivos já foram processados
        for file_path in files:
            rel_path = str(file_path.relative_to(input_dir))
            if tracker.is_processed(rel_path):
                logger.info(f"Pulando {rel_path} - já processado com sucesso.")
            else:
                pending_files.append((file_path, rel_path))

        logger.info(f"Iniciando processamento para {len(pending_files)} arquivos.")

        async def worker(index, total, in_path, rel_path):
            out_path = output_dir / rel_path
            success = await client.enhance_image(session, in_path, out_path, logger)
            if success:
                tracker.mark_processed(rel_path, "SUCCESS")
                logger.info(f"[{index}/{total}] Imagem {rel_path} processada com sucesso.")
            else:
                tracker.mark_processed(rel_path, "FAILED")
                logger.info(f"[{index}/{total}] Falha ao processar a imagem {rel_path}.")

        # Agenda as tarefas com base no limitador do client
        for idx, (in_path, rel_path) in enumerate(pending_files, 1):
            tasks.append(asyncio.create_task(worker(idx, len(pending_files), in_path, rel_path)))

        if tasks:
            await asyncio.gather(*tasks)

    logger.info("Processamento concluído.")

def main():
    parser = argparse.ArgumentParser(description="Script para melhoria gráfica de imagens PNG via API")
    parser.add_argument("--input-dir", required=True, type=Path, help="Diretório de entrada contendo os arquivos PNG")
    parser.add_argument("--output-dir", required=True, type=Path, help="Diretório de saída para os arquivos melhorados")
    parser.add_argument("--db-path", default="progress.db", help="Caminho para o banco SQLite de rastreamento")
    parser.add_argument("--log-file", default="enhance_images.log", help="Caminho para o arquivo de log")
    parser.add_argument("--api-url", default="", help="URL da API de melhoramento de imagem")
    parser.add_argument("--api-key", default="DUMMY_KEY", help="Chave de API para autenticação")
    parser.add_argument("--max-rpm", type=int, default=50, help="Limite máximo de requisições por minuto")

    args = parser.parse_args()

    asyncio.run(process_files(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        db_path=args.db_path,
        log_file=args.log_file,
        api_url=args.api_url,
        api_key=args.api_key,
        max_rpm=args.max_rpm
    ))

if __name__ == "__main__":
    main()
