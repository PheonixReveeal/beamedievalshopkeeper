-- Runs the real IntroKit module from a built IntroAssets.rbxm against R15 and R6 dummies.
-- Lune supplies Roblox's instance model (property names and types are checked against the reflection database).
-- The engine behaviour Lune doesn't have (Animator, AnimationTrack, ParticleEmitter:Emit, Heartbeat, IsStudio,
-- KeyframeSequenceProvider) is faked below and recorded so the tests can check what IntroKit did.
--   lune run tools/introgen/tests/test_introkit.luau <dir containing IntroAssets.rbxm>
local fs = require("@lune/fs")
local luau = require("@lune/luau")
local process = require("@lune/process")
local roblox = require("@lune/roblox") :: any
local Instance, CFrame, Vector3, Enum = roblox.Instance, roblox.CFrame, roblox.Vector3, roblox.Enum

local dir = process.args[1] or "assets/intro/roblox"

------------------------------------------------------------------------------------------------
-- Fakes
------------------------------------------------------------------------------------------------
local function Signal()
	local s = { handlers = {} }
	function s:Connect(fn)
		local c = { connected = true }
		function c.Disconnect()
			c.connected = false
		end
		table.insert(s.handlers, { fn = fn, c = c })
		return c
	end
	function s:Fire(...)
		for _, h in table.clone(s.handlers) do
			if h.c.connected then
				h.fn(...)
			end
		end
	end
	function s:Count()
		local n = 0
		for _, h in s.handlers do
			if h.c.connected then
				n += 1
			end
		end
		return n
	end
	return s
end

local env = { studio = true, emits = {}, warns = {}, registered = {}, loaded = {} }
local heartbeat = Signal()
local kfsById: { [string]: any } = {}

roblox.implementMethod("Instance", "WaitForChild", function(self, name)
	local c = self:FindFirstChild(name)
	assert(c, "WaitForChild would hang: " .. name)
	return c
end)
roblox.implementMethod("RunService", "IsStudio", function()
	return env.studio
end)
roblox.implementProperty("RunService", "Heartbeat", function()
	return heartbeat
end)
roblox.implementMethod("KeyframeSequenceProvider", "RegisterKeyframeSequence", function(_, kfs)
	local id = "active://" .. kfs.Name
	table.insert(env.registered, kfs.Name)
	kfsById[id] = kfs
	return id
end)
roblox.implementMethod("ParticleEmitter", "Emit", function(self, n)
	table.insert(env.emits, { name = self.Parent.Name .. "/" .. self.Name, foot = self.Parent.Parent.Name, n = n })
end)

local function kfsInfo(kfs)
	local length, markers = 0, {}
	for _, kf in kfs:GetChildren() do
		length = math.max(length, kf.Time)
		for _, m in kf:GetChildren() do
			if m.ClassName == "KeyframeMarker" then
				markers[m.Name] = true
			end
		end
	end
	return length, markers
end

roblox.implementMethod("Animator", "LoadAnimation", function(self, anim)
	local kfs = kfsById[anim.AnimationId]
	local length, loop = 1.5, false
	if kfs then
		length = kfsInfo(kfs)
		loop = kfs.Loop
	end
	local markers = {}
	local track = {
		Name = anim.Name, AnimationId = anim.AnimationId, Length = length, Looped = loop,
		IsPlaying = false, TimePosition = 0, Speed = 1, Stopped = Signal(), plays = 0, stops = 0, lastFade = nil,
	}
	function track:Play(fade, weight, speed)
		self.IsPlaying = true
		self.TimePosition = 0
		self.Speed = speed or 1
		self.plays += 1
		self.lastFade = fade
	end
	function track:Stop(fade)
		if self.IsPlaying then
			self.IsPlaying = false
			self.stops += 1
			self.lastFade = fade
			self.Stopped:Fire()
		end
	end
	function track:AdjustSpeed(s)
		self.Speed = s
	end
	function track:GetMarkerReachedSignal(name)
		markers[name] = markers[name] or Signal()
		return markers[name]
	end
	function track:_advance(dt)
		if not self.IsPlaying then
			return
		end
		self.TimePosition += dt * self.Speed
		if self.TimePosition >= self.Length then
			if self.Looped then
				self.TimePosition -= self.Length
			else
				self.TimePosition = self.Length
				self:Stop(0)
			end
		end
	end
	track.markers = markers
	table.insert(env.loaded, track)
	return track
end)

