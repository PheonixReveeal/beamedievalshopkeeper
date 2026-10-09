--[[
	WeaponVFXTool (Script -> put one inside each special weapon's Tool)

	Tags the tool so every client builds its effects, and replicates swings/equips to all players
	by bumping attributes. The preset defaults to the Tool's name; set a "VFXPreset" attribute on
	the Tool to use a different one.

	To trigger an impact burst from your own damage code:
	    tool:SetAttribute("VFXBurst", (tool:GetAttribute("VFXBurst") or 0) + 1)
]]
local CollectionService = game:GetService("CollectionService")

local tool = script.Parent
if not tool:IsA("Tool") then
	return -- the template isn't inside a Tool yet
end

if tool:GetAttribute("VFXPreset") == nil then
	tool:SetAttribute("VFXPreset", tool.Name)
end
tool:SetAttribute("VFXSwing", 0)
tool:SetAttribute("VFXBurst", 0)
CollectionService:AddTag(tool, "WeaponVFX")

local function bump(attribute)
	tool:SetAttribute(attribute, (tool:GetAttribute(attribute) or 0) + 1)
end

tool.Activated:Connect(function()
	bump("VFXSwing")
end)
tool.Equipped:Connect(function()
	bump("VFXBurst")
end)
