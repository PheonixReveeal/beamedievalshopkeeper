-- IntroDemo: plays the whole "My Sword Broke!" opening with the intro assets, to check them in Studio.
-- It is an example, not the game's cutscene controller: no camera work, skip button or onboarding state.
--
-- Setup:
--   1. Insert IntroAssets.rbxm into ReplicatedStorage.
--   2. Make an R15 rig (Avatar tab > Rig Builder > R15 > any rig), rename it "IntroActor" and move it into ReplicatedStorage.
--   3. Move this LocalScript into StarterPlayer > StarterPlayerScripts and press Play.
-- The actor is a local copy, so it runs entirely on your client (the same way each newcomer gets their own actor).

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")

local IntroKit = require(ReplicatedStorage:WaitForChild("IntroAssets"):WaitForChild("IntroKit"))
local player = Players.LocalPlayer
local character = player.Character or player.CharacterAdded:Wait()
local playerRoot = character:WaitForChild("HumanoidRootPart") :: BasePart

local template = ReplicatedStorage:WaitForChild("IntroActor", 10)
if not template then
	warn("IntroDemo: put an R15 rig named IntroActor in ReplicatedStorage")
	return
end
task.wait(1.5)

-- subtitles
local gui = Instance.new("ScreenGui")
gui.Name = "IntroDemoSubtitles"
gui.ResetOnSpawn = false
local label = Instance.new("TextLabel")
label.AnchorPoint = Vector2.new(0.5, 1)
label.Position = UDim2.new(0.5, 0, 0.92, 0)
label.Size = UDim2.new(0.8, 0, 0, 44)
label.BackgroundTransparency = 0.35
label.BackgroundColor3 = Color3.new(0, 0, 0)
label.TextColor3 = Color3.new(1, 1, 1)
label.TextScaled = true
label.Font = Enum.Font.GothamBold
label.Text = ""
label.Visible = false
label.Parent = gui
gui.Parent = player:WaitForChild("PlayerGui")
local function say(text: string?)
	label.Text = text or ""
	label.Visible = text ~= nil
end

-- place the actor 30 studs in front of the player, facing them
local flat = Vector3.new(playerRoot.CFrame.LookVector.X, 0, playerRoot.CFrame.LookVector.Z).Unit
local stopAt = playerRoot.Position + flat * 7
local startAt = stopAt + flat * 30
local actor = template:Clone()
for _, d in actor:GetDescendants() do
	if d:IsA("BasePart") then
		d.Anchored = false
	elseif d:IsA("Script") or d:IsA("LocalScript") then
		d.Enabled = false -- e.g. an Animate script would fight the intro animations
	end
end
local humanoid = actor:FindFirstChildOfClass("Humanoid") :: Humanoid
local root = actor:FindFirstChild("HumanoidRootPart") :: BasePart
actor:PivotTo(CFrame.lookAt(startAt, stopAt))
actor.Parent = workspace

local function cleanup()
	IntroKit.Cleanup(actor)
	actor:Destroy()
	gui:Destroy()
end

local ok, err = pcall(function()
	IntroKit.AttachProp(actor, "Intro_BrokenSword")
	local dust = IntroKit.AttachDust(actor)

	-- 0-2 s: footsteps and dust puffs as they run in
	humanoid.WalkSpeed = 20
	local run = IntroKit.Play(actor, "Intro_PanicRun")
	IntroKit.BindEffects(run, dust)
	humanoid:MoveTo(stopAt)
	local t0 = os.clock()
	while (root.Position - stopAt).Magnitude > 4 and os.clock() - t0 < 4 do
		task.wait()
	end

	-- 2-4 s: awkward stop and catching breath
	local arrive = IntroKit.Play(actor, "Intro_ArriveStop", { fadeTime = 0.12 })
	IntroKit.BindEffects(arrive, dust)
	if arrive then
		arrive:GetMarkerReachedSignal(IntroKit.Markers.Skid):Wait()
	end
	-- slide a little further, then stop dead
	humanoid.WalkSpeed = 7
	humanoid:MoveTo(root.Position + root.CFrame.LookVector * 1.2)
	task.wait(0.25)
	humanoid:MoveTo(root.Position)
	if arrive then
		arrive:GetMarkerReachedSignal(IntroKit.Markers.Stop):Wait()
	end
	IntroKit.Play(actor, "Intro_CatchBreath", { fadeTime = 0.3 })
	task.wait(0.5)
	say("Shopkeeper!")
	task.wait(1.4)

	-- 4-8 s: the broken sword
	local show = IntroKit.Play(actor, "Intro_ShowBrokenSword", { fadeTime = 0.3 })
	say("My sword broke! My party's leaving without me!")
	task.wait(if show then show.Length else 3.8)

	-- 8-11 s: slump, then notice the sword display (on the actor's left here)
	local notice = IntroKit.Play(actor, "Intro_SlumpNotice", { fadeTime = 0.25 })
	say(nil)
	if notice then
		notice:GetMarkerReachedSignal(IntroKit.Markers.Notice):Wait()
	end
	say("Please tell me you have another one...")
	task.wait(1.4)

	-- 11-14 s: turn to the display and point
	TweenService:Create(root, TweenInfo.new(0.3, Enum.EasingStyle.Quad), { CFrame = root.CFrame * CFrame.Angles(0, math.rad(60), 0) }):Play()
	task.wait(0.15)
	local point = IntroKit.Play(actor, "Intro_PointShelf", { fadeTime = 0.15 })
	say("That one! I'll take it!")
	if point then
		point:GetMarkerReachedSignal(IntroKit.Markers.Point):Wait()
		print("IntroDemo: Point marker - highlight the shelf here")
	end
	task.wait(2)

	-- after checkout: relieved thanks (the real game hands them the sword they bought)
	IntroKit.DetachProp(actor)
	TweenService:Create(root, TweenInfo.new(0.3, Enum.EasingStyle.Quad), { CFrame = CFrame.lookAt(root.Position, Vector3.new(playerRoot.Position.X, root.Position.Y, playerRoot.Position.Z)) }):Play()
	task.wait(0.3)
	local thanks = IntroKit.Play(actor, "Intro_Thanks", { fadeTime = 0.2 })
	say("You saved my adventure! I'll send my friends!")
	task.wait(if thanks then thanks.Length + 0.5 else 3)
	say(nil)

	-- off they go (reusing the panic run, a little slower, as an excited jog)
	IntroKit.Play(actor, "Intro_PanicRun", { speed = 0.85 })
	humanoid.WalkSpeed = 16
	humanoid:MoveTo(startAt)
	task.wait(3)
end)
if not ok then
	warn("IntroDemo stopped: " .. tostring(err))
end
cleanup()
