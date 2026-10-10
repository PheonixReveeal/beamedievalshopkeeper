# Intro cutscene assets: "My Sword Broke!"

Everything from the **Effects and Asset Request** except the audio (dropped by request):

| Asset | What it is | File |
|---|---|---|
| `Intro_BrokenSword` | Low-poly broken sword made from ordinary Parts, so there's nothing to upload. The pivot sits at the grip. | `roblox/Intro_BrokenSword.rbxm` |
| `Intro_BrokenSwordTool` | The same sword as a Tool, with `Tool.Grip` already set | `roblox/Intro_BrokenSwordTool.rbxm` |
| `Intro_BrokenSwordTip` | The snapped-off piece (optional prop) | `roblox/Intro_BrokenSwordTip.rbxm` |
| `Intro_RunDust` | Beige footstep dust puffs (Attachment with a ParticleEmitter) | `roblox/Intro_RunDust.rbxm` |
| `Intro_SkidDust` | Brief, low dust burst for the stop | `roblox/Intro_SkidDust.rbxm` |
| Animations | 8 R15 `KeyframeSequence`s you can edit and publish | `roblox/Intro_Animations.rbxm` |
| **Everything** | All of the above, plus the `IntroKit` helper module and a demo script | `roblox/IntroAssets.rbxm` |

ANIMATION_TABLE

## Quick start

1. In Studio, right-click **ReplicatedStorage > Insert from File…** and pick `roblox/IntroAssets.rbxm`.
2. **Try it.** Build an R15 rig (Avatar tab > Rig Builder > R15), rename it `IntroActor` and move it into
   ReplicatedStorage. Then move `IntroAssets > IntroDemo` into StarterPlayer > StarterPlayerScripts and
   press Play. The demo plays the whole opening in front of you. It works before you publish anything,
   because in Studio IntroKit registers the bundled KeyframeSequences as temporary animations.
3. **Publish the animations** (needed for live servers, see below), paste the ids into
   `IntroAssets > IntroKit > AnimationIds`, and move `IntroDemo` back out of StarterPlayerScripts.

## Using IntroKit in your cutscene controller

```lua
local IntroKit = require(ReplicatedStorage.IntroAssets.IntroKit)

local sword = IntroKit.AttachProp(actor, "Intro_BrokenSword")   -- welded at RightGripAttachment
local dust = IntroKit.AttachDust(actor)                         -- dust under each foot + skid dust

local run = IntroKit.Play(actor, "Intro_PanicRun")              -- looping; puffs dust on each footstep
IntroKit.BindEffects(run, dust)
humanoid:MoveTo(stopPoint)

local stop = IntroKit.Play(actor, "Intro_ArriveStop")           -- "Skid" marker bursts the skid dust
IntroKit.BindEffects(stop, dust)
stop:GetMarkerReachedSignal("Skid"):Wait()                      -- stop moving the actor here
stop:GetMarkerReachedSignal("Stop"):Wait()
IntroKit.Play(actor, "Intro_CatchBreath")
-- ... Intro_ShowBrokenSword, Intro_SlumpNotice / Intro_SlumpNoticeRight, Intro_PointShelf, later Intro_Thanks

IntroKit.Cleanup(actor)                                         -- on Skip, respawn, disconnect or error
```

- `IntroKit.Play(character, name, {fadeTime, speed, weight, hold, exclusive})` returns the AnimationTrack,
  or `nil` if the animation isn't available, so your cutscene can fall back to static poses. It
  crossfades from whatever intro animation was playing. Non-looping animations **hold their last
  frame** until the next one starts (pass `hold = false` to let them end).
- `IntroKit.AttachProp(character, "Intro_BrokenSword")` works on R15 (RightHand) and R6 (Right Arm). It
  uses the same grip a Tool would, so the blade lines up with any animation made for tools.
- `IntroKit.AttachDust(character)` returns `dust:Footstep("Left"|"Right")`, `dust:Skid(scale)`,
  `dust:SetRunning(on)` and `dust:Destroy()`. `IntroKit.Settings.DustQuality` scales every burst; set
  it to 0 to turn dust off.
- `IntroKit.Cleanup(character)` stops the intro animations and removes every prop and effect IntroKit
  added.
- Run IntroKit on the **client that watches the cutscene** (each newcomer gets their own actor). Its
  `Emit` bursts are local, and so are the Studio-only temporary animation ids.
- The game turns the actor to face the shelf before `Intro_PointShelf`; the point goes straight ahead.
  Use `Intro_SlumpNotice` when the display is on the actor's left, or `Intro_SlumpNoticeRight` when
  it's on their right.

### Markers

MARKER_TABLE

## Publishing the animations (to get ids)

Animations have to be owned by the account or group that owns the experience, so publish them from
that account. For each KeyframeSequence in `IntroAssets > Intro_Animations`, either:

- **Right-click it > Save to Roblox…**, pick the owner (you or your group), and publish. Or:
- Put a copy in **ServerStorage > RBX_ANIMSAVES > (your rig's name)**. Open the rig in the
  **Animation Editor**, choose **… > Load** and pick it, then **… > Publish to Roblox**. You can also
  tweak it there first.

Copy each new id into `IntroKit > AnimationIds` (for example `Intro_CatchBreath = 1234567890`). Ids still at
0 are skipped in live servers, with one warning each.

## The sword

![Intro_BrokenSword](previews/Intro_BrokenSword.png)

- Built from Parts with Roblox materials, so there's nothing to upload and it streams like any part.
- `Handle` is the grip. It's the Model's `PrimaryPart`, and the Model's pivot sits at the grip. A
  `GripAttachment` inside the Handle marks the grip frame: +Y runs up the blade, the same convention
  as the shop weapons.
- All parts are unanchored, massless and non-colliding, and welded to the Handle. Anchor the Handle
  for a static display.
- For a player Tool, use `Intro_BrokenSwordTool`. Its `Grip` equals the GripAttachment.

## The dust

DUST_SECTION

## Editing and regenerating

The sources live in `tools/introgen/` as plain JSON, and the build turns them into the `.rbxm` files:

```
tools/introgen/anims/*.json         one file per animation (format: tools/introgen/AUTHORING.md)
tools/introgen/props/*.json         the sword parts and the dust emitters
tools/introgen/runtime/*.luau       IntroKit, AnimationIds, IntroDemo
```

```
lune run tools/introgen/build_rbxm.luau                 # writes assets/intro/roblox/*.rbxm
sh tools/introgen/tests/run_all.sh lune                 # lint, build, rbxm-vs-preview check, IntroKit tests
sh tools/introgen/render_previews.sh                    # sheets and animated previews
node tools/introgen/preview/seqshot.mjs out_dir         # the full opening as frames (animatic)
```

[Lune](https://github.com/lune-org/lune) 0.10 builds the files (`cargo install lune --locked`, or a
release binary). It checks every property against Roblox's reflection database, so a wrong property,
type or enum fails the build instead of being silently dropped by Studio. The previews need Node with
`three` and `playwright` (`tools/weapongen/preview`).
