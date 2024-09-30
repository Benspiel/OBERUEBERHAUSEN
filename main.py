import discord
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

# Lese die Token, Channel ID, Category ID, Target Channel ID, Log Channel ID und Role ID aus der Datei
def read_infos():
    with open('infos.txt', 'r') as f:
        lines = f.readlines()
        token = lines[0].split('=')[1].strip()
        channel_id = int(lines[1].split('=')[1].strip())
        category_id = int(lines[2].split('=')[1].strip())  # Kategorie-ID
        target_channel_id = int(lines[3].split('=')[1].strip())  # ID des Zielkanals
        log_channel_id = int(lines[4].split('=')[1].strip())  # ID des Log-Kanals
        role_id = int(lines[5].split('=')[1].strip())  # ID der Rolle, die den Delete-Button verwenden darf
    return token, channel_id, category_id, target_channel_id, log_channel_id, role_id

TOKEN, CHANNEL_ID, CATEGORY_ID, TARGET_CHANNEL_ID, LOG_CHANNEL_ID, ROLE_ID = read_infos()

# Erstelle den Bot mit Command-Intents und App Command Tree
intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Speichere aktive Claims pro Aufgabe
active_claims = {}

class FormModal(Modal):
    def __init__(self):
        super().__init__(title="Formular")

        # Füge Eingabefelder hinzu
        self.title_input = TextInput(label="Titel", placeholder="Gib den Titel ein...")
        self.description_input = TextInput(label="Beschreibung", style=discord.TextStyle.paragraph, placeholder="Gib die Beschreibung ein...")
        self.max_claims_input = TextInput(label="Maximale Anzahl an Claimer", placeholder="Gib die maximale Anzahl ein...", style=discord.TextStyle.short)

        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.max_claims_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Kanal erstellen und Beschreibung als erste Nachricht senden
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)
        max_claims = int(self.max_claims_input.value)

        if category:
            # Erstelle einen neuen Kanal in der Kategorie mit dem Titel des Formulars
            new_channel = await category.create_text_channel(name=self.title_input.value)

            # Speichere die Informationen zur Aufgabe und Initialisierung der Claims
            active_claims[new_channel.id] = {"max_claims": max_claims, "current_claims": 0, "users": []}

            # Sende die Beschreibung als einzige Nachricht im erstellten Kanal
            embed = discord.Embed(title=self.title_input.value, description=self.description_input.value)
            complete_button = Button(label="Aufgabe erledigt", style=discord.ButtonStyle.success)

            async def complete_callback(complete_interaction: discord.Interaction):
                # Lösche den Kanal, wenn die Aufgabe erledigt wurde
                await new_channel.delete(reason="Aufgabe wurde erledigt.")
                # Logge die abgeschlossene Aufgabe
                log_channel = bot.get_channel(LOG_CHANNEL_ID)
                if log_channel:
                    await log_channel.send(f"Die Aufgabe '{self.title_input.value}' wurde erledigt und der Kanal wurde gelöscht.")

            complete_button.callback = complete_callback
            view = View(timeout=None)
            view.add_item(complete_button)
            await new_channel.send(embed=embed, view=view)

            # Sende eine Meldung in den Zielkanal, dass die Aufgabe erstellt wurde
            target_channel = bot.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                embed = discord.Embed(
                    title=f"Neue Aufgabe: {self.title_input.value}",
                    description=f"{self.description_input.value}\n\nAktueller Stand: 0/{max_claims} Teilnehmer"
                )
                claim_button = Button(label="Claim", style=discord.ButtonStyle.primary)
                delete_button = Button(label="Delete", style=discord.ButtonStyle.danger)  # Button ist nicht mehr disabled

                async def claim_callback(claim_interaction: discord.Interaction):
                    # Überprüfe, ob der Benutzer bereits die Aufgabe geclaimed hat
                    if claim_interaction.user.id in active_claims[new_channel.id]["users"]:
                        await claim_interaction.response.send_message("Du hast diese Aufgabe bereits geclaimed.", ephemeral=True)
                        return

                    # Aktualisiere die Anzahl der Claimer
                    if active_claims[new_channel.id]["current_claims"] < max_claims:
                        active_claims[new_channel.id]["current_claims"] += 1
                        active_claims[new_channel.id]["users"].append(claim_interaction.user.id)

                        # Aktualisiere die Nachricht mit dem neuen Status
                        current_claims = active_claims[new_channel.id]["current_claims"]
                        updated_embed = discord.Embed(
                            title=f"Neue Aufgabe: {self.title_input.value}",
                            description=f"{self.description_input.value}\n\nAktueller Stand: {current_claims}/{max_claims} Teilnehmer"
                        )
                        await claim_interaction.message.edit(embed=updated_embed, view=view)

                        # Logge die Übernahme der Aufgabe
                        log_channel = bot.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            await log_channel.send(f"{claim_interaction.user.mention} hat die Aufgabe '{self.title_input.value}' geclaimed.")

                        # Gebe dem Benutzer Zugriff auf den Aufgabenkanal
                        await new_channel.set_permissions(claim_interaction.user, read_messages=True, send_messages=True)

                        # Lösche die Nachricht, wenn die maximale Anzahl erreicht wurde
                        if current_claims == max_claims:
                            await claim_interaction.message.delete()
                            # Logge die Aufgabe als "vollständig geclaimed"
                            if log_channel:
                                await log_channel.send(f"Die Aufgabe '{self.title_input.value}' hat nun die maximale Anzahl an Teilnehmern erreicht und die Nachricht wurde gelöscht.")

                        await claim_interaction.response.send_message("Du hast die Aufgabe erfolgreich geclaimed.", ephemeral=True)
                    else:
                        await claim_interaction.response.send_message("Die maximale Anzahl an Claimer für diese Aufgabe ist bereits erreicht.", ephemeral=True)

                async def delete_callback(delete_interaction: discord.Interaction):
                    # Überprüfe, ob der Benutzer die Berechtigung hat, die Nachricht zu löschen
                    if any(role.id == ROLE_ID for role in delete_interaction.user.roles):
                        await delete_interaction.message.delete()
                        await new_channel.delete(reason="Aufgabe wurde manuell gelöscht.")
                        # Logge die manuelle Löschung
                        log_channel = bot.get_channel(LOG_CHANNEL_ID)
                        if log_channel:
                            await log_channel.send(f"{delete_interaction.user.mention} hat die Aufgabe '{self.title_input.value}' gelöscht.")
                    else:
                        await delete_interaction.response.send_message("Du hast keine Berechtigung, diese Nachricht zu löschen.", ephemeral=True)

                claim_button.callback = claim_callback
                delete_button.callback = delete_callback

                view = View(timeout=None)
                view.add_item(claim_button)
                view.add_item(delete_button)

                await target_channel.send(embed=embed, view=view)
                print('Aufgabe gesendet.')

@bot.event
async def on_ready():
    print(f'Bot ist eingeloggt als {bot.user}')
    # Clear den Kanal und sende den Button (wie zuvor)
    channel = bot.get_channel(CHANNEL_ID)
    if channel is not None:
        async for message in channel.history(limit=100):
            await message.delete()

        button = Button(label="Formular öffnen", style=discord.ButtonStyle.primary)

        async def button_callback(interaction: discord.Interaction):
            modal = FormModal()
            await interaction.response.send_modal(modal)

        button.callback = button_callback
        view = View(timeout=None)
        view.add_item(button)
        await channel.send("Klicke auf den Button, um das Formular zu öffnen:", view=view)
        print('Button gesendet.')

# Starte den Bot
bot.run(TOKEN)
