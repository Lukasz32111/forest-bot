# config.py
import discord
from discord.ext import commands

PREFIX = '8'

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.guilds = True
INTENTS.reactions = True
INTENTS.members = True
