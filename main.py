import discord
from discord.ext import commands
from discord import ui

# Kanal-IDs definieren
TEXT_CHANNEL_ID = 1286057563699282111  # Kanal-ID, in dem die Nachrichten gelöscht werden sollen
FORUM_CHANNEL_ID = 1286062719824560190  # Forum-Kanal-ID, in dem die Beiträge erstellt werden sollen

# Intents initialisieren
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Bot erstellen
bot = commands.Bot(command_prefix="!", intents=intents)

# Globaler Zähler für die Beitragsnummer
post_counter = 1

# Button zum Formular
class FormButton(ui.View):
    @ui.button(label="Formular ausfüllen", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FormModal())

# Modal für das Formular
class FormModal(ui.Modal, title="Formular ausfüllen"):
    post_title = ui.TextInput(label="Titel des Beitrags", placeholder="Gib den Titel des Beitrags ein", required=True)
    post_description = ui.TextInput(label="Beschreibung", placeholder="Gib die Beschreibung des Beitrags ein", style=discord.TextStyle.long, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        global post_counter  # Zugriff auf den globalen Zähler

        # Generiere den vollständigen Titel mit der fortlaufenden Nummer
        formatted_title = f"{self.post_title.value} / # {post_counter}"

        # Erstelle den Beitrag im Forum mit den übermittelten Daten
        channel = bot.get_channel(FORUM_CHANNEL_ID)
        if isinstance(channel, discord.ForumChannel):  # Stelle sicher, dass der Kanal vom Typ ForumChannel ist
            # Erstelle einen Beitrag mit den übermittelten Daten
            thread = await channel.create_thread(
                name=formatted_title,  # Verwende den vollständigen Titel mit der Nummer
                content=self.post_description.value,  # Verwende den Wert des Beschreibung-Feldes
                reason="Neues Thema erstellt durch das Formular"
            )

            await interaction.response.send_message(
                f'Danke, dein Beitrag wurde erstellt:\n**Titel:** {formatted_title}\n**Beschreibung:** {self.post_description.value}',
                ephemeral=True
            )

            # Zähler erhöhen
            post_counter += 1
        else:
            await interaction.response.send_message("Der Kanal ist nicht vom Typ `ForumChannel`.", ephemeral=True)

# Event: Bot ist bereit
@bot.event
async def on_ready():
    print(f'Bot ist eingeloggt als {bot.user}')

    # Kanal definieren, in dem die Nachrichten gelöscht werden sollen
    text_channel = bot.get_channel(TEXT_CHANNEL_ID)

    # Alle Nachrichten in dem Kanal löschen, wenn es ein TextChannel ist
    if isinstance(text_channel, discord.TextChannel):  # Stelle sicher, dass der Kanal vom Typ TextChannel ist
        await text_channel.purge(limit=None)
        print(f'Alle Nachrichten im Channel {text_channel.name} wurden gelöscht.')

    # Button zum Formular senden
    forum_channel = bot.get_channel(TEXT_CHANNEL_ID)  # Verwende hier den TextChannel zum Senden des Buttons
    if isinstance(forum_channel, discord.TextChannel):  # Stelle sicher, dass der Kanal vom Typ TextChannel ist
        await forum_channel.send("Klicke auf den Button, um das Formular auszufüllen:", view=FormButton())

# Starte den Bot (ersetze DEIN_BOT_TOKEN durch deinen echten Bot-Token)
bot.run('DEIN_BOT_TOKEN')