------------------------------------------------------------------------------------------------
-- World and dummies
------------------------------------------------------------------------------------------------
local game = Instance.new("DataModel")
local RS = game:GetService("ReplicatedStorage")
local bundle = roblox.deserializeModel(fs.readFile(dir .. "/IntroAssets.rbxm"))[1]
bundle.Parent = RS
local workspace = game:GetService("Workspace")

local function part(name, size, cf, parent)
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.CFrame = cf
	p.Parent = parent
	return p
end

local function r15Dummy(name)
	local m = Instance.new("Model")
	m.Name = name
	local root = part("HumanoidRootPart", Vector3.new(2, 2, 1), CFrame.new(10, 3, 5), m)
	part("RightHand", Vector3.new(1, 0.3, 1), CFrame.new(11.5, 2.2, 5), m)
	part("LeftFoot", Vector3.new(1, 0.3, 1), CFrame.new(9.5, 0.15, 5), m)
	part("RightFoot", Vector3.new(1, 0.3, 1), CFrame.new(10.5, 0.15, 5), m)
	local g = Instance.new("Attachment")
	g.Name = "RightGripAttachment"
	g.CFrame = CFrame.new(0, -0.15, 0) * CFrame.Angles(math.rad(-90), 0, 0)
	g.Parent = m.RightHand
	local h = Instance.new("Humanoid")
	h.RigType = Enum.HumanoidRigType.R15
	h.HipHeight = 2
	h.Parent = m
	m.PrimaryPart = root
	m.Parent = workspace
	return m
end

local function r6Dummy(name)
	local m = Instance.new("Model")
	m.Name = name
	part("HumanoidRootPart", Vector3.new(2, 2, 1), CFrame.new(-10, 3, 0), m)
	part("Right Arm", Vector3.new(1, 2, 1), CFrame.new(-8.5, 3, 0), m)
	part("Left Leg", Vector3.new(1, 2, 1), CFrame.new(-10.5, 1, 0), m)
	part("Right Leg", Vector3.new(1, 2, 1), CFrame.new(-9.5, 1, 0), m)
	local g = Instance.new("Attachment")
	g.Name = "RightGripAttachment"
	g.CFrame = CFrame.new(0, -1, 0) * CFrame.Angles(math.rad(-90), 0, 0)
	g.Parent = m["Right Arm"]
	local h = Instance.new("Humanoid")
	h.RigType = Enum.HumanoidRigType.R6
	h.Parent = m
	m.Parent = workspace
	return m
end

------------------------------------------------------------------------------------------------
-- Load IntroKit exactly as Roblox would (script.Parent = the bundle)
------------------------------------------------------------------------------------------------
local modules = {}
local function requireModule(ms)
	if modules[ms] then
		return modules[ms]
	end
	local fn = luau.load(ms.Source, {
		debugName = ms:GetFullName(),
		environment = {
			game = game, workspace = workspace, script = ms, require = requireModule,
			Instance = Instance, CFrame = CFrame, Vector3 = Vector3, Enum = Enum,
			warn = function(...)
				table.insert(env.warns, table.concat({ ... }, " "))
			end,
		},
	})
	modules[ms] = fn()
	return modules[ms]
end
local IntroKit = requireModule(bundle.IntroKit)

------------------------------------------------------------------------------------------------
-- Tests
------------------------------------------------------------------------------------------------
local passed, failed = 0, 0
local function test(name, fn)
	env.emits, env.warns = {}, {}
	local ok, err = pcall(fn)
	if ok then
		passed += 1
		print("  ok   " .. name)
	else
		failed += 1
		print("  FAIL " .. name .. "\n       " .. tostring(err))
	end
end
local function near(a, b, eps)
	return (a.Position - b.Position).Magnitude < (eps or 1e-3)
		and (a.LookVector - b.LookVector).Magnitude < (eps or 1e-3)
		and (a.UpVector - b.UpVector).Magnitude < (eps or 1e-3)
end
local function stepHeartbeat(seconds, dt)
	dt = dt or 1 / 60
	local t = 0
	while t < seconds do
		for _, tr in env.loaded do
			tr:_advance(dt)
		end
		heartbeat:Fire(dt)
		t += dt
	end
end

local ANIMS = {}
for _, kfs in bundle.Intro_Animations:GetChildren() do
	ANIMS[kfs.Name] = kfs
end
local IDS = requireModule(bundle.IntroKit.AnimationIds)

