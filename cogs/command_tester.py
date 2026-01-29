import datetime as dt
import os
import traceback
from dataclasses import dataclass
from typing import Iterable, Optional, get_args, get_origin

import discord
from discord import app_commands
from discord.ext import commands
from openai import AsyncOpenAI

_OPENAI_KEY = os.getenv("OPENAI_API_KEY")


@dataclass
class CommandTestResult:
    nome: str
    status: str
    erro: Optional[str] = None
    traceback: Optional[str] = None
    analise_ia: Optional[str] = None


class _DummyResponse:
    def __init__(self) -> None:
        self._done = False

    @property
    def is_done(self) -> bool:
        return self._done

    async def defer(self, **kwargs) -> None:
        self._done = True

    async def send_message(self, *args, **kwargs) -> None:
        self._done = True


class _DummyFollowup:
    async def send(self, *args, **kwargs) -> None:
        return None


class _DummyUser:
    def __init__(self) -> None:
        self.id = 1
        self.name = "Tester"
        self.display_name = "Tester"
        self.mention = "@Tester"


class _DummyChannel:
    def __init__(self) -> None:
        self.id = 1
        self.name = "dummy-channel"

    async def send(self, *args, **kwargs) -> None:
        return None


class _DummyAttachment:
    def __init__(self) -> None:
        self.filename = "dummy.txt"
        self.url = "https://example.com/dummy.txt"
        self.content_type = "text/plain"

    async def read(self) -> bytes:
        return b"dummy"


class _DummyInteraction:
    def __init__(self, bot: commands.Bot) -> None:
        self.client = bot
        self.guild = None
        self.guild_id = None
        self.channel = _DummyChannel()
        self.user = _DummyUser()
        self.response = _DummyResponse()
        self.followup = _DummyFollowup()


