--!nocheck
-- A strict, minimal mock of the Roblox API used by WeaponVFX, for running it under the Luau CLI.
-- Unknown properties, wrong value types, bad enum names and malformed sequences raise errors,
-- the way they would in Studio.

local T = 0
local os = { clock = function() return T end, time = os.time }
local function advance(dt) T += dt end

local function typeof(x)
	if type(x) == "table" and rawget(x, "__type") then
		return rawget(x, "__type")
	end
	local mt = type(x) == "table" and getmetatable(x)
	if mt and mt.__type then
		return mt.__type
	end
	return type(x)
end

-- Vector3 ---------------------------------------------------------------------------------
local V3 = {}
V3.__type = "Vector3"
local function v3(x, y, z) return setmetatable({ X = x, Y = y, Z = z }, V3) end
V3.__index = function(v, k)
	if k == "Magnitude" then return math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z) end
	if k == "Unit" then local m = math.sqrt(v.X * v.X + v.Y * v.Y + v.Z * v.Z); assert(m > 0, "Unit of zero vector"); return v3(v.X / m, v.Y / m, v.Z / m) end
	if k == "Cross" then return function(a, b) return v3(a.Y * b.Z - a.Z * b.Y, a.Z * b.X - a.X * b.Z, a.X * b.Y - a.Y * b.X) end end
	if k == "Dot" then return function(a, b) return a.X * b.X + a.Y * b.Y + a.Z * b.Z end end
	error("Vector3 has no member " .. tostring(k))
end
V3.__add = function(a, b) return v3(a.X + b.X, a.Y + b.Y, a.Z + b.Z) end
V3.__sub = function(a, b) return v3(a.X - b.X, a.Y - b.Y, a.Z - b.Z) end
V3.__unm = function(a) return v3(-a.X, -a.Y, -a.Z) end
V3.__mul = function(a, b)
	if type(a) == "number" then a, b = b, a end
	if type(b) == "number" then return v3(a.X * b, a.Y * b, a.Z * b) end
	return v3(a.X * b.X, a.Y * b.Y, a.Z * b.Z)
end
V3.__div = function(a, b) return v3(a.X / b, a.Y / b, a.Z / b) end
local Vector3 = { new = function(x, y, z)
	assert(type(x) == "number" and type(y) == "number" and type(z) == "number", "Vector3.new expects numbers")
	return v3(x, y, z)
end }
Vector3.zero, Vector3.xAxis, Vector3.yAxis, Vector3.zAxis = v3(0, 0, 0), v3(1, 0, 0), v3(0, 1, 0), v3(0, 0, 1)

local Vector2 = { new = function(x, y) return { __type = "Vector2", X = x, Y = y } end }

-- CFrame (rotation rows r + position p) --------------------------------------------------------
local CF = {}
CF.__type = "CFrame"
local function cf(r, p) return setmetatable({ r = r, p = p }, CF) end
local I3 = { { 1, 0, 0 }, { 0, 1, 0 }, { 0, 0, 1 } }
local function rotv(r, v)
	return v3(r[1][1] * v.X + r[1][2] * v.Y + r[1][3] * v.Z, r[2][1] * v.X + r[2][2] * v.Y + r[2][3] * v.Z,
		r[3][1] * v.X + r[3][2] * v.Y + r[3][3] * v.Z)
end
CF.__index = function(c, k)
	if k == "Position" then return c.p end
	if k == "VectorToWorldSpace" then return function(self, v) return rotv(self.r, v) end end
	error("CFrame has no member " .. tostring(k))
end
CF.__mul = function(a, b)
	if typeof(b) == "Vector3" then return rotv(a.r, b) + a.p end
	local r = {}
	for i = 1, 3 do
		r[i] = {}
		for j = 1, 3 do
			r[i][j] = a.r[i][1] * b.r[1][j] + a.r[i][2] * b.r[2][j] + a.r[i][3] * b.r[3][j]
		end
	end
	return cf(r, rotv(a.r, b.p) + a.p)
