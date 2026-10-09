--[[
	WeaponVFXClient (LocalScript -> StarterPlayer > StarterPlayerScripts)

	Builds effects on this player's machine for every instance tagged "WeaponVFX":
	  * a Tool (its Handle gets the effects), or
	  * a MeshPart / Model on display (shop racks, counters).
	The preset is the instance's "VFXPreset" attribute, or else its name (or its Tool's name)
	when that matches a preset, e.g. a Tool named "Voidrender".

	Swings and bursts are triggered by bumping the "VFXSwing" / "VFXBurst" number attributes on
	the tagged instance (the WeaponVFXTool script does this), so every player sees them.
]]
local CollectionService = game:GetService("CollectionService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local WeaponVFX = require(ReplicatedStorage:WaitForChild("WeaponVFX"))
local TAG = "WeaponVFX"
local localPlayer = Players.LocalPlayer

-- Lower the cost automatically on phones/tablets.
local UserInputService = game:GetService("UserInputService")
if UserInputService.TouchEnabled and not UserInputService.KeyboardEnabled then
	WeaponVFX.Settings.Quality = 0.5
end

local active = {}

local function presetFor(inst)
	local name = inst:GetAttribute("VFXPreset")
	if typeof(name) == "string" and WeaponVFX.Presets[name] then
		return name
	end
	if WeaponVFX.Presets[inst.Name] then
		return inst.Name
	end
	local tool = inst:FindFirstAncestorOfClass("Tool")
	if tool and WeaponVFX.Presets[tool.Name] then
		return tool.Name
	end
	return nil
end

local function handleOf(inst)
	if inst:IsA("Tool") then
		return inst:WaitForChild("Handle", 10)
	elseif inst:IsA("BasePart") then
		return inst
	elseif inst:IsA("Model") then
		return inst.PrimaryPart or inst:FindFirstChildWhichIsA("BasePart", true)
	end
	return nil
end

local function onAdded(inst)
	if active[inst] then
		return
	end
	local handle = handleOf(inst)
	local preset = presetFor(inst) or (handle and presetFor(handle))
	if not (handle and preset) then
		warn(("WeaponVFX: %s is tagged but has no matching preset (set a VFXPreset attribute)"):format(inst:GetFullName()))
		return
	end
	local vfx = WeaponVFX.Attach(handle, preset)
	if not vfx then
		return
	end
	active[inst] = vfx

	vfx:Bind(inst:GetAttributeChangedSignal("VFXSwing"):Connect(function()
		vfx:Swing()
	end))
	vfx:Bind(inst:GetAttributeChangedSignal("VFXBurst"):Connect(function()
		vfx:Burst()
	end))

	-- Instant feedback for the player holding the tool (the attribute echo just extends it).
	if inst:IsA("Tool") then
		vfx:Bind(inst.Activated:Connect(function()
			local character = localPlayer.Character
			if character and inst.Parent == character then
				vfx:Swing()
			end
		end))
	end
end

local function onRemoved(inst)
	local vfx = active[inst]
	if vfx then
		active[inst] = nil
		vfx:Destroy()
	end
end

CollectionService:GetInstanceAddedSignal(TAG):Connect(function(inst)
	task.spawn(onAdded, inst)
end)
CollectionService:GetInstanceRemovedSignal(TAG):Connect(onRemoved)
for _, inst in ipairs(CollectionService:GetTagged(TAG)) do
	task.spawn(onAdded, inst)
end
