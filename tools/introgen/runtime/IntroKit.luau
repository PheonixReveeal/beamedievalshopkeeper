-- IntroKit: helpers for the "My Sword Broke!" opening cutscene.
-- Lives at ReplicatedStorage.IntroAssets.IntroKit (inserted from IntroAssets.rbxm). Works on R15 rigs, and on R6 for props
-- and dust. Run it from the client that is watching the cutscene, so every newcomer's actor and effects stay independent.
--
--   local IntroKit = require(ReplicatedStorage.IntroAssets.IntroKit)
--   local sword = IntroKit.AttachProp(actor, "Intro_BrokenSword")      -- welded into the right hand
--   local dust = IntroKit.AttachDust(actor)                            -- footstep and skid dust
--   local run = IntroKit.Play(actor, "Intro_PanicRun")                 -- looping; markers puff dust from each foot
--   IntroKit.BindEffects(run, dust)
--   ... (move the actor with Humanoid:MoveTo) ...
--   local stop = IntroKit.Play(actor, "Intro_ArriveStop")              -- "Skid" marker bursts skid dust
--   IntroKit.BindEffects(stop, dust)
--   stop:GetMarkerReachedSignal("Stop"):Wait()
--   IntroKit.Play(actor, "Intro_CatchBreath")
--   ...
--   IntroKit.Cleanup(actor)                                            -- on skip, respawn or error
--
-- Animations come from AnimationIds (published ids). Until you publish them, in Studio the bundled KeyframeSequences are
-- registered as temporary ids, so you can test right away. In a live game an unpublished animation returns nil from
-- Play(), and the cutscene should fall back to static poses.

local RunService = game:GetService("RunService")
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")

local Assets = script.Parent
local AnimationIds = require(script:WaitForChild("AnimationIds"))

local IntroKit = {}

IntroKit.Settings = {
	DustQuality = 1, -- multiplies every dust burst; 0 turns dust off (e.g. Reduced Motion or low-end devices)
	FadeTime = 0.2, -- default blend time between animations
}

-- Markers placed in the animations
IntroKit.Markers = {
	FootstepL = "FootstepL", -- Intro_PanicRun: left foot lands
	FootstepR = "FootstepR", -- Intro_PanicRun: right foot lands
	Skid = "Skid", -- Intro_ArriveStop: front foot plants, skid starts (stop moving the actor here)
	Stop = "Stop", -- Intro_ArriveStop: came to rest
	Raise = "Raise", -- Intro_ShowBrokenSword: sword starts coming up
	Clink = "Clink", -- Intro_ShowBrokenSword: wiggles the broken blade (glint / clink moment)
	LookAtPlayer = "LookAtPlayer", -- Intro_ShowBrokenSword: turns back to the player
	Slump = "Slump", -- Intro_SlumpNotice(Right): shoulders drop
	Notice = "Notice", -- Intro_SlumpNotice(Right): spots the sword display
	Point = "Point", -- Intro_PointShelf: point lands (highlight the shelf)
	Bow = "Bow", -- Intro_Thanks
	Cheer = "Cheer", -- Intro_Thanks: raises the new sword
}

local CREATED = "IntroKitCreated" -- attribute on everything IntroKit adds to a character

local function getHumanoid(character: Model): Humanoid?
	return character:FindFirstChildOfClass("Humanoid")
end

local function getAnimator(character: Model): Animator?
	local holder: Instance? = getHumanoid(character) or character:FindFirstChildOfClass("AnimationController")
	if not holder then
		return nil
	end
	local animator = holder:FindFirstChildOfClass("Animator")
	if not animator then
		animator = Instance.new("Animator")
		animator.Parent = holder
	end
	return animator
end

------------------------------------------------------------------------------------------------
-- Props
------------------------------------------------------------------------------------------------

-- Clones a prop from IntroAssets.Props and welds it into the character's right hand, at the same grip a Tool would use.
-- Returns the prop Model. Any prop IntroKit attached before is removed first.
function IntroKit.AttachProp(character: Model, propName: string): Model?
	local template = Assets.Props:FindFirstChild(propName)
	assert(template, "IntroKit.AttachProp: no prop named " .. tostring(propName))
	local hand = character:FindFirstChild("RightHand") or character:FindFirstChild("Right Arm")
	if not (hand and hand:IsA("BasePart")) then
		warn("IntroKit.AttachProp: " .. character:GetFullName() .. " has no right hand")
		return nil
	end
	IntroKit.DetachProp(character)
	local model = template:Clone()
	local handle = model.PrimaryPart or model:FindFirstChild("Handle")
	assert(handle and handle:IsA("BasePart"), "IntroKit.AttachProp: prop has no Handle")
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = false
			d.CanCollide = false
			d.CanTouch = false
			d.CanQuery = false
			d.Massless = true
		end
	end
	local handGrip = hand:FindFirstChild("RightGripAttachment")
	local propGrip = handle:FindFirstChild("GripAttachment")
	local weld = Instance.new("Weld")
	weld.Name = "IntroPropGrip"
	weld.Part0 = hand
	weld.Part1 = handle
	-- R15 and R6 hands both carry RightGripAttachment; the fallback matches R6's.
	weld.C0 = if handGrip and handGrip:IsA("Attachment") then handGrip.CFrame else CFrame.new(0, -1, 0) * CFrame.Angles(-math.pi / 2, 0, 0)
	weld.C1 = if propGrip and propGrip:IsA("Attachment") then propGrip.CFrame else CFrame.new()
	handle.CFrame = hand.CFrame * weld.C0 * weld.C1:Inverse()
	weld.Parent = handle
	model:SetAttribute(CREATED, true)
	model.Parent = character
	return model