test("bundle has the props, effects and animations", function()
	assert(bundle.Props:FindFirstChild("Intro_BrokenSword"), "Intro_BrokenSword")
	assert(bundle.Props:FindFirstChild("Intro_BrokenSwordTool"), "Intro_BrokenSwordTool")
	assert(bundle.Effects:FindFirstChild("Intro_RunDust"), "Intro_RunDust")
	assert(bundle.Effects:FindFirstChild("Intro_SkidDust"), "Intro_SkidDust")
	assert(next(ANIMS), "no animations")
end)

test("AnimationIds lists every animation, and nothing else", function()
	for name in ANIMS do
		assert(IDS[name] ~= nil, "AnimationIds is missing " .. name)
	end
	for name in IDS do
		assert(ANIMS[name], "AnimationIds has unknown " .. name)
	end
end)

test("animations carry the markers IntroKit and the cutscene rely on", function()
	local expect = {
		Intro_PanicRun = { "FootstepL", "FootstepR" },
		Intro_ArriveStop = { "Skid", "Stop" },
		Intro_ShowBrokenSword = { "Raise", "Clink", "LookAtPlayer" },
		Intro_SlumpNotice = { "Slump", "Notice" },
		Intro_SlumpNoticeRight = { "Slump", "Notice" },
		Intro_PointShelf = { "Point" },
		Intro_Thanks = { "Bow", "Cheer" },
	}
	for name, list in expect do
		local kfs = ANIMS[name]
		assert(kfs, "missing animation " .. name)
		local _, markers = kfsInfo(kfs)
		for _, m in list do
			assert(markers[m], name .. " has no marker " .. m)
			assert(IntroKit.Markers[m] == m, "IntroKit.Markers lacks " .. m)
		end
	end
	assert(ANIMS.Intro_PanicRun.Loop and ANIMS.Intro_CatchBreath.Loop, "run and catch-breath must loop")
	for _, n in { "Intro_ArriveStop", "Intro_ShowBrokenSword", "Intro_SlumpNotice", "Intro_PointShelf", "Intro_Thanks" } do
		assert(not ANIMS[n].Loop, n .. " must not loop")
	end
	for name, kfs in ANIMS do
		assert(kfs.Priority == Enum.AnimationPriority.Action, name .. " should be Action priority")
	end
end)

local r15 = r15Dummy("Adventurer")
local r6 = r6Dummy("ClassicAdventurer")

test("AttachProp welds the sword so its grip sits on RightGripAttachment (R15)", function()
	local sword = IntroKit.AttachProp(r15, "Intro_BrokenSword")
	assert(sword and sword.Parent == r15, "prop not parented to the character")
	local handle = sword.PrimaryPart
	local weld = handle:FindFirstChild("IntroPropGrip")
	assert(weld and weld.Part0 == r15.RightHand and weld.Part1 == handle, "weld wrong")
	local handGrip = r15.RightHand.RightGripAttachment
	assert(near(weld.C0, handGrip.CFrame), "C0 should be RightGripAttachment.CFrame")
	assert(near(weld.C1, handle.GripAttachment.CFrame), "C1 should be the prop's GripAttachment")
	-- the grip frame lands exactly on the hand's grip attachment
	assert(near(handle.CFrame * handle.GripAttachment.CFrame, r15.RightHand.CFrame * handGrip.CFrame), "grip frame misplaced")
	for _, d in sword:GetDescendants() do
		if d:IsA("BasePart") then
			assert(not d.Anchored and not d.CanCollide and d.Massless, d.Name .. " should be unanchored, non-colliding, massless")
		end
	end
	-- attaching again replaces the old prop
	IntroKit.AttachProp(r15, "Intro_BrokenSword")
	local n = 0
	for _, c in r15:GetChildren() do
		if c.Name == "Intro_BrokenSword" then
			n += 1
		end
	end
	assert(n == 1, "re-attaching should replace the old prop, found " .. n)
end)

test("the sword's blade points along the grip's +Y (forward from a hanging hand)", function()
	local sword = r15:FindFirstChild("Intro_BrokenSword")
	local gripWorld = sword.PrimaryPart.CFrame * sword.PrimaryPart.GripAttachment.CFrame
	-- with the hand unrotated, R15's grip turns +Y to the character's front (-Z)
	assert((gripWorld.UpVector - Vector3.new(0, 0, -1)).Magnitude < 1e-3, "blade should point forward, got " .. tostring(gripWorld.UpVector))
	-- the blade part sits above the grip along +Y
	local blade = sword:FindFirstChild("Blade")
	if blade then
		local rel = gripWorld:PointToObjectSpace(blade.CFrame.Position) -- (Lune has no derived BasePart.Position)
		assert(rel.Y > 0.3, "blade should be toward +Y of the grip")
	end
end)

