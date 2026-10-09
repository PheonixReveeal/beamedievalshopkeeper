--[[
	WeaponVFX
	Builds heavy, animated effects (particles, swing trails, crackling lightning, light shafts,
	orbiting wisps and lights) onto a weapon's MeshPart from the presets in the Presets module.

	Run it on the CLIENT (see WeaponVFXClient): every player builds their own copy, so nothing is
	replicated per frame and each player's settings (quality, culling) stay local.

		local WeaponVFX = require(ReplicatedStorage.WeaponVFX)
		local vfx = WeaponVFX.Attach(handle, "Voidrender")   -- idle aura starts immediately
		vfx:Swing()         -- swing trail + swing particles for Settings.SwingDuration
		vfx:Burst()         -- one-shot impact / equip burst
		vfx:SetEnabled(false)
		vfx:Destroy()
]]

local RunService = game:GetService("RunService")
local Workspace = game:GetService("Workspace")

local Presets = require(script:WaitForChild("Presets"))
local Textures = require(script:WaitForChild("Textures"))

local WeaponVFX = {}
WeaponVFX.Presets = Presets

WeaponVFX.Settings = {
	Quality = 1, -- particle-rate multiplier: 0.35 for low-end devices, 1 = as designed, 1.5 = extra heavy
	DisplayRate = 0.6, -- rate multiplier while a weapon is NOT held (shop racks, counters)
	CullDistance = 140, -- effects pause when the camera is farther than this (studs)
	SwingDuration = 0.35, -- seconds the swing trail/particles stay on per Swing()
	FlipXZ = false, -- set true if effects appear mirrored front-to-back on your imported meshes
}

-- Fallbacks so effects still show before you upload the textures (see the Textures module).
local BUILTIN = {
	Flames = "rbxasset://textures/particles/fire_main.dds",
	Smoke = "rbxasset://textures/particles/smoke_main.dds",
	Mist = "rbxasset://textures/particles/smoke_main.dds",
}
local DEFAULT_TEXTURE = "rbxasset://textures/particles/sparkles_main.dds"

local function textureFor(name)
	local id = Textures[name]
	if typeof(id) == "string" and id ~= "" and id ~= "rbxassetid://0" then
		return id, true
	end
	return BUILTIN[name] or DEFAULT_TEXTURE, false
end

-- Newer properties (Brightness, flipbooks, emitter shapes) are set defensively so the module
-- keeps working on clients/engines that don't have them.
local function trySet(inst, prop, value)
	pcall(function()
		inst[prop] = value
	end)
end