class CommandTester(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = AsyncOpenAI(api_key=_OPENAI_KEY) if _OPENAI_KEY else None

    def _flatten_commands(
        self, comandos: Iterable[app_commands.Command], prefixo: str = ""
    ) -> list[tuple[str, app_commands.Command]]:
        encontrados: list[tuple[str, app_commands.Command]] = []
        for comando in comandos:
            nome_completo = f"{prefixo}{comando.name}" if prefixo else comando.name
            if isinstance(comando, app_commands.Group):
                encontrados.extend(
                    self._flatten_commands(comando.commands, prefixo=f"{nome_completo} ")
                )
            else:
                encontrados.append((nome_completo, comando))
        return encontrados

    def _resolver_tipo(self, annotation):
        if annotation is None:
            return None
        origin = get_origin(annotation)
        if origin is None:
            return annotation
        if origin is list:
            return list
        if origin is dict:
            return dict
        if origin is Optional:
            return get_args(annotation)[0]
        if origin is tuple:
            return tuple
        if origin is type(Optional):
            return get_args(annotation)[0]
        if origin is getattr(__import__("typing"), "Union"):
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            return args[0] if args else None
        return annotation

    def _dummy_for(self, annotation):
        base = self._resolver_tipo(annotation)
        if base is None or base is type(None):
            return None
        if base is str:
            return "teste"
        if base is int:
            return 1
        if base is float:
            return 1.0
        if base is bool:
            return True
        if base is list:
            return []
        if base is dict:
            return {}
        if base is tuple:
            return ()
        if isinstance(base, type) and issubclass(base, discord.Attachment):
            return _DummyAttachment()
        if isinstance(base, type) and issubclass(base, (discord.Member, discord.User)):
            return _DummyUser()
        if isinstance(base, type) and issubclass(base, discord.TextChannel):
            return _DummyChannel()
        if isinstance(base, type) and issubclass(base, discord.Role):
            return discord.Object(id=1)
        if isinstance(base, type) and issubclass(base, discord.Object):
            return discord.Object(id=1)
        return None

    def _build_args(self, comando: app_commands.Command) -> tuple[list[object], list[str]]:
        params = None
        if hasattr(comando, "parameters"):
            params = comando.parameters
            values = getattr(params, "values", None)
            if callable(values):
                params = list(values())
            else:
                params = list(params)
        elif hasattr(comando, "_params"):
            params = comando._params
            values = getattr(params, "values", None)
            if callable(values):
                params = list(values())
            else:
                params = list(params)
        if params is None:
            return [], []

        args = []
        avisos = []
        missing_sentinel = getattr(app_commands, "MISSING", app_commands.commands.MISSING)
        for param in params:
            annotation = getattr(param, "annotation", None)
            default = getattr(param, "default", None)
            if default is not None and default is not missing_sentinel:
                args.append(default)
                continue
            valor = self._dummy_for(annotation)
            if valor is None:
                avisos.append(param.name)
            args.append(valor)
        return args, avisos

    async def _gerar_analise_ia(self, nome: str, erro: str, stack: str) -> str:
        if not self.client:
            return "IA indisponível. Configure OPENAI_API_KEY para análises detalhadas."
        prompt = (
            "Você é um engenheiro de software analisando erros de um bot Discord. "
            "Explique o motivo provável do erro e sugira correções objetivas. "
            "Responda em português, com o formato:\n"
            "Motivo provável: ...\n"
            "Correções sugeridas: \n- ...\n- ...\n"
            f"\nComando: {nome}\nErro: {erro}\nStack trace:\n{stack}"
        )
        resposta = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return resposta.choices[0].message.content.strip()

    @app_commands.command(
        name="testar_comandos",
        description="🔎 Executa diagnóstico dos comandos do bot e gera relatório.",
    )
    @app_commands.describe(
        executar="Executa callbacks reais (pode falhar se faltarem dados).",
        usar_ia="Inclui análise da IA no relatório (precisa OPENAI_API_KEY).",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def testar_comandos(
        self,
        interaction: discord.Interaction,
        executar: bool = True,
        usar_ia: bool = True,
    ) -> None:
        await interaction.response.defer(ephemeral=True)

        resultados: list[CommandTestResult] = []
        comandos = self._flatten_commands(self.bot.tree.get_commands())
        dummy_interaction = _DummyInteraction(self.bot)

        for nome, comando in comandos:
            if nome == "testar_comandos":
                continue
            args, avisos = self._build_args(comando)
            if avisos and executar:
                resultados.append(
                    CommandTestResult(
                        nome=nome,
                        status="PULADO",
                        erro=f"Parâmetros sem valores simulados: {', '.join(avisos)}",
                    )
                )
                continue

            if not executar:
                resultados.append(CommandTestResult(nome=nome, status="OK"))
                continue

            binding = getattr(comando, "binding", None)
            try:
                if binding is not None:
                    await comando.callback(binding, dummy_interaction, *args)
                else:
                    await comando.callback(dummy_interaction, *args)
                resultados.append(CommandTestResult(nome=nome, status="OK"))
            except Exception as exc:
                stack = traceback.format_exc(limit=6)
                resultados.append(
                    CommandTestResult(
                        nome=nome,
                        status="ERRO",
                        erro=str(exc),
                        traceback=stack,
                    )
                )

        if usar_ia:
            for resultado in resultados:
                if resultado.status != "ERRO":
                    continue
                try:
                    resultado.analise_ia = await self._gerar_analise_ia(
                        resultado.nome,
                        resultado.erro or "",
                        resultado.traceback or "",
                    )
                except Exception as exc:
                    resultado.analise_ia = (
                        "Falha ao gerar análise da IA: "
                        f"{exc}"
                    )

        relatorio_dir = os.path.join("data", "diagnosticos")
        os.makedirs(relatorio_dir, exist_ok=True)
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        relatorio_path = os.path.join(
            relatorio_dir,
            f"relatorio_comandos_{timestamp}.txt",
        )

        total = len(resultados)
        erros = sum(1 for r in resultados if r.status == "ERRO")
        pulados = sum(1 for r in resultados if r.status == "PULADO")

        linhas = [
            "RELATÓRIO DE TESTE DE COMANDOS",
            f"Data/Hora: {dt.datetime.now().isoformat()}",
            f"Total de comandos: {total}",
            f"Sucesso: {total - erros - pulados}",
            f"Erros: {erros}",
            f"Pulados: {pulados}",
            "",
        ]

        for resultado in resultados:
            linhas.append(f"Comando: /{resultado.nome}")
            linhas.append(f"Status: {resultado.status}")
            if resultado.erro:
                linhas.append(f"Erro: {resultado.erro}")
            if resultado.traceback:
                linhas.append("Traceback:")
                linhas.append(resultado.traceback)
            if resultado.analise_ia:
                linhas.append("Análise IA:")
                linhas.append(resultado.analise_ia)
            linhas.append("-" * 60)

        with open(relatorio_path, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(linhas))

        arquivo_discord = discord.File(relatorio_path, filename=os.path.basename(relatorio_path))
        resumo = (
            f"✅ Relatório gerado com {total} comandos. "
            f"Erros: {erros}. Pulados: {pulados}."
        )
        await interaction.followup.send(resumo, file=arquivo_discord, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandTester(bot))
