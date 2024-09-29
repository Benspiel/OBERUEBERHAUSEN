import discord
from discord.ext import commands

def load_config():
    config = {}
    with open('infos.txt', 'r') as file:
        for line in file:
            if '=' in line:
                key, value = line.strip().split('=')
                config[key] = value
    return config

# Lade die Konfiguration
config = load_config()

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

CATEGORY_ID = int(config['CATEGORY_ID'])  # Kategorie-ID
CHANNEL_ID_CREATE_WORKS = int(config['CHANNEL_ID_CREATE_WORKS'])  # ID für den Create Works Channel
CHANNEL_ID_AUFGABEN = int(config['CHANNEL_ID_AUFGABEN'])  # ID für den Aufgaben Channel
ADMIN_ROLE_ID = int(config['ADMIN_ROLE_ID'])  # Rolle-ID für die Admin-Rolle
LOG_CHANNEL_ID = int(config['LOG_CHANNEL_ID'])  # ID für den Log-Channel

active_tasks = set()  # Set zur Verfolgung aktiver Aufgaben

@bot.event
async def on_ready():
    print(f'Bot ist bereit. Eingeloggt als {bot.user}')
    await delete_old_channel_and_send_button()

async def delete_old_channel_and_send_button():
    channel = bot.get_channel(CHANNEL_ID_CREATE_WORKS)
    if channel:
        await channel.purge(limit=100)

        button = discord.ui.Button(label="Aufgabe erstellen", style=discord.ButtonStyle.primary)
        button.callback = create_task_form
        view = discord.ui.View()
        view.add_item(button)

        await channel.send("Klicke den Button, um eine Aufgabe zu erstellen:", view=view)

async def create_task_form(interaction: discord.Interaction):
    # Überprüfe, ob bereits eine aktive Aufgabe existiert
    if active_tasks:
        await interaction.response.send_message("Es gibt bereits eine aktive Aufgabe. Bitte schließe diese zuerst.", ephemeral=True)
        return

    modal = discord.ui.Modal(title="Aufgabe erstellen")
    title_input = discord.ui.TextInput(label="Titel des Channels", required=True)
    message_input = discord.ui.TextInput(label="Erste Nachricht", required=True)

    modal.add_item(title_input)
    modal.add_item(message_input)

    await interaction.response.send_modal(modal)

    await modal.wait()
    channel_title = title_input.value
    first_message = message_input.value

    if not channel_title or not first_message:
        await interaction.followup.send("Bitte stelle sicher, dass beide Felder ausgefüllt sind.", ephemeral=True)
        return

    active_tasks.add(interaction.user.id)  # Füge die Benutzer-ID zu den aktiven Aufgaben hinzu

    category = bot.get_channel(CATEGORY_ID)
    admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)

    if not admin_role:
        await interaction.followup.send("Keine Admin-Rolle mit der angegebenen ID gefunden.", ephemeral=True)
        return

    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
        admin_role: discord.PermissionOverwrite(read_messages=True)
    }

    new_channel = await category.create_text_channel(channel_title, overwrites=overwrites)

    # Sende die Embed-Nachricht mit einem Zuweisen- und einem Erledigt-Button in den neuen Channel
    embed = discord.Embed(title=channel_title, description=first_message, color=discord.Color.blue())

    assign_button = discord.ui.Button(label="Zuweisen", style=discord.ButtonStyle.success)
    assign_button.callback = lambda inter: assign_task(inter, new_channel, embed)

    done_button = discord.ui.Button(label="Erledigt", style=discord.ButtonStyle.danger)
    done_button.callback = lambda inter: complete_task(inter, new_channel, embed)

    view = discord.ui.View()
    view.add_item(assign_button)
    view.add_item(done_button)

    await new_channel.send(embed=embed, view=view)  # Sende die Embed-Nachricht mit Buttons in den neuen Channel

    await interaction.followup.send(f"Channel **{channel_title}** wurde erstellt!", ephemeral=True)

async def assign_task(interaction: discord.Interaction, channel: discord.TextChannel, embed: discord.Embed):
    # Überprüfe, ob die Zuweisung im Aufgaben-Channel erfolgt
    if interaction.channel.id != CHANNEL_ID_AUFGABEN:
        await interaction.response.send_message("Du kannst Aufgaben nur im Aufgaben-Channel zuweisen.", ephemeral=True)
        return

    # Gewähre dem Benutzer Zugriff auf den Channel
    await channel.set_permissions(interaction.user, read_messages=True)

    # Lösche die Embed-Nachricht aus dem Aufgaben-Channel
    await interaction.message.delete()

    await interaction.response.send_message(f"Du hast Zugriff auf den Channel **{channel.name}** erhalten.", ephemeral=True)

async def complete_task(interaction: discord.Interaction, channel: discord.TextChannel, embed: discord.Embed):
    # Protokolliere die Erledigung in einem Log-Channel
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send(f"Aufgabe **{embed.title}** wurde als erledigt markiert von {interaction.user.mention}.")

    # Entferne die Benutzer-ID aus den aktiven Aufgaben
    active_tasks.discard(interaction.user.id)

    # Lösche die Embed-Nachricht aus dem Aufgaben-Channel
    await interaction.message.delete()

    await interaction.response.send_message(f"Die Aufgabe **{channel.name}** wurde als erledigt markiert.", ephemeral=True)

bot.run(config['BOT_TOKEN'])

