-- Dumps every Pose CFrame in an animation .rbxm as JSON (used by tests/check_builder.mjs).
local fs = require("@lune/fs")
local serde = require("@lune/serde")
local process = require("@lune/process")
local roblox = require("@lune/roblox") :: any
local folder = roblox.deserializeModel(fs.readFile(process.args[1]))[1]
local out = {}
for _, kfs in folder:GetChildren() do
	local frames = {}
	for _, kf in kfs:GetChildren() do
		local poses, markers = {}, {}
		for _, d in kf:GetDescendants() do
			if d:IsA("Pose") then
				poses[d.Name] = { cf = { d.CFrame:GetComponents() }, ease = d.EasingStyle.Name, dir = d.EasingDirection.Name, parent = d.Parent.Name }
			elseif d:IsA("KeyframeMarker") then
				table.insert(markers, d.Name)
			end
		end
		table.insert(frames, { t = kf.Time, name = kf.Name, poses = poses, markers = markers })
	end
	table.sort(frames, function(a, b) return a.t < b.t end)
	out[kfs.Name] = { loop = kfs.Loop, priority = kfs.Priority.Name, hip = kfs.AuthoredHipHeight, frames = frames }
end
print(serde.encode("json", out, false))