end

function IntroKit.DetachProp(character: Model)
	for _, child in character:GetChildren() do
		if child:IsA("Model") and child:GetAttribute(CREATED) then
			child:Destroy()
		end
	end
end

------------------------------------------------------------------------------------------------
-- Animations
------------------------------------------------------------------------------------------------

local registered: { [string]: string } = {} -- Studio-only temporary ids, per animation name
local warned: { [string]: boolean } = {}

-- Returns an Animation for one of the intro animations, or nil if it isn't published and we're not in Studio.
function IntroKit.GetAnimation(name: string): Animation?
	local id = AnimationIds[name]
	local content: string? = nil
	if type(id) == "number" and id > 0 then
		content = "rbxassetid://" .. tostring(id)
	elseif type(id) == "string" and id ~= "" and id ~= "0" then
		content = if id:match("^%d+$") then "rbxassetid://" .. id else id
	elseif RunService:IsStudio() then
		content = registered[name]
		if not content then
			local kfs = Assets.Intro_Animations:FindFirstChild(name)
			assert(kfs, "IntroKit: no animation named " .. tostring(name))
			local ok, result = pcall(function()
				return KeyframeSequenceProvider:RegisterKeyframeSequence(kfs)
			end)
			if ok then
				content = result
				registered[name] = result
			else
				warn("IntroKit: couldn't register " .. name .. ": " .. tostring(result))
			end
		end
	end
	if not content then
		if not warned[name] then
			warned[name] = true
			warn("IntroKit: " .. name .. " has no published id in IntroKit.AnimationIds; skipping it")
		end
		return nil
	end
	local anim = Instance.new("Animation")
	anim.Name = name
	anim.AnimationId = content
	return anim
end

local tracks = setmetatable({}, { __mode = "k" }) :: { [Animator]: { [string]: AnimationTrack } }

local function loadTrack(animator: Animator, name: string): AnimationTrack?
	local cache = tracks[animator]
	if not cache then
		cache = {}
		tracks[animator] = cache
	end
	if cache[name] then
		return cache[name]
	end
	local anim = IntroKit.GetAnimation(name)
	if not anim then
		return nil
	end
	local track = animator:LoadAnimation(anim)
	cache[name] = track
	return track
end

-- Freezes a non-looping track on its last frame instead of letting it end (the next Play blends out of it).
local function holdAtEnd(track: AnimationTrack)
	local conn
	conn = RunService.Heartbeat:Connect(function(dt)
		if not track.IsPlaying then
			conn:Disconnect()
			return
		end
		local length = track.Length
		if length > 0 and track.TimePosition + dt * math.max(track.Speed, 0) * 1.5 >= length then
			conn:Disconnect()
			track:AdjustSpeed(0)
			track.TimePosition = math.max(0, length - 0.02)
		end
	end)
end

export type PlayOptions = {
	fadeTime: number?, -- blend in (and blend out of other intro tracks); default Settings.FadeTime
	speed: number?,
	weight: number?,
	hold: boolean?, -- non-looping animations freeze on their last frame (default true)
	exclusive: boolean?, -- stop the other intro animations on this character (default true)
}

-- Plays an intro animation on a character. Returns the AnimationTrack, or nil if it isn't available.
function IntroKit.Play(character: Model, name: string, options: PlayOptions?): AnimationTrack?
	local opts = options or {}
	local animator = getAnimator(character)
	if not animator then
		warn("IntroKit.Play: " .. character:GetFullName() .. " has no Humanoid or AnimationController")
		return nil
	end
	local track = loadTrack(animator, name)
	if not track then
		return nil
	end
	local fade = opts.fadeTime or IntroKit.Settings.FadeTime
	if opts.exclusive ~= false then
		for other, t in tracks[animator] do
			if other ~= name and t.IsPlaying then
				t:Stop(fade)
			end
		end
	end
	track:Play(fade, opts.weight or 1, opts.speed or 1)
	if opts.hold ~= false and not track.Looped then
		holdAtEnd(track)
	end
	return track
end

