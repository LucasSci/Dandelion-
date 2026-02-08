import discord
from discord import ui

from utils.i18n import get_interaction_context, resolve_locale, translate

# DB_NAME não é mais necessário aqui


class CriarFichaModal(ui.Modal):
    def __init__(self, target_user_id=None, locale: str | None = None):
        locale = resolve_locale(locale)
        super().__init__(title=translate("ui.character_create.title", locale=locale))
        self.target_user_id = target_user_id
        self.locale = locale

        self.nome = ui.TextInput(
            label=translate("ui.character_create.name_label", locale=locale),
            placeholder=translate("ui.character_create.name_placeholder", locale=locale),
        )
        self.raca = ui.TextInput(
            label=translate("ui.character_create.race_label", locale=locale),
            placeholder=translate("ui.character_create.race_placeholder", locale=locale),
        )
        self.classe = ui.TextInput(
            label=translate("ui.character_create.class_label", locale=locale),
            placeholder=translate("ui.character_create.class_placeholder", locale=locale),
        )
        self.genero = ui.TextInput(
            label=translate("ui.character_create.gender_label", locale=locale),
            placeholder=translate("ui.character_create.gender_placeholder", locale=locale),
            required=False,
        )

        # Conformidade verificada: required=False em campos opcionais
        self.historia = ui.TextInput(
            label=translate("ui.character_create.history_label", locale=locale),
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
            placeholder=translate("ui.character_create.history_placeholder", locale=locale),
        )
        # Added placeholder for better UX
        self.imagem = ui.TextInput(
            label=translate("ui.character_create.image_label", locale=locale),
            required=False,
            placeholder=translate("ui.character_create.image_placeholder", locale=locale),
        )

        self.add_item(self.nome)
        self.add_item(self.raca)
        self.add_item(self.classe)
        self.add_item(self.genero)
        self.add_item(self.historia)
        self.add_item(self.imagem)

    async def on_submit(self, interaction: discord.Interaction):
        ctx = get_interaction_context(interaction)
        final_user_id = self.target_user_id

        if final_user_id == 'proprio':
            final_user_id = interaction.user.id
        
        # FIX: Acessando DB via client, evitando abrir nova conexão (bolt.md)
        db = interaction.client.db

        try:
            # Não usamos 'async with db' aqui, pois a conexão é persistente. 
            # Usamos apenas o execute.
            await db.execute("""
                INSERT INTO personagens
                (user_id, nome, raca, classe, genero, historia, imagem_url, ouro)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                final_user_id,
                self.nome.value.strip(),
                self.raca.value,
                self.classe.value,
                self.genero.value,
                self.historia.value,
                self.imagem.value
            ))
            await db.commit()

            if final_user_id:
                title = ctx.t("ui.character_create.success_title", name=self.nome.value)
                footer_text = ctx.t("ui.character_create.success_footer")
                desc = ctx.t("ui.character_create.success_desc")
            else:
                title = ctx.t("ui.character_create.archive_title", name=self.nome.value)
                footer_text = ctx.t("ui.character_create.archive_footer")
                desc = ctx.t("ui.character_create.archive_desc")

            embed = discord.Embed(
                title=title,
                description=desc,
                color=0x57F287  # Green
            )

            # Identity Field
            raca = self.raca.value or ctx.t("ui.common.unknown")
            classe = self.classe.value or ctx.t("ui.common.adventurer")
            genero = self.genero.value or ctx.t("ui.common.not_informed")
            embed.add_field(
                name=ctx.t("ui.character_create.identity_field"),
                value=f"**{raca}** • *{classe}* • {genero}",
                inline=True,
            )

            # History Field (if provided)
            if self.historia.value:
                historia_curta = (self.historia.value[:200] + '...') if len(self.historia.value) > 200 else self.historia.value
                embed.add_field(
                    name=ctx.t("ui.character_create.history_field"),
                    value=f"_{historia_curta}_",
                    inline=False,
                )

            # Thumbnail (if provided)
            if self.imagem.value:
                embed.set_thumbnail(url=self.imagem.value)

            embed.set_footer(text=footer_text)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            # Capturando IntegrityError genericamente ou checando o tipo de erro específico do aiosqlite/sqlite3
            if "UNIQUE constraint failed" in str(e) or "IntegrityError" in str(type(e)):
                 await interaction.response.send_message(
                    ctx.t("ui.character_create.name_exists", name=self.nome.value),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    ctx.t("ui.character_create.error", error=e),
                    ephemeral=True,
                )
