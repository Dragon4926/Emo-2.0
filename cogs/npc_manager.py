import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime

class NPCManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parent_cog = None
        self.character_creation_cog = None
    
    async def cog_load(self):
        self.parent_cog = self.bot.get_cog("DnDGame")
        self.character_creation_cog = self.bot.get_cog("CharacterCreation")
        if not self.parent_cog:
            print("WARNING: DnDGame cog not found. NPC Manager requires DnDGame cog.")
        if not self.character_creation_cog:
            print("WARNING: CharacterCreation cog not found. NPC Manager requires CharacterCreation cog.")
    
    @commands.command(name="create_npc")
    async def create_npc(self, ctx, *, npc_name=None):
        """Create an NPC for the current D&D game
        
        Example: !create_npc [optional name]
        """
        if not self.parent_cog or not self.character_creation_cog:
            await ctx.send("Error: Required game systems are not currently available.")
            return
        
        channel_id = str(ctx.channel.id)
        game = await self.parent_cog.get_game(channel_id)
        if not game:
            await ctx.send("There is no active D&D game in this channel. Use `!dnd` to create one first.")
            return
        
        # Only the GM or game creator can create NPCs
        if str(ctx.author.id) != game["game_master_id"] and str(ctx.author.id) != game["created_by"]:
            await ctx.send("Only the Game Master or game creator can create NPCs.")
            return
        
        # Initialize NPCs list if it doesn't exist
        if "npcs" not in game:
            game["npcs"] = []
        
        # Generate a random character using the existing method
        character_data = self.character_creation_cog.generate_random_character()
        
        # Override the name if provided
        if npc_name:
            character_data["name"] = npc_name
        
        # Add NPC flag
        character_data["is_npc"] = True
        character_data["created_at"] = datetime.now().isoformat()
        
        # Add the NPC to the game
        game["npcs"].append(character_data)
        game["last_updated"] = datetime.now().isoformat()
        await self.parent_cog.save_game(channel_id, game)
        
        # Create success embed
        success_embed = discord.Embed(
            title=f"🎭 NPC Created: {character_data.get('name', 'Unknown')}",
            description=f"A new NPC has joined the adventure!",
            color=discord.Color.green()
        )
        self.character_creation_cog._add_character_fields(success_embed, character_data)
        
        # Add NPC image
        normalized_race = self.character_creation_cog.normalize_race(character_data['race'])
        image_key = f"{normalized_race}_{character_data['class']}"
        image_url = self.character_creation_cog.character_images.get(image_key, self.character_creation_cog.default_image)
        success_embed.set_thumbnail(url=image_url)
        
        await ctx.send(embed=success_embed)
    
    @commands.command(name="list_npcs")
    async def list_npcs(self, ctx):
        """List all NPCs in the current D&D game
        
        Example: !list_npcs
        """
        if not self.parent_cog:
            await ctx.send("Error: DnD game system is not currently available.")
            return
        
        channel_id = str(ctx.channel.id)
        game = await self.parent_cog.get_game(channel_id)
        if not game:
            await ctx.send("There is no active D&D game in this channel.")
            return
        
        if not game.get("npcs") or len(game["npcs"]) == 0:
            await ctx.send("There are no NPCs in this game yet. Use `!create_npc` to create one.")
            return
        
        embed = discord.Embed(
            title="🎭 NPCs in this Adventure",
            description=f"There are {len(game['npcs'])} NPCs in this game.",
            color=discord.Color.blue()
        )
        
        for i, npc in enumerate(game["npcs"]):
            embed.add_field(
                name=f"{i+1}. {npc.get('name', 'Unknown')}",
                value=(
                    f"Race: {npc.get('race', 'Unknown')}\n"
                    f"Class: {npc.get('class', 'Unknown')}\n"
                    f"Level: {npc.get('level', '0')}"
                ),
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="npc_detail")
    async def npc_detail(self, ctx, *, npc_name):
        """Show detailed information about a specific NPC
        
        Example: !npc_detail Gandalf
        """
        if not self.parent_cog:
            await ctx.send("Error: DnD game system is not currently available.")
            return
        
        channel_id = str(ctx.channel.id)
        game = await self.parent_cog.get_game(channel_id)
        if not game:
            await ctx.send("There is no active D&D game in this channel.")
            return
        
        if not game.get("npcs") or len(game["npcs"]) == 0:
            await ctx.send("There are no NPCs in this game yet.")
            return
        
        # Find the NPC by name
        npc = None
        for character in game["npcs"]:
            if character.get("name", "").lower() == npc_name.lower():
                npc = character
                break
        
        if not npc:
            await ctx.send(f"No NPC named '{npc_name}' was found.")
            return
        
        # Create detailed embed
        embed = discord.Embed(
            title=f"🎭 NPC: {npc.get('name', 'Unknown')}",
            description=npc.get("backstory", "No backstory available."),
            color=discord.Color.gold()
        )
        
        self.character_creation_cog._add_character_fields(embed, npc)
        
        # Add ability scores
        ability_scores = (
            f"STR: {npc.get('strength', '10')} | "
            f"DEX: {npc.get('dexterity', '10')} | "
            f"CON: {npc.get('constitution', '10')}\n"
            f"INT: {npc.get('intelligence', '10')} | "
            f"WIS: {npc.get('wisdom', '10')} | "
            f"CHA: {npc.get('charisma', '10')}"
        )
        embed.add_field(name="Ability Scores", value=ability_scores, inline=False)
        
        # Add inventory if available
        if "inventory" in npc and npc["inventory"]:
            embed.add_field(name="Inventory", value=", ".join(npc["inventory"]), inline=False)
        
        # Add skills if available
        if "skills" in npc and npc["skills"]:
            embed.add_field(name="Skills", value=", ".join(npc["skills"]), inline=False)
        
        # Add NPC image
        normalized_race = self.character_creation_cog.normalize_race(npc['race'])
        image_key = f"{normalized_race}_{npc['class']}"
        image_url = self.character_creation_cog.character_images.get(image_key, self.character_creation_cog.default_image)
        embed.set_thumbnail(url=image_url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="remove_npc")
    async def remove_npc(self, ctx, *, npc_name):
        """Remove an NPC from the game
        
        Example: !remove_npc Gandalf
        """
        if not self.parent_cog:
            await ctx.send("Error: DnD game system is not currently available.")
            return
        
        channel_id = str(ctx.channel.id)
        game = await self.parent_cog.get_game(channel_id)
        if not game:
            await ctx.send("There is no active D&D game in this channel.")
            return
        
        # Only the GM or game creator can remove NPCs
        if str(ctx.author.id) != game["game_master_id"] and str(ctx.author.id) != game["created_by"]:
            await ctx.send("Only the Game Master or game creator can remove NPCs.")
            return
        
        if not game.get("npcs") or len(game["npcs"]) == 0:
            await ctx.send("There are no NPCs in this game yet.")
            return
        
        # Find the NPC by name
        npc_index = None
        for i, character in enumerate(game["npcs"]):
            if character.get("name", "").lower() == npc_name.lower():
                npc_index = i
                break
        
        if npc_index is None:
            await ctx.send(f"No NPC named '{npc_name}' was found.")
            return
        
        # Remove the NPC
        removed_npc = game["npcs"].pop(npc_index)
        game["last_updated"] = datetime.now().isoformat()
        await self.parent_cog.save_game(channel_id, game)
        
        await ctx.send(f"NPC '{removed_npc.get('name', 'Unknown')}' has been removed from the game.")

async def setup(bot):
    await bot.add_cog(NPCManager(bot))