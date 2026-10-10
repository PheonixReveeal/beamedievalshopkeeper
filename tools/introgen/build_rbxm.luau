--!strict
-- Builds the intro cutscene assets as Roblox model files (.rbxm) with Lune (https://lune-org.github.io).
--   lune run tools/introgen/build_rbxm.luau [out_dir]        (default out_dir: assets/intro/roblox)
-- Sources (all JSON, editable):
--   props/Intro_BrokenSword.json   the sword, built from ordinary Parts (no mesh upload needed)
--   props/Intro_Dust.json          the dust particle prefabs
--   anims/*.json                   R15 animations -> KeyframeSequences (files starting with "_" are skipped)
--   runtime/*.luau                 scripts packed into the bundle
-- Every property goes through Roblox's reflection database, so a wrong name, type or enum fails the build.
local fs = require("@lune/fs")
local serde = require("@lune/serde")
local process = require("@lune/process")
local roblox = require("@lune/roblox") :: any

local Instance, Vector3, Vector2, CFrame, Color3 = roblox.Instance, roblox.Vector3, roblox.Vector2, roblox.CFrame, roblox.Color3
local NumberSequence, NumberSequenceKeypoint = roblox.NumberSequence, roblox.NumberSequenceKeypoint
local ColorSequence, ColorSequenceKeypoint, NumberRange, Enum = roblox.ColorSequence, roblox.ColorSequenceKeypoint, roblox.NumberRange, roblox.Enum
local db = roblox.getReflectionDatabase()

local HERE = "tools/introgen/"
local OUT = process.args[1] or "assets/intro/roblox"
local function readJson(path: string): any
	return serde.decode("json", fs.readFile(path))
end
local rig = readJson(HERE .. "rig_r15.json")

------------------------------------------------------------------------------------------------
-- Generic, reflection-checked property conversion
------------------------------------------------------------------------------------------------
local function datatypeOf(className: string, prop: string): string?
	local c = db:GetClass(className)
	while c do
		local p = c.Properties[prop]
		if p then
			return p.Datatype
		end
		c = if c.Superclass then db:GetClass(c.Superclass) else nil
	end
	return nil
end

local function rad(v: { number }): (number, number, number)
	return math.rad(v[1] or 0), math.rad(v[2] or 0), math.rad(v[3] or 0)
end

-- CFrame from {pos = {x,y,z}, rot = {x,y,z} degrees as CFrame.Angles}
local function toCFrame(v: any): any
	local p = v.pos or { 0, 0, 0 }
	return CFrame.new(p[1], p[2], p[3]) * CFrame.Angles(rad(v.rot or { 0, 0, 0 }))
end

local function rgb(c: { number }): any
	return Color3.fromRGB(c[1], c[2], c[3])
end

local function convert(dt: string, v: any, where: string): any
	if dt == "Bool" then
		assert(type(v) == "boolean", where .. ": expected a boolean")
		return v
	elseif dt:match("^Float") or dt:match("^Int") then
		assert(type(v) == "number", where .. ": expected a number")
		return v
	elseif dt == "String" or dt == "ContentId" or dt == "Content" then
		assert(type(v) == "string", where .. ": expected a string")
		return v
	elseif dt == "Vector3" then
		return Vector3.new(v[1], v[2], v[3])
	elseif dt == "Vector2" then
		return Vector2.new(v[1], v[2])
	elseif dt == "Color3" then
		return rgb(v)
	elseif dt == "CFrame" then
		return toCFrame(v)
	elseif dt == "NumberRange" then
		if type(v) == "number" then
			return NumberRange.new(v)
		end
		return NumberRange.new(v[1], v[2])
	elseif dt == "NumberSequence" then
		if type(v) == "number" then
			return NumberSequence.new(v)
		end
		local kps = {}
		for _, k in v do
			table.insert(kps, NumberSequenceKeypoint.new(k[1], k[2], k[3] or 0))
		end
		return NumberSequence.new(kps)
	elseif dt == "ColorSequence" then
		if type(v[1]) == "number" then
			return ColorSequence.new(rgb(v))
		end
		local kps = {}
		for _, k in v do
			table.insert(kps, ColorSequenceKeypoint.new(k[1], rgb(k[2])))
		end
		return ColorSequence.new(kps)
	elseif dt:sub(1, 5) == "Enum." then
		local enumName = dt:sub(6)
		local item = (Enum :: any)[enumName][v]
		assert(item, `{where}: {v} is not an Enum.{enumName} item`)
		return item
	end
	error(`{where}: unsupported datatype {dt}`)
end

local function setProps(inst: any, props: { [string]: any }?)
	for key, value in props or {} do
		local where = `{inst.ClassName}.{key} ({inst.Name})`
		local dt = datatypeOf(inst.ClassName, key)
		assert(dt, where .. ": not a property of " .. inst.ClassName)
		inst[key] = convert(dt :: string, value, where)
	end
end

-- {class, name, props, attributes, tags, children}
local function fromSpec(spec: any, nameOverride: string?): any
	local inst = Instance.new(spec.class)
	inst.Name = nameOverride or spec.name or spec.class
	setProps(inst, spec.props)
	for k, v in spec.attributes or {} do
		inst:SetAttribute(k, v)
	end
	for _, t in spec.tags or {} do
		inst:AddTag(t)
	end
	for _, c in spec.children or {} do
		fromSpec(c).Parent = inst
	end
	return inst
end

------------------------------------------------------------------------------------------------
-- Sword: Parts welded to the Handle; grip frame = sword frame (+Y toward the tip)
------------------------------------------------------------------------------------------------
local PART_DEFAULTS = {
	Anchored = false,
	CanCollide = false,
	CanTouch = false,
	CanQuery = false,
	Massless = true,
	CastShadow = true,
}

local function buildPart(pt: any, gripCF: any): any
	local p = Instance.new(pt.class or "Part")
	p.Name = pt.name
	for k, v in PART_DEFAULTS do
		p[k] = v
	end
	p.TopSurface = Enum.SurfaceType.Smooth
	p.BottomSurface = Enum.SurfaceType.Smooth
	if (pt.class or "Part") == "Part" then
		p.Shape = Enum.PartType[pt.shape or "Block"]
	end
	p.Size = Vector3.new(pt.size[1], pt.size[2], pt.size[3])
	p.Color = rgb(pt.color)
	p.Material = Enum.Material[pt.material or "SmoothPlastic"]
	if pt.reflectance then
		p.Reflectance = pt.reflectance
	end
	if pt.transparency then
		p.Transparency = pt.transparency
	end
	p.CFrame = gripCF * toCFrame(pt)
	if pt.props then
		setProps(p, pt.props)
	end
	return p
end

-- Builds the parts of a prop into `container`; returns the Handle.
local function buildProp(spec: any, parts: { any }, container: any, gripCF: any): any
	local handle
	local built = {}
	for _, pt in parts do
		local p = buildPart(pt, gripCF)
		p.Parent = container
		table.insert(built, p)
		if pt.name == "Handle" then
			handle = p
		end
	end
	assert(handle, spec.name .. ": needs a part named Handle")
	for _, p in built do
		if p ~= handle then
			local w = Instance.new("WeldConstraint")
			w.Name = "WeldToHandle"
			w.Part0 = handle
			w.Part1 = p
			w.Parent = p
		end
	end
	local grip = Instance.new("Attachment")
	grip.Name = "GripAttachment"
	grip.CFrame = handle.CFrame:Inverse() * gripCF
	grip.Parent = handle
	return handle
end

local function swordModel(spec: any, parts: { any }, name: string): any
	local gripCF = CFrame.new(0, 3, 0) -- upright, grip 3 studs above the origin
	local model = Instance.new("Model")
	model.Name = name
	local handle = buildProp(spec, parts, model, gripCF)
	model.PrimaryPart = handle
	model.WorldPivotData = gripCF
	model:SetAttribute("GripOffset", (handle.CFrame:Inverse() * gripCF).Position)
	return model, handle
end

local function swordTool(spec: any, name: string): any
	local tool = Instance.new("Tool")
	tool.Name = name
	tool.CanBeDropped = false
	tool.RequiresHandle = true
	tool.ToolTip = spec.toolTip or "Broken sword"
	local gripCF = CFrame.new(0, 3, 0)
	local handle = buildProp(spec, spec.parts, tool, gripCF)
	tool.Grip = handle.GripAttachment.CFrame
	return tool
end

------------------------------------------------------------------------------------------------
-- Animations: authored JSON -> KeyframeSequence (same semantics as preview/anim.js)
------------------------------------------------------------------------------------------------
local JOINT_PARENT: { [string]: string } = {}
local ORDER: { string } = {}
for _, j in rig.joints do
	JOINT_PARENT[j.part1] = j.part0
	table.insert(ORDER, j.part1)
end
local EASE_OK = { Linear = true, CubicV2 = true } -- no Constant: see preview/anim.js
local DIR_OK = { In = true, Out = true, InOut = true }

local function mirrorAnim(anim: any, newName: string): any
	local function swap(n: string): string
		if n:sub(1, 4) == "Left" then
			return "Right" .. n:sub(5)
		elseif n:sub(1, 5) == "Right" then
			return "Left" .. n:sub(6)
		end
		return n
	end
	local function swapMarker(s: string): string
		return (s:gsub("Left", "\0"):gsub("Right", "Left"):gsub("%z", "Right"))
	end
	local m = serde.decode("json", serde.encode("json", anim))
	m.name = newName
	m.mirrorAs = nil
	for _, k in m.keyframes do
		local poses = {}
		for n, s in k.poses or {} do
			local t = table.clone(s)
			if s.r then
				t.r = { s.r[1], -s.r[2], -s.r[3] }
			end
			if s.p then
				t.p = { -s.p[1], s.p[2], s.p[3] }
			end
			poses[swap(n)] = t
		end
		k.poses = poses
		if k.markers then
			for i, mk in k.markers do
				if type(mk) == "string" then
					k.markers[i] = swapMarker(mk)
				else
					mk.name = swapMarker(mk.name)
				end
			end
		end
	end
	return m
end

-- Fully keyed poses per keyframe (a joint not listed keeps the previous keyframe's value).
local function prepare(anim: any): { any }
	local keys = table.clone(anim.keyframes)
	table.sort(keys, function(a, b)
		return a.t < b.t
	end)
	local prev = {}
	for _, n in ORDER do
		prev[n] = { r = { 0, 0, 0 }, p = { 0, 0, 0 } }
	end
	local out = {}
	for _, k in keys do
		for n in k.poses or {} do
			assert(JOINT_PARENT[n], `{anim.name}: unknown joint {n}`)
		end
		local kf = { t = k.t, name = k.name or "Keyframe", markers = k.markers or {}, poses = {} }
		for _, n in ORDER do
			local s = (k.poses or {})[n] or {}
			local r, p = s.r or prev[n].r, s.p or prev[n].p
			local style = s.ease or k.ease or anim.ease or "CubicV2"
			local dir = s.dir or k.dir or anim.dir or "InOut"
			assert(EASE_OK[style], `{anim.name} t={k.t} {n}: easing {style} not allowed`)
			assert(DIR_OK[dir], `{anim.name} t={k.t} {n}: direction {dir} not allowed`)
			kf.poses[n] = { r = r, p = p, ease = style, dir = dir }
			prev[n] = { r = r, p = p }
		end
		table.insert(out, kf)
	end
	return out
end

local function keyframeSequence(anim: any): any
	local kfs = Instance.new("KeyframeSequence")
	kfs.Name = anim.name
	kfs.Loop = anim.loop == true
	kfs.Priority = Enum.AnimationPriority[anim.priority or "Action"]
	kfs.AuthoredHipHeight = rig.hipHeight
	for _, k in prepare(anim) do
		local kf = Instance.new("Keyframe")
		kf.Name = k.name
		kf.Time = k.t
		local rootPose = Instance.new("Pose")
		rootPose.Name = rig.root.part
		rootPose.Weight = 1
		rootPose.Parent = kf
		local made = { [rig.root.part] = rootPose }
		for _, n in ORDER do -- rig.joints is ordered parents-first
			local s = k.poses[n]
			local pose = Instance.new("Pose")
			pose.Name = n
			pose.Weight = 1
			pose.CFrame = CFrame.new(s.p[1], s.p[2], s.p[3]) * CFrame.Angles(rad(s.r))
			pose.EasingStyle = Enum.PoseEasingStyle[s.ease]
			pose.EasingDirection = Enum.PoseEasingDirection[s.dir]
			pose.Parent = made[JOINT_PARENT[n]]
			made[n] = pose
		end
		for _, mk in k.markers do
			local marker = Instance.new("KeyframeMarker")
			marker.Name = if type(mk) == "string" then mk else mk.name
			marker.Value = if type(mk) == "table" and mk.value then tostring(mk.value) else ""
			marker.Parent = kf
		end
		kf.Parent = kfs
	end
	return kfs
end

------------------------------------------------------------------------------------------------
-- Build
------------------------------------------------------------------------------------------------
fs.writeDir(OUT)
local written: { [string]: number } = {}
local function save(file: string, roots: { any })
	local bytes = roblox.serializeModel(roots)
	fs.writeFile(OUT .. "/" .. file, bytes)
	written[file] = #bytes
end

-- Sword
local swordSpec = readJson(HERE .. "props/Intro_BrokenSword.json")
local sword = swordModel(swordSpec, swordSpec.parts, "Intro_BrokenSword")
local tool = swordTool(swordSpec, "Intro_BrokenSwordTool")
local tip
if swordSpec.tip then
	tip = Instance.new("Model")
	tip.Name = "Intro_BrokenSwordTip"
	local gripCF = CFrame.new(0, 3, 0)
	local first
	for _, pt in swordSpec.tip do
		local p = buildPart(pt, gripCF)
		p.Parent = tip
		first = first or p
	end
	for _, p in tip:GetChildren() do
		if p ~= first then
			local w = Instance.new("WeldConstraint")
			w.Name = "WeldToRoot"
			w.Part0 = first
			w.Part1 = p
			w.Parent = p
		end
	end
	tip.PrimaryPart = first
	tip.WorldPivotData = first.CFrame
end
save("Intro_BrokenSword.rbxm", { sword })
save("Intro_BrokenSwordTool.rbxm", { tool })
if tip then
	save("Intro_BrokenSwordTip.rbxm", { tip })
end

-- Dust
local dustSpec = readJson(HERE .. "props/Intro_Dust.json")
local dust = {}
for _, name in { "Intro_RunDust", "Intro_SkidDust" } do
	assert(dustSpec[name], "Intro_Dust.json needs " .. name)
	dust[name] = fromSpec(dustSpec[name], name)
	save(name .. ".rbxm", { dust[name] })
end

-- Animations
local animFolder = Instance.new("Folder")
animFolder.Name = "Intro_Animations"
local animNames = {}
local dump = {}
for _, file in fs.readDir(HERE .. "anims") do
	if file:sub(-5) == ".json" and file:sub(1, 1) ~= "_" then
		local anim = readJson(HERE .. "anims/" .. file)
		assert(anim.name == file:sub(1, -6), file .. ": name field must match the file name")
		local variants = { anim }
		if anim.mirrorAs then
			table.insert(variants, mirrorAnim(anim, anim.mirrorAs))
		end
		for _, a in variants do
			local kfs = keyframeSequence(a)
			kfs.Parent = animFolder
			table.insert(animNames, a.name)
			dump[a.name] = prepare(a)
		end
	end
end
table.sort(animNames)
save("Intro_Animations.rbxm", { animFolder })
fs.writeFile(OUT .. "/../anim_dump.json", serde.encode("json", dump, false)) -- used by tests/check_builder.mjs

-- Everything in one bundle, plus the runtime module
local bundle = Instance.new("Folder")
bundle.Name = "IntroAssets"
local kit = Instance.new("ModuleScript")
kit.Name = "IntroKit"
kit.Source = fs.readFile(HERE .. "runtime/IntroKit.luau")
kit.Parent = bundle
local ids = Instance.new("ModuleScript")
ids.Name = "AnimationIds"
ids.Source = fs.readFile(HERE .. "runtime/AnimationIds.luau")
ids.Parent = kit
local demo = Instance.new("LocalScript")
demo.Name = "IntroDemo" -- inert in ReplicatedStorage; move to StarterPlayerScripts to run the demo
demo.Source = fs.readFile(HERE .. "runtime/IntroDemo.client.luau")
demo.Parent = bundle
local props = Instance.new("Folder")
props.Name = "Props"
props.Parent = bundle
sword:Clone().Parent = props
tool:Clone().Parent = props
if tip then
	tip:Clone().Parent = props
end
local fx = Instance.new("Folder")
fx.Name = "Effects"
fx.Parent = bundle
for _, d in dust do
	d:Clone().Parent = fx
end
animFolder:Clone().Parent = bundle
save("IntroAssets.rbxm", { bundle })

------------------------------------------------------------------------------------------------
-- Read everything back and check it survived serialization
------------------------------------------------------------------------------------------------
local function load(file: string): { any }
	return roblox.deserializeModel(fs.readFile(OUT .. "/" .. file))
end
local problems = {}
local function check(cond: any, msg: string)
	if not cond then
		table.insert(problems, msg)
	end
end
do
	local m = load("Intro_BrokenSword.rbxm")[1]
	check(m.ClassName == "Model" and m.PrimaryPart and m.PrimaryPart.Name == "Handle", "sword: PrimaryPart should be Handle")
	local g = m.PrimaryPart:FindFirstChild("GripAttachment")
	check(g, "sword: GripAttachment missing")
	check(m.WorldPivotData and (m.WorldPivotData.Position - (m.PrimaryPart.CFrame * g.CFrame).Position).Magnitude < 1e-4,
		"sword: WorldPivot should sit at the grip")
	local welds = 0
	for _, d in m:GetDescendants() do
		if d:IsA("WeldConstraint") then
			welds += 1
			check(d.Part0 == m.PrimaryPart, "sword: weld not to Handle")
		end
	end
	check(welds == #swordSpec.parts - 1, "sword: every part except Handle should be welded")
	local t = load("Intro_BrokenSwordTool.rbxm")[1]
	check(t.ClassName == "Tool" and t:FindFirstChild("Handle"), "tool: Handle missing")
	check((t.Grip.Position - t.Handle.GripAttachment.CFrame.Position).Magnitude < 1e-4, "tool: Grip should equal GripAttachment")
end
for _, name in { "Intro_RunDust", "Intro_SkidDust" } do
	local a = load(name .. ".rbxm")[1]
	local n = 0
	for _, d in a:GetDescendants() do
		if d:IsA("ParticleEmitter") then
			n += 1
		end
	end
	check(n > 0, name .. ": no ParticleEmitter")
end
do
	local f = load("Intro_Animations.rbxm")[1]
	for _, name in animNames do
		local kfs = f:FindFirstChild(name)
		check(kfs and kfs.ClassName == "KeyframeSequence", name .. ": missing")
		if kfs then
			local frames = kfs:GetChildren()
			check(#frames == #dump[name], `{name}: {#frames} keyframes, expected {#dump[name]}`)
			for _, kf in frames do
				local poses = 0
				for _, d in kf:GetDescendants() do
					if d:IsA("Pose") then
						poses += 1
					end
				end
				check(poses == #rig.joints + 1, `{name} t={kf.Time}: {poses} poses, expected {#rig.joints + 1}`)
			end
		end
	end
	local b = load("IntroAssets.rbxm")[1]
	check(b:FindFirstChild("IntroKit") and b.IntroKit:FindFirstChild("AnimationIds"), "bundle: IntroKit/AnimationIds missing")
	check(b:FindFirstChild("Props") and b.Props:FindFirstChild("Intro_BrokenSword"), "bundle: Props missing")
	check(b:FindFirstChild("Intro_Animations") and #b.Intro_Animations:GetChildren() == #animNames, "bundle: animations missing")
end

local names = {}
for k in written do
	table.insert(names, k)
end
table.sort(names)
for _, k in names do
	print(string.format("  %-28s %7d bytes", k, written[k]))
end
print("  animations: " .. table.concat(animNames, ", "))
if #problems > 0 then
	for _, p in problems do
		print("PROBLEM: " .. p)
	end
	process.exit(1)
end
print("OK: all files read back correctly")
