--[[
	Texture asset ids for the weapon effects.

	1. In Studio open View > Asset Manager > Bulk Import (or Import 3D) and upload every PNG in
	   assets/vfx/textures/.
	2. Right-click each uploaded image > Copy Asset ID and paste it below, e.g.
	       Glow = "rbxassetid://1234567890",

	Until an id is filled in, that texture falls back to one of Roblox's built-in particle
	textures, so effects still show (just less detailed, and without flipbook animation).
]]
return {
	Bubble = "rbxassetid://0",
	Droplet = "rbxassetid://0",
	Ember = "rbxassetid://0",
	Flames = "rbxassetid://0", -- 4x4 flipbook
	Glow = "rbxassetid://0",
	Lightning = "rbxassetid://0", -- beam strip
	MagicCircle = "rbxassetid://0",
	Mist = "rbxassetid://0",
	Orb = "rbxassetid://0",
	Ray = "rbxassetid://0", -- beam strip
	Ring = "rbxassetid://0",
	Runes = "rbxassetid://0", -- 4x4 flipbook
	Shards = "rbxassetid://0", -- 2x2 flipbook
	Smoke = "rbxassetid://0", -- 4x4 flipbook
	Snowflake = "rbxassetid://0",
	Spark = "rbxassetid://0",
	Star = "rbxassetid://0",
	Swirl = "rbxassetid://0",
	TrailStreak = "rbxassetid://0", -- trail strip
	TrailWisp = "rbxassetid://0", -- trail strip
	Zaps = "rbxassetid://0", -- 2x2 flipbook
}