test("AttachProp works on R6 (Right Arm)", function()
	local sword = IntroKit.AttachProp(r6, "Intro_BrokenSword")
	local handle = sword.PrimaryPart
	assert(handle.IntroPropGrip.Part0 == r6["Right Arm"], "should weld to Right Arm")
	assert(near(handle.CFrame * handle.GripAttachment.CFrame, r6["Right Arm"].CFrame * r6["Right Arm"].RightGripAttachment.CFrame), "grip frame misplaced")
end)

test("unpublished animations register the bundled KeyframeSequence in Studio", function()
	env.studio = true
	env.registered = {}
	local a = IntroKit.GetAnimation("Intro_CatchBreath")
	assert(a and a.AnimationId == "active://Intro_CatchBreath", "expected a temporary id, got " .. tostring(a and a.AnimationId))
	IntroKit.GetAnimation("Intro_CatchBreath")
	assert(#env.registered == 1, "should register once and cache")
end)

test("published ids are used as rbxassetid", function()
	IDS.Intro_Thanks = 1234567
	local a = IntroKit.GetAnimation("Intro_Thanks")
	assert(a.AnimationId == "rbxassetid://1234567", a.AnimationId)
	IDS.Intro_Thanks = "7654321"
	assert(IntroKit.GetAnimation("Intro_Thanks").AnimationId == "rbxassetid://7654321")
	IDS.Intro_Thanks = 0
end)

test("unpublished animations outside Studio return nil and warn once", function()
	env.studio = false
	assert(IntroKit.GetAnimation("Intro_PointShelf") == nil)
	assert(IntroKit.GetAnimation("Intro_PointShelf") == nil)
	assert(#env.warns == 1, "expected one warning, got " .. #env.warns)
	assert(IntroKit.Play(r15, "Intro_PointShelf") == nil, "Play should return nil")
	env.studio = true
end)

test("Play loads once per character, blends, and stops the previous intro animation", function()
	local run = IntroKit.Play(r15, "Intro_PanicRun")
	assert(run and run.IsPlaying and run.lastFade == IntroKit.Settings.FadeTime, "run should play with the default fade")
	local stop = IntroKit.Play(r15, "Intro_ArriveStop", { fadeTime = 0.1 })
	assert(stop.IsPlaying and not run.IsPlaying, "playing ArriveStop should stop PanicRun")
	assert(run.lastFade == 0.1, "the previous track should fade out with the same fade time")
	local again = IntroKit.Play(r15, "Intro_PanicRun")
	assert(again == run, "tracks should be cached per animator")
	assert(r15.Humanoid:FindFirstChildOfClass("Animator"), "an Animator should be created")
end)

test("non-looping animations hold their last frame", function()
	local show = IntroKit.Play(r15, "Intro_ShowBrokenSword")
	stepHeartbeat(show.Length + 1)
	assert(show.IsPlaying, "should still be playing (held)")
	assert(show.Speed == 0, "should be frozen")
	assert(show.TimePosition > show.Length - 0.1, "should be at the end, at " .. show.TimePosition)
	local loop = IntroKit.Play(r15, "Intro_CatchBreath")
	stepHeartbeat(loop.Length * 2.5)
	assert(loop.IsPlaying and loop.Speed == 1, "a looping track keeps playing")
	local free = IntroKit.Play(r15, "Intro_PointShelf", { hold = false })
	stepHeartbeat(free.Length + 0.5)
	assert(not free.IsPlaying, "hold=false should let it end")
end)

test("hold also works at 20 fps", function()
	local t = IntroKit.Play(r15, "Intro_Thanks")
	stepHeartbeat(t.Length + 1, 1 / 20)
	assert(t.IsPlaying and t.Speed == 0, "should hold at low frame rates too")
end)

test("AttachDust puts run dust under each foot and skid dust at ground level", function()
	local dust = IntroKit.AttachDust(r15)
	local lf = r15.LeftFoot:FindFirstChild("Intro_RunDust")
	local rf = r15.RightFoot:FindFirstChild("Intro_RunDust")
	assert(lf and rf, "run dust should be on both feet")
	assert(math.abs(lf.CFrame.Position.Y + 0.15) < 1e-4, "run dust should sit at the bottom of the foot")
	local skid = r15.HumanoidRootPart:FindFirstChild("Intro_SkidDust")
	assert(skid, "skid dust on the root")
	local worldY = (r15.HumanoidRootPart.CFrame * skid.CFrame).Position.Y
	assert(math.abs(worldY - 0.05) < 1e-3, "skid dust should be at ground level, at y=" .. worldY)
	dust:Footstep("Left")
	assert(#env.emits > 0, "footstep should emit")
	for _, e in env.emits do
		assert(e.foot == "LeftFoot", "left footstep emitted from " .. e.foot)
	end
	env.emits = {}
	dust:Skid()
	local total = 0
	for _, e in env.emits do
		assert(e.foot == "HumanoidRootPart", "skid should emit from the skid attachment")
		total += e.n
	end
	assert(total > 0, "skid should emit")
	IntroKit.Settings.DustQuality = 0
	env.emits = {}
	dust:Skid()
	dust:Footstep("Right")
	assert(#env.emits == 0, "DustQuality 0 should emit nothing")
	IntroKit.Settings.DustQuality = 1
	dust:SetRunning(true)
	for _, e in lf:GetChildren() do
		if e:IsA("ParticleEmitter") then
			assert(e.Enabled, "SetRunning(true) should enable run dust")
		end
	end
	dust:SetRunning(false)
	dust:Destroy()
	assert(not r15.LeftFoot:FindFirstChild("Intro_RunDust") and not r15.HumanoidRootPart:FindFirstChild("Intro_SkidDust"), "Destroy should remove dust")
end)

test("skid dust also lands on the ground for R6", function()
	IntroKit.AttachDust(r6)
	local skid = r6.HumanoidRootPart.Intro_SkidDust
	local worldY = (r6.HumanoidRootPart.CFrame * skid.CFrame).Position.Y
	assert(math.abs(worldY - 0.05) < 1e-3, "R6 skid dust at y=" .. worldY)
	assert(r6["Left Leg"]:FindFirstChild("Intro_RunDust"), "R6 run dust on the legs")
end)

test("BindEffects turns animation markers into dust and disconnects when the track stops", function()
	local dust = IntroKit.AttachDust(r15)
	local run = IntroKit.Play(r15, "Intro_PanicRun")
	local conns = IntroKit.BindEffects(run, dust)
	assert(#conns == 3)
	env.emits = {}
	run.markers.FootstepL:Fire("")
	run.markers.FootstepR:Fire("")
	local feet = {}
	for _, e in env.emits do
		feet[e.foot] = true
	end
	assert(feet.LeftFoot and feet.RightFoot, "footstep markers should puff from both feet")
	env.emits = {}
	run.markers.Skid:Fire("")
	assert(#env.emits > 0, "Skid marker should burst")
	IntroKit.Stop(r15, "Intro_PanicRun")
	assert(run.markers.FootstepL:Count() == 0, "connections should end when the track stops")
	dust:Destroy()
end)

test("Cleanup stops intro animations and removes everything IntroKit added", function()
	IntroKit.AttachProp(r15, "Intro_BrokenSword")
	IntroKit.AttachDust(r15)
	local t = IntroKit.Play(r15, "Intro_CatchBreath")
	IntroKit.Cleanup(r15)
	assert(not t.IsPlaying, "tracks should stop")
	for _, d in r15:GetDescendants() do
		assert(not d:GetAttribute("IntroKitCreated"), "left behind: " .. d:GetFullName())
	end
	assert(r15:FindFirstChild("HumanoidRootPart") and r15:FindFirstChild("RightHand"), "must not remove the character's own parts")
end)

test("the bundled scripts compile", function()
	for _, name in { "IntroKit", "IntroDemo" } do
		local s = bundle:FindFirstChild(name)
		assert(s, name .. " missing from the bundle")
		local ok, err = pcall(luau.compile, s.Source)
		assert(ok, name .. ": " .. tostring(err))
	end
	assert(bundle.IntroDemo.ClassName == "LocalScript", "IntroDemo should be a LocalScript")
end)

test("BindEffects tolerates a nil track (animation unavailable)", function()
	local dust = IntroKit.AttachDust(r6)
	assert(#IntroKit.BindEffects(nil, dust) == 0)
	dust:Destroy()
end)

print(string.format("\n%d passed, %d failed", passed, failed))
process.exit(if failed > 0 then 1 else 0)