local function numberSequence(points, scale)
	scale = scale or 1
	local kps = table.create(#points)
	for i, p in ipairs(points) do
		kps[i] = NumberSequenceKeypoint.new(p[1], p[2] * scale, (p[3] or 0) * scale)
	end
	return NumberSequence.new(kps)
end

local function colorSequence(points)
	local kps = table.create(#points)
	for i, p in ipairs(points) do
		kps[i] = ColorSequenceKeypoint.new(p[1], Color3.new(p[2][1], p[2][2], p[2][3]))
	end
	return ColorSequence.new(kps)
end

local MIRROR_FACE = { Front = "Back", Back = "Front", Left = "Right", Right = "Left" }

local function isHeld(handle)
	local tool = handle:FindFirstAncestorOfClass("Tool")
	local owner = tool and tool.Parent
	return owner ~= nil and owner:FindFirstChildOfClass("Humanoid") ~= nil
end

local function randomInBox(rng, center, size)
	return center + Vector3.new(
		(rng:NextNumber() - 0.5) * size.X,
		(rng:NextNumber() - 0.5) * size.Y,
		(rng:NextNumber() - 0.5) * size.Z
	)
end

local function basis(axis)
	local ref = math.abs(axis.Y) < 0.9 and Vector3.yAxis or Vector3.xAxis
	local u = axis:Cross(ref).Unit
	return u, axis:Cross(u).Unit
end

----------------------------------------------------------------------------------------------
local Controller = {}
Controller.__index = Controller

local controllers = {}
local loopConnection = nil
local lastVisibilityCheck = 0

local function step()
	local now = os.clock()
	local camera = Workspace.CurrentCamera
	if camera and now - lastVisibilityCheck > 0.25 then
		lastVisibilityCheck = now
		local camPos = camera.CFrame.Position
		for c in pairs(controllers) do
			c:_checkVisibility(camPos)
		end
	end
	for c in pairs(controllers) do
		if c.visible and c.enabled then
			c:_animate(now)
		end
		if c.swinging and now >= c.swingUntil then
			c.swinging = false
			c:_refresh()
		end
	end
end

local function ensureLoop()
	if not loopConnection then
		loopConnection = RunService.Heartbeat:Connect(step)
	end
end

function WeaponVFX.Attach(handle, presetName)
	local preset = Presets[presetName]
	if not preset then
		warn(("WeaponVFX: no preset named %q"):format(tostring(presetName)))
		return nil
	end
	assert(typeof(handle) == "Instance" and handle:IsA("BasePart"), "WeaponVFX.Attach needs a BasePart")

	local settings = WeaponVFX.Settings
	local flip = settings.FlipXZ
	local ms = preset.meshSize
	-- Presets are authored at the mesh's imported size; follow any resizing in Studio.
	local scale = Vector3.new(handle.Size.X / ms[1], handle.Size.Y / ms[2], handle.Size.Z / ms[3])
	local k = (scale.X + scale.Y + scale.Z) / 3

	local self = setmetatable({
		handle = handle,
		preset = preset,
		name = presetName,
		k = k,
		created = {},
		connections = {},
		anchors = {},
		regions = {},
		orbitSets = {},
		orbitByName = {},
		emitters = {},
		trails = {},
		staticBeams = {},
		bolts = {},
		raySets = {},
		lights = {},
		enabled = true,
		visible = false,
		held = false,
		swinging = false,
		swingUntil = 0,
		rng = Random.new(),
		seed = math.random() * 100,
	}, Controller)

	local function vec(t)
		local x, y, z = t[1], t[2], t[3]
		if flip then
			x, z = -x, -z
		end
		return Vector3.new(x, y, z)
	end
	local function pos(t)
		return vec(t) * scale
	end
	local function attachment(name, position)
		local a = Instance.new("Attachment")
		a.Name = "VFX_" .. name
		a.Position = position
		a.Parent = handle
		table.insert(self.created, a)
		return a
	end
	local function box(b)
		return { center = pos(b.center), size = Vector3.new(b.size[1] * scale.X, b.size[2] * scale.Y, b.size[3] * scale.Z) }
	end

	local folder = Instance.new("Folder")
	folder.Name = "WeaponVFX"
	folder.Parent = handle
	table.insert(self.created, folder)
	self.folder = folder

	for name, p in pairs(preset.anchors or {}) do
		self.anchors[name] = attachment(name, pos(p))
	end

	-- Invisible welded parts give emitters a volume to spawn from (the blade, the axe head...).
	for name, r in pairs(preset.regions or {}) do
		local part = Instance.new("Part")
		part.Name = "VFX_" .. name
		part.Size = Vector3.new(
			math.max(r.size[1] * scale.X, 0.05),
			math.max(r.size[2] * scale.Y, 0.05),
			math.max(r.size[3] * scale.Z, 0.05)
		)
		part.Transparency = 1
		part.CanCollide = false
		part.CanTouch = false
		part.CanQuery = false
		part.CastShadow = false
		part.Massless = true
		part.Anchored = false
		part.CFrame = handle.CFrame * CFrame.new(pos(r.center))
		local weld = Instance.new("WeldConstraint")
		weld.Part0 = handle
		weld.Part1 = part
		weld.Parent = part
		part.Parent = folder
		self.regions[name] = part
	end

	for _, o in ipairs(preset.orbits or {}) do
		local axis = vec(o.axis).Unit
		local u0 = basis(axis)
		local set = { def = o, center = pos(o.center), radius = o.radius * k, list = {} }
		for i = 1, o.count do
			local tilt = (o.tilt or 0) * (((i - 1) % 3) - 1)
			local ax = CFrame.fromAxisAngle(u0, tilt):VectorToWorldSpace(axis)
			local u, v = basis(ax)
			table.insert(set.list, { att = attachment(o.name .. i, set.center), axis = ax, u = u, v = v, phase = (i - 1) * 2 * math.pi / o.count })
		end
		table.insert(self.orbitSets, set)
		local atts = {}
		for _, item in ipairs(set.list) do
			table.insert(atts, item.att)
		end
		self.orbitByName[o.name] = atts
	end

	-- Particle emitters.
	for _, def in ipairs(preset.emitters or {}) do
		local parents
		if string.sub(def.at, 1, 6) == "orbit:" then
			parents = self.orbitByName[string.sub(def.at, 7)] or {}
		elseif self.regions[def.at] then
			parents = { self.regions[def.at] }
		elseif self.anchors[def.at] then
			parents = { self.anchors[def.at] }
		else
			warn(("WeaponVFX: %s/%s has unknown location %q"):format(presetName, def.name, def.at))
			parents = {}
		end
		for _, parent in ipairs(parents) do
			local e = Instance.new("ParticleEmitter")
			e.Name = def.name
			local texture, uploaded = textureFor(def.texture)
			e.Texture = texture
			if def.flipbook and uploaded then
				trySet(e, "FlipbookLayout", def.flipbook == "4x4" and Enum.ParticleFlipbookLayout.Grid4x4 or Enum.ParticleFlipbookLayout.Grid2x2)
				trySet(e, "FlipbookMode", Enum.ParticleFlipbookMode[def.flipMode or "Loop"])
				trySet(e, "FlipbookFramerate", NumberRange.new(def.fps[1], def.fps[2]))
				trySet(e, "FlipbookStartRandom", def.flipRandomStart == true)
			end
			e.Color = colorSequence(def.color)
			e.Size = numberSequence(def.size, k)
			e.Transparency = numberSequence(def.transparency)
			if def.squash then
				e.Squash = numberSequence(def.squash)
			end
			e.Lifetime = NumberRange.new(def.lifetime[1], def.lifetime[2])
			e.Speed = NumberRange.new(def.speed[1] * k, def.speed[2] * k)
			e.SpreadAngle = Vector2.new(def.spread[1], def.spread[2])
			e.Acceleration = vec(def.accel) * k
			e.Drag = def.drag or 0
			e.Rotation = NumberRange.new(def.rotation[1], def.rotation[2])
			e.RotSpeed = NumberRange.new(def.rotSpeed[1], def.rotSpeed[2])
			e.LightEmission = def.lightEmission or 0
			e.LightInfluence = def.lightInfluence or 0
			trySet(e, "Brightness", def.brightness or 1)
			e.ZOffset = def.zOffset or 0
			e.Orientation = Enum.ParticleOrientation[def.orientation or "FacingCamera"]
			local face = def.direction or "Top"
			if flip and MIRROR_FACE[face] then
				face = MIRROR_FACE[face]
			end
			e.EmissionDirection = Enum.NormalId[face]
			e.LockedToPart = def.locked == true
			e.VelocityInheritance = def.velInherit or 0
			if parent:IsA("BasePart") then
				trySet(e, "Shape", Enum.ParticleEmitterShape[def.shape or "Box"])
				trySet(e, "ShapeStyle", Enum.ParticleEmitterShapeStyle[def.shapeStyle or "Volume"])
				trySet(e, "ShapeInOut", Enum.ParticleEmitterShapeInOut[def.shapeInOut or "Outward"])
			end
			e.Rate = 0
			e.Enabled = false
			e.Parent = parent
			table.insert(self.emitters, { inst = e, def = def })
		end
	end

	-- Swing trails.
	for _, def in ipairs(preset.trails or {}) do
		local tr = Instance.new("Trail")
		tr.Name = def.name
		tr.Attachment0 = self.anchors[def.a0]
		tr.Attachment1 = self.anchors[def.a1]
		tr.Texture = (textureFor(def.texture))
		tr.TextureMode = Enum.TextureMode.Stretch
		tr.Color = colorSequence(def.color)
		tr.Transparency = numberSequence(def.transparency)
		tr.WidthScale = numberSequence(def.width)
		tr.Lifetime = def.lifetime
		tr.LightEmission = def.lightEmission or 1
		tr.LightInfluence = 0
		tr.FaceCamera = def.faceCamera == true
		tr.MinLength = 0.05
		trySet(tr, "Brightness", def.brightness or 1)
		tr.Enabled = false
		tr.Parent = folder
		table.insert(self.trails, { inst = tr, def = def })
	end

	-- Beams: static glows, crackling bolts and rotating light shafts.
	local function makeBeam(def, a0, a1, width0, width1)
		local b = Instance.new("Beam")
		b.Name = def.name
		b.Attachment0 = a0
		b.Attachment1 = a1
		b.Texture = (textureFor(def.texture))
		b.TextureMode = Enum.TextureMode.Wrap
		b.TextureLength = (def.textureLength or 1) * k
		b.TextureSpeed = def.textureSpeed or 0
		b.Width0 = width0 * k
		b.Width1 = width1 * k
		b.Segments = def.segments or 10
		b.Color = colorSequence(def.color)
		b.Transparency = numberSequence(def.transparency)
		b.LightEmission = def.lightEmission or 1
		b.LightInfluence = 0
		b.FaceCamera = true
		trySet(b, "Brightness", def.brightness or 1)
		b.Enabled = false
		b.Parent = folder
		return b
	end

	for _, def in ipairs(preset.beams or {}) do
		if def.kind == "beam" then
			local b = makeBeam(def, self.anchors[def.a0], self.anchors[def.a1], def.width[1], def.width[2])
			b.CurveSize0 = def.curve[1] * k
			b.CurveSize1 = def.curve[2] * k
			table.insert(self.staticBeams, b)
		elseif def.kind == "bolt" then
			local function endpoint(spec, label)
				if typeof(spec) == "string" then
					return { att = self.anchors[spec] }
				end
				local bx = box(spec)
				return { att = attachment(def.name .. label, bx.center), box = bx }
			end
			local from, to = endpoint(def.frm, "A"), endpoint(def.to, "B")
			local b = makeBeam(def, from.att, to.att, def.width[1], def.width[2])
			table.insert(self.bolts, { beam = b, def = def, from = from, to = to, nextFlick = 0 })
		elseif def.kind == "rays" then
			local source = self.anchors[def.at]
			local axis = vec(def.axis).Unit
			local u, v = basis(axis)
			local set = { def = def, source = source, axis = axis, u = u, v = v, list = {} }
			for i = 1, def.count do
				local tip = attachment(def.name .. i, source.Position)
				local b = makeBeam(def, source, tip, def.width[1], def.width[2])
				local tilt = math.rad(def.cone) * (0.35 + 0.65 * ((i * 0.618) % 1))
				table.insert(set.list, { tip = tip, beam = b, tilt = tilt, phase = (i - 1) * 2 * math.pi / def.count })
			end
			table.insert(self.raySets, set)
		end
	end

	for _, def in ipairs(preset.lights or {}) do
		local l = Instance.new("PointLight")
		l.Color = Color3.new(def.color[1], def.color[2], def.color[3])
		l.Brightness = def.brightness
		l.Range = def.range * k
		l.Shadows = false
		l.Enabled = false
		l.Parent = self.anchors[def.at]
		table.insert(self.lights, { inst = l, def = def })
	end

	controllers[self] = true
	ensureLoop()
	local camera = Workspace.CurrentCamera
	self:_checkVisibility(camera and camera.CFrame.Position or handle.Position)
	return self
end

----------------------------------------------------------------------------------------------
function Controller:_refresh()
	local settings = WeaponVFX.Settings
	local on = self.enabled and self.visible
	local mult = settings.Quality * (self.held and 1 or settings.DisplayRate)
	for _, e in ipairs(self.emitters) do
		local mode = e.def.mode
		if mode == "idle" then
			e.inst.Rate = e.def.rate * mult
			e.inst.Enabled = on
		elseif mode == "swing" then
			e.inst.Rate = e.def.rate * settings.Quality
			e.inst.Enabled = on and self.swinging
		else
			e.inst.Enabled = false
		end
	end
	for _, t in ipairs(self.trails) do
		t.inst.Enabled = on and (t.def.mode == "always" or self.swinging)
	end
	for _, b in ipairs(self.staticBeams) do
		b.Enabled = on
	end
	for _, set in ipairs(self.raySets) do
		for _, r in ipairs(set.list) do
			r.beam.Enabled = on
		end
	end
	if not on then
		for _, bolt in ipairs(self.bolts) do
			bolt.beam.Enabled = false
		end
	end
	for _, l in ipairs(self.lights) do
		l.inst.Enabled = on
	end
end

function Controller:_checkVisibility(camPos)
	local handle = self.handle
	local visible = handle:IsDescendantOf(Workspace)
		and (handle.Position - camPos).Magnitude <= WeaponVFX.Settings.CullDistance
	local held = isHeld(handle)
	if visible ~= self.visible or held ~= self.held then
		self.visible, self.held = visible, held
		self:_refresh()
	end
end

function Controller:_animate(now)
	local t = now
	for _, set in ipairs(self.orbitSets) do
		local o = set.def
		for _, item in ipairs(set.list) do
			local a = item.phase + o.speed * t
			local r = set.radius * (1 + 0.15 * (o.wobble or 0) * math.sin(a * 1.7))
			local bob = item.axis * (set.radius * 0.35 * (o.wobble or 0) * math.sin(a * 2.3 + item.phase))
			item.att.Position = set.center + (item.u * math.cos(a) + item.v * math.sin(a)) * r + bob
		end
	end

	local rng = self.rng
	for _, bolt in ipairs(self.bolts) do
		if now >= bolt.nextFlick then
			local def = bolt.def
			bolt.nextFlick = now + rng:NextNumber(def.interval[1], def.interval[2])
			if bolt.from.box then
				bolt.from.att.Position = randomInBox(rng, bolt.from.box.center, bolt.from.box.size)
			end
			if bolt.to.box then
				bolt.to.att.Position = randomInBox(rng, bolt.to.box.center, bolt.to.box.size)
			end
			local c = def.curve * self.k
			bolt.beam.CurveSize0 = rng:NextNumber(-c, c)
			bolt.beam.CurveSize1 = rng:NextNumber(-c, c)
			bolt.beam.TextureSpeed = (rng:NextNumber() < 0.5 and -1 or 1) * def.textureSpeed
			bolt.beam.Enabled = rng:NextNumber() < def.chance
		end
	end

	for _, set in ipairs(self.raySets) do
		local def = set.def
		local base = set.source.Position
		for i, r in ipairs(set.list) do
			local a = r.phase + def.speed * t
			local len = def.length * self.k * (0.85 + 0.15 * math.sin(t * 1.3 + i))
			local dir = set.axis * math.cos(r.tilt) + (set.u * math.cos(a) + set.v * math.sin(a)) * math.sin(r.tilt)
			r.tip.Position = base + dir * len
		end
	end

	for i, l in ipairs(self.lights) do
		local def = l.def
		local b = def.brightness
		if def.pulse[2] > 0 then
			b *= 1 + def.pulse[2] * math.sin(t * def.pulse[1] * 2 * math.pi)
		end
		if def.flicker > 0 then
			b *= 1 + def.flicker * math.noise(t * 9, self.seed + i)
		end
		l.inst.Brightness = math.max(b, 0)
	end
end

-- Public API ---------------------------------------------------------------------------------

function Controller:Swing(duration)
	local now = os.clock()
	local wasSwinging = now < self.swingUntil
	self.swingUntil = math.max(self.swingUntil, now + (duration or WeaponVFX.Settings.SwingDuration))
	if not wasSwinging then
		self.swinging = true
		self:_refresh()
	end
end

function Controller:Burst(scale)
	if not (self.visible and self.enabled) then
		return
	end
	local q = WeaponVFX.Settings.Quality * (scale or 1)
	for _, e in ipairs(self.emitters) do
		if e.def.mode == "burst" and e.def.burst > 0 then
			e.inst:Emit(math.max(1, math.floor(e.def.burst * q + 0.5)))
		end
	end
end

function Controller:SetEnabled(on)
	self.enabled = on and true or false
	self:_refresh()
end

function Controller:Bind(connection)
	table.insert(self.connections, connection)
	return connection
end

function Controller:Destroy()
	controllers[self] = nil
	for _, c in ipairs(self.connections) do
		c:Disconnect()
	end
	for _, inst in ipairs(self.created) do
		inst:Destroy()
	end
	table.clear(self.created)
	if next(controllers) == nil and loopConnection then
		loopConnection:Disconnect()
		loopConnection = nil
	end
end

-- Re-apply rates after changing WeaponVFX.Settings at runtime.
function WeaponVFX.Refresh()
	for c in pairs(controllers) do
		c:_refresh()
	end
end

return WeaponVFX