-- Stops one intro animation (or all of them) on a character.
function IntroKit.Stop(character: Model, name: string?, fadeTime: number?)
	local animator = getAnimator(character)
	local cache = animator and tracks[animator]
	if not cache then
		return
	end
	for n, t in cache do
		if (name == nil or n == name) and t.IsPlaying then
			t:Stop(fadeTime or IntroKit.Settings.FadeTime)
		end
	end
end

------------------------------------------------------------------------------------------------
-- Dust
------------------------------------------------------------------------------------------------

export type Dust = {
	Footstep: (self: Dust, side: string) -> (),
	Skid: (self: Dust, scale: number?) -> (),
	SetRunning: (self: Dust, on: boolean) -> (),
	Destroy: (self: Dust) -> (),
}

local function emitAll(attachment: Attachment?, scale: number)
	if not attachment then
		return
	end
	for _, e in attachment:GetChildren() do
		if e:IsA("ParticleEmitter") then
			local n = math.floor((e:GetAttribute("EmitCount") or 4) * scale + 0.5)
			if n > 0 then
				e:Emit(n)
			end
		end
	end
end

local function cloneEffect(name: string, parent: BasePart, cf: CFrame): Attachment
	local att = Assets.Effects:FindFirstChild(name):Clone()
	att.CFrame = cf
	att:SetAttribute(CREATED, true)
	att.Parent = parent
	return att
end

-- Adds footstep dust under each foot and skid dust at ground level under the character.
function IntroKit.AttachDust(character: Model): Dust
	local root = character:FindFirstChild("HumanoidRootPart") :: BasePart
	assert(root, "IntroKit.AttachDust: character has no HumanoidRootPart")
	local humanoid = getHumanoid(character)
	local feet = {
		Left = character:FindFirstChild("LeftFoot") or character:FindFirstChild("Left Leg"),
		Right = character:FindFirstChild("RightFoot") or character:FindFirstChild("Right Leg"),
	}
	local run: { [string]: Attachment } = {}
	for side, foot in feet do
		if foot and foot:IsA("BasePart") then
			run[side] = cloneEffect("Intro_RunDust", foot, CFrame.new(0, -foot.Size.Y / 2, 0))
		end
	end
	local hip = if humanoid and humanoid.RigType == Enum.HumanoidRigType.R15 then humanoid.HipHeight else 2
	local skid = cloneEffect("Intro_SkidDust", root, CFrame.new(0, -(root.Size.Y / 2 + hip) + 0.05, -0.4))

	local dust = {}
	function dust:Footstep(side: string)
		local key = if side == "L" or side == "Left" or side == "FootstepL" then "Left" else "Right"
		emitAll(run[key], IntroKit.Settings.DustQuality)
	end
	function dust:Skid(scale: number?)
		emitAll(skid, IntroKit.Settings.DustQuality * (scale or 1))
	end
	function dust:SetRunning(on: boolean)
		for _, att in run do
			for _, e in att:GetChildren() do
				if e:IsA("ParticleEmitter") then
					e.Enabled = on and IntroKit.Settings.DustQuality > 0
				end
			end
		end
	end
	function dust:Destroy()
		for _, att in run do
			att:Destroy()
		end
		skid:Destroy()
	end
	return dust :: any
end

-- Connects a track's markers to dust: FootstepL/FootstepR puff from that foot, Skid bursts skid dust.
-- The connections end when the track stops. Returns them in case you want to end them sooner.
function IntroKit.BindEffects(track: AnimationTrack?, dust: Dust): { RBXScriptConnection }
	local conns = {}
	if not track then
		return conns
	end
	table.insert(conns, track:GetMarkerReachedSignal(IntroKit.Markers.FootstepL):Connect(function()
		dust:Footstep("Left")
	end))
	table.insert(conns, track:GetMarkerReachedSignal(IntroKit.Markers.FootstepR):Connect(function()
		dust:Footstep("Right")
	end))
	table.insert(conns, track:GetMarkerReachedSignal(IntroKit.Markers.Skid):Connect(function()
		dust:Skid()
	end))
	local stopped
	stopped = track.Stopped:Connect(function()
		for _, c in conns do
			c:Disconnect()
		end
		stopped:Disconnect()
	end)
	return conns
end

------------------------------------------------------------------------------------------------
-- Cleanup
------------------------------------------------------------------------------------------------

-- Stops the intro animations and removes every prop and effect IntroKit added to the character.
function IntroKit.Cleanup(character: Model)
	IntroKit.Stop(character, nil, 0.1)
	local doomed = {}
	for _, d in character:GetDescendants() do
		if d:GetAttribute(CREATED) then
			doomed[d] = true
		end
	end
	for d in doomed do
		-- destroy only the top-most ones; their descendants go with them
		local p, nested = d.Parent, false
		while p and p ~= character do
			if doomed[p] then
				nested = true
				break
			end
			p = p.Parent
		end
		if not nested then
			d:Destroy()
		end
	end
end

return IntroKit