end
local CFrame = {
	new = function(x, y, z)
		if typeof(x) == "Vector3" then return cf(I3, x) end
		return cf(I3, v3(x or 0, y or 0, z or 0))
	end,
	fromAxisAngle = function(axis, a)
		local u = axis.Unit
		local c, s, t = math.cos(a), math.sin(a), 1 - math.cos(a)
		local x, y, z = u.X, u.Y, u.Z
		return cf({ { t * x * x + c, t * x * y - s * z, t * x * z + s * y }, { t * x * y + s * z, t * y * y + c, t * y * z - s * x },
			{ t * x * z - s * y, t * y * z + s * x, t * z * z + c } }, v3(0, 0, 0))
	end,
}

-- Value types -----------------------------------------------------------------------------
local Color3 = { new = function(r, g, b)
	for _, c in ipairs({ r, g, b }) do assert(type(c) == "number" and c >= 0 and c <= 1, "Color3 component out of range") end
	return { __type = "Color3", R = r, G = g, B = b }
end }
local NumberRange = { new = function(a, b)
	b = b or a
	assert(type(a) == "number" and type(b) == "number", "NumberRange expects numbers")
	if a > b then error(("NumberRange: min %s > max %s"):format(a, b)) end
	return { __type = "NumberRange", Min = a, Max = b }
end }
local function checkTimes(kps, what)
	assert(#kps >= 2, what .. " needs at least 2 keypoints")
	assert(#kps <= 20, what .. " has more than 20 keypoints")
	assert(kps[1].Time == 0, what .. " must start at time 0")
	assert(kps[#kps].Time == 1, what .. " must end at time 1")
	for i = 2, #kps do assert(kps[i].Time > kps[i - 1].Time, what .. " times must increase") end
end
local NumberSequenceKeypoint = { new = function(t, v, e)
	assert(type(t) == "number" and type(v) == "number", "NumberSequenceKeypoint expects numbers")
	return { __type = "NumberSequenceKeypoint", Time = t, Value = v, Envelope = e or 0 }
end }
local NumberSequence = { new = function(kps) checkTimes(kps, "NumberSequence"); return { __type = "NumberSequence", Keypoints = kps } end }
local ColorSequenceKeypoint = { new = function(t, c)
	assert(typeof(c) == "Color3", "ColorSequenceKeypoint needs a Color3")
	return { __type = "ColorSequenceKeypoint", Time = t, Value = c }
end }
local ColorSequence = { new = function(kps) checkTimes(kps, "ColorSequence"); return { __type = "ColorSequence", Keypoints = kps } end }

local RandomMT = { __index = { NextNumber = function(self, a, b)
	self.s = (self.s * 1103515245 + 12345) % 2147483648
	local x = self.s / 2147483648
	if a then return a + (b - a) * x end
	return x
end } }
local Random = { new = function(seed) return setmetatable({ s = seed or 12345 }, RandomMT) end }

-- Enums -----------------------------------------------------------------------------------
local ENUMS = {
	ParticleFlipbookLayout = { "None", "Grid2x2", "Grid4x4", "Grid8x8" },
	ParticleFlipbookMode = { "Loop", "OneShot", "PingPong", "Random" },
	ParticleOrientation = { "FacingCamera", "FacingCameraWorldUp", "VelocityParallel", "VelocityPerpendicular" },
	NormalId = { "Right", "Top", "Back", "Left", "Bottom", "Front" },
	ParticleEmitterShape = { "Box", "Sphere", "Cylinder", "Disc" },
	ParticleEmitterShapeStyle = { "Volume", "Surface" },
	ParticleEmitterShapeInOut = { "Outward", "Inward", "InAndOut" },
	TextureMode = { "Stretch", "Wrap", "Static" },
}
local Enum = setmetatable({}, { __index = function(_, typeName)
	local items = ENUMS[typeName] or error("Unknown enum type Enum." .. tostring(typeName))
	return setmetatable({}, { __index = function(_, name)
		for _, n in ipairs(items) do
			if n == name then return { __type = "EnumItem", EnumType = typeName, Name = name } end
		end
		error(("%s is not a valid member of Enum.%s"):format(tostring(name), typeName))
	end })
end })

-- Instances -------------------------------------------------------------------------------
local function enumOf(t) return function(v) return typeof(v) == "EnumItem" and v.EnumType == t end end
local function is(t) return function(v) return typeof(v) == t end end
local num, bool, str = is("number"), is("boolean"), is("string")
local anyInst = function(v) return v == nil or typeof(v) == "Instance" end
local common = { Name = str, Parent = anyInst }
local PROPS = {
	Folder = {},
	Attachment = { Position = is("Vector3") },
	WeldConstraint = { Part0 = anyInst, Part1 = anyInst },
	Part = { Size = is("Vector3"), Transparency = num, CanCollide = bool, CanTouch = bool, CanQuery = bool, CastShadow = bool,
		Massless = bool, Anchored = bool, CFrame = is("CFrame") },
	ParticleEmitter = { Texture = str, FlipbookLayout = enumOf("ParticleFlipbookLayout"), FlipbookMode = enumOf("ParticleFlipbookMode"),
		FlipbookFramerate = is("NumberRange"), FlipbookStartRandom = bool, Color = is("ColorSequence"), Size = is("NumberSequence"),
		Transparency = is("NumberSequence"), Squash = is("NumberSequence"), Lifetime = is("NumberRange"), Speed = is("NumberRange"),
		SpreadAngle = is("Vector2"), Acceleration = is("Vector3"), Drag = num, Rotation = is("NumberRange"), RotSpeed = is("NumberRange"),
		LightEmission = num, LightInfluence = num, Brightness = num, ZOffset = num, Orientation = enumOf("ParticleOrientation"),
		EmissionDirection = enumOf("NormalId"), LockedToPart = bool, VelocityInheritance = num, Shape = enumOf("ParticleEmitterShape"),
		ShapeStyle = enumOf("ParticleEmitterShapeStyle"), ShapeInOut = enumOf("ParticleEmitterShapeInOut"), Rate = num, Enabled = bool },
	Trail = { Attachment0 = anyInst, Attachment1 = anyInst, Texture = str, TextureMode = enumOf("TextureMode"), Color = is("ColorSequence"),
		Transparency = is("NumberSequence"), WidthScale = is("NumberSequence"), Lifetime = num, LightEmission = num, LightInfluence = num,
		FaceCamera = bool, MinLength = num, Brightness = num, Enabled = bool },
	Beam = { Attachment0 = anyInst, Attachment1 = anyInst, Texture = str, TextureMode = enumOf("TextureMode"), TextureLength = num,
		TextureSpeed = num, Width0 = num, Width1 = num, Segments = num, Color = is("ColorSequence"), Transparency = is("NumberSequence"),
		LightEmission = num, LightInfluence = num, FaceCamera = bool, Brightness = num, Enabled = bool, CurveSize0 = num, CurveSize1 = num },
	PointLight = { Color = is("Color3"), Brightness = num, Range = num, Shadows = bool, Enabled = bool },
	Tool = {}, Model = {}, Humanoid = {}, Workspace = {}, Camera = { CFrame = is("CFrame") },
}
PROPS.MeshPart = PROPS.Part
local IS = { MeshPart = { "BasePart", "Part" }, Part = { "BasePart" } }

local stats = { created = {}, live = 0, emitted = 0 }
local Inst = {}
local methods = {}
local function newInstance(class)
	assert(PROPS[class], "Instance.new: unsupported class " .. tostring(class))
	local o = setmetatable({ __props = { Name = class, ClassName = class }, __children = {}, __attrs = {}, __alive = true, __class = class }, Inst)
	stats.created[class] = (stats.created[class] or 0) + 1
	stats.live += 1
	return o
end
Inst.__type = "Instance"
Inst.__index = function(o, k)
	if methods[k] then return methods[k] end
	if k == "Position" and (o.__class == "Part" or o.__class == "MeshPart") then
		return o.__props.CFrame and o.__props.CFrame.p or v3(0, 0, 0)
	end
	local v = o.__props[k]
	if v ~= nil then return v end
	if k == "Parent" or k == "Attachment0" or k == "Attachment1" or k == "Part0" or k == "Part1" or k == "CurrentCamera" then return nil end
	if PROPS[o.__class][k] or common[k] then return nil end
	local child = methods.FindFirstChild(o, k)
	if child then return child end
	error(("%s is not a valid member of %s"):format(tostring(k), o.__class))
end
Inst.__newindex = function(o, k, v)
	assert(o.__alive, "setting " .. k .. " on a destroyed instance")
	local check = PROPS[o.__class][k] or common[k]
	if not check then error(("%s is not a valid property of %s"):format(tostring(k), o.__class)) end
	if not check(v) then error(("bad value for %s.%s (%s)"):format(o.__class, k, typeof(v))) end
	if k == "Parent" then
		local old = o.__props.Parent
		if old then
			for i, c in ipairs(old.__children) do if c == o then table.remove(old.__children, i) break end end
		end
		if v then table.insert(v.__children, o) end
	end
	if k == "Size" and (o.__class == "Part" or o.__class == "MeshPart") then
		assert(v.X > 0 and v.Y > 0 and v.Z > 0, "part size must be positive")
	end
	o.__props[k] = v
end
function methods.IsA(o, c)
	if o.__class == c or c == "Instance" then return true end
	for _, x in ipairs(IS[o.__class] or {}) do if x == c then return true end end
	return false
end
function methods.FindFirstChild(o, name)
	for _, c in ipairs(o.__children) do if c.__props.Name == name then return c end end
	return nil
end
function methods.WaitForChild(o, name) return methods.FindFirstChild(o, name) or error("WaitForChild: missing " .. name) end
function methods.FindFirstChildOfClass(o, c)
	for _, x in ipairs(o.__children) do if x.__class == c then return x end end
	return nil
end
function methods.FindFirstChildWhichIsA(o, c)
	for _, x in ipairs(o.__children) do if methods.IsA(x, c) then return x end end
	return nil
end
function methods.FindFirstAncestorOfClass(o, c)
	local p = o.__props.Parent
	while p do
		if p.__class == c then return p end
		p = p.__props.Parent
	end
	return nil
end
function methods.IsDescendantOf(o, a)
	local p = o.__props.Parent
	while p do
		if p == a then return true end
		p = p.__props.Parent
	end
	return false
end
function methods.Destroy(o)
	if not o.__alive then return end
	for _, c in ipairs(table.clone(o.__children)) do methods.Destroy(c) end
	o.Parent = nil
	o.__alive = false
	stats.live -= 1
end
function methods.GetFullName(o) return o.__props.Name end
function methods.GetAttribute(o, k) return o.__attrs[k] end
function methods.SetAttribute(o, k, v) o.__attrs[k] = v end
function methods.Emit(o, n)
	assert(o.__class == "ParticleEmitter", "Emit on non-emitter")
	assert(type(n) == "number" and n >= 1 and n == math.floor(n), "Emit count must be a positive integer")
	stats.emitted += n
end
function methods.GetChildren(o) return table.clone(o.__children) end
function methods.GetDescendants(o)
	local out = {}
	local function walk(x) for _, c in ipairs(x.__children) do table.insert(out, c); walk(c) end end
	walk(o)
	return out
end

local Instance = { new = newInstance }

-- Services ----------------------------------------------------------------------------------
local heartbeat = {}
local workspace = newInstance("Workspace")
local camera = newInstance("Camera")
camera.CFrame = CFrame.new(0, 2, 12)
workspace.__props.CurrentCamera = camera
local RunService = { Heartbeat = { Connect = function(_, fn)
	table.insert(heartbeat, fn)
	return { Disconnect = function() for i, f in ipairs(heartbeat) do if f == fn then table.remove(heartbeat, i) break end end end }
end } }
local game = { GetService = function(_, name)
	if name == "RunService" then return RunService end
	if name == "Workspace" then return workspace end
	error("mock: unsupported service " .. name)
end }
local function runFrames(n, dt)
	for _ = 1, n do
		advance(dt)
		for _, fn in ipairs(table.clone(heartbeat)) do fn(dt) end
	end
end
