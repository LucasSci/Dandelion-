"""Desktop control center for the Dandelion Discord bot."""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk


class BotControllerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Dandelion Control Center")
        self.geometry("960x720")
        self.minsize(860, 620)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()
        self._stop_reader = threading.Event()

        self._build_ui()
        self._set_status("Parado")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_output)

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=12, pady=10)

        self.start_button = ttk.Button(toolbar, text="Iniciar Bot", command=self.start_bot)
        self.start_button.pack(side=tk.LEFT)

        self.stop_button = ttk.Button(toolbar, text="Parar Bot", command=self.stop_bot, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(8, 0))

        self.status_label = ttk.Label(toolbar, text="Status: --", font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side=tk.LEFT, padx=(16, 0))

        self.last_change_label = ttk.Label(toolbar, text="Última alteração: --")
        self.last_change_label.pack(side=tk.RIGHT)

        content = ttk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        left_panel = ttk.Frame(content)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_panel = ttk.Frame(content)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(12, 0))

        log_label = ttk.Label(left_panel, text="Logs do Bot")
        log_label.pack(anchor=tk.W)

        self.log_text = tk.Text(left_panel, wrap=tk.WORD, height=24)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

        command_frame = ttk.LabelFrame(right_panel, text="Console de Comandos (Teste Local)")
        command_frame.pack(fill=tk.BOTH, expand=True)

        self.command_entry = ttk.Entry(command_frame)
        self.command_entry.pack(fill=tk.X, padx=12, pady=(12, 8))

        self.command_entry.bind("<Return>", lambda _event: self.run_command())

        command_button = ttk.Button(command_frame, text="Executar", command=self.run_command)
        command_button.pack(anchor=tk.E, padx=12)

        self.command_output = tk.Text(command_frame, wrap=tk.WORD, height=18)
        self.command_output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.command_output.configure(state=tk.DISABLED)

        hint = ttk.Label(
            right_panel,
            text=(
                "Dica: este console permite validar comandos localmente antes de levar ao Discord.\n"
                "Você pode integrar chamadas reais ao bot conectando este painel aos handlers."
            ),
            wraplength=360,
            foreground="#666",
        )
        hint.pack(anchor=tk.W, pady=(10, 0))

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _append_command_output(self, message: str) -> None:
        self.command_output.configure(state=tk.NORMAL)
        self.command_output.insert(tk.END, message)
        self.command_output.see(tk.END)
        self.command_output.configure(state=tk.DISABLED)

    def _set_status(self, status: str) -> None:
        self.status_label.configure(text=f"Status: {status}")

    def _set_last_change(self, message: str) -> None:
        self.last_change_label.configure(text=f"Última alteração: {message}")

    def start_bot(self) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showinfo("Bot ativo", "O bot já está em execução.")
            return

        try:
            self.process = subprocess.Popen(
                [sys.executable, "-u", "bot.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError:
            messagebox.showerror("Erro", "Arquivo bot.py não encontrado.")
            return

        self._stop_reader.clear()
        reader_thread = threading.Thread(target=self._read_output, daemon=True)
        reader_thread.start()

        self._set_status("Executando")
        self._set_last_change(time.strftime("%H:%M:%S"))
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)

    def stop_bot(self) -> None:
        if not self.process or self.process.poll() is not None:
            self._set_status("Parado")
            return

        self._stop_reader.set()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
        finally:
            self.process = None

        self._set_status("Parado")
        self._set_last_change(time.strftime("%H:%M:%S"))
        self.start_button.configure(state=tk.NORMAL)
        self.stop_button.configure(state=tk.DISABLED)

    def run_command(self) -> None:
        command = self.command_entry.get().strip()
        if not command:
            return

        self.command_entry.delete(0, tk.END)
        timestamp = time.strftime("%H:%M:%S")
        self._append_command_output(f"[{timestamp}] > {command}\n")
        self._append_command_output(
            "Simulação local: conecte este painel aos handlers para validar a lógica sem o Discord.\n\n"
        )

    def _read_output(self) -> None:
        if not self.process or not self.process.stdout:
            return

        for line in self.process.stdout:
            if self._stop_reader.is_set():
                break
            self.output_queue.put(line)

    def _poll_output(self) -> None:
        while not self.output_queue.empty():
            self._append_log(self.output_queue.get_nowait())

        if self.process and self.process.poll() is not None:
            self._set_status("Parado")
            self.start_button.configure(state=tk.NORMAL)
            self.stop_button.configure(state=tk.DISABLED)
            self.process = None

        self.after(200, self._poll_output)

    def _on_close(self) -> None:
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("Encerrar", "O bot ainda está rodando. Encerrar mesmo assim?"):
                return
            self.stop_bot()
        self.destroy()


if __name__ == "__main__":
    app = BotControllerApp()
    app.mainloop()
