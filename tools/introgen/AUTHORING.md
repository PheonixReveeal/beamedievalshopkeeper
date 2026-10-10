# Authoring the intro animations

Each animation is one JSON file in `anims/`. `build_rbxm.luau` turns it into a Roblox
`KeyframeSequence`; the previewer and linter in `preview/` show exactly what Roblox will play
(`tests/check_builder.mjs` proves the two agree).

## Format

```json
{
  "name": "Intro_CatchBreath",          // must match the file name
  "loop": true,
  "priority": "Action",                 // Idle | Movement | Action | Action2..4 | Core
  "prop": "broken",                     // preview only: broken | intact | none (sword in the right hand)
  "ease": "CubicV2", "dir": "InOut",    // defaults for every pose (these are the defaults anyway)
  "locomotion": false,                  // true for in-place run cycles (skips the foot-slide check)
  "allowContact": [["LeftHand", "LeftUpperLeg"], ["Prop", "RightUpperLeg"]],   // intended touches
  "mirrorAs": "Intro_SomethingRight",   // optional: also build a left/right mirrored copy
  "keyframes": [
    {"t": 0, "name": "Start", "markers": ["Skid"],
     "poses": {"UpperTorso": {"r": [-20, 0, 0]}, "LowerTorso": {"r": [0, 0, 0], "p": [0, -0.3, 0]},
               "RightHand": {"r": [-60, 0, 0], "ease": "Linear"}}},
    {"t": 0.4, "poses": {}}
  ]
}
```

- **A keyframe is a full pose.** A joint you don't list keeps its value from the previous keyframe
  (rest pose on the first keyframe). `r` and `p` carry over separately.
- `r` is rotation in degrees, applied like `CFrame.Angles(x, y, z)`. `p` is translation in studs.
  Only `LowerTorso` (the Root joint) should normally be translated.
- Easing (`ease`) is `Linear` or `CubicV2`, with `dir` `In` (slow start), `Out` (slow end) or `InOut`.
  A pose's easing shapes the move **from** that keyframe **to** the next one. Other styles are not
  allowed. `Cubic` is deprecated (In and Out are reversed). `Constant` holds or snaps depending on the
  direction. `Elastic` and `Bounce` aren't previewed. For a hold, repeat the pose in the next keyframe.
  For a snap, put two keyframes 1/30 s apart.
- `markers` become `KeyframeMarker`s. Listen with `track:GetMarkerReachedSignal("Skid")`.
- The last keyframe's time is the animation length. A looping animation's first and last keyframes
  must be identical.

## Joints and directions (R15)

Joints, written as the Pose name (the part the joint moves): `LowerTorso` (Root), `UpperTorso` (Waist),
`Head` (Neck), `LeftUpperArm`/`RightUpperArm` (shoulders), `LeftLowerArm`/`RightLowerArm` (elbows),
`LeftHand`/`RightHand` (wrists), `LeftUpperLeg`/`RightUpperLeg` (hips), `LeftLowerLeg`/`RightLowerLeg`
(knees), `LeftFoot`/`RightFoot` (ankles).

The character faces **-Z**, its right is **+X** and up is **+Y**. Each rotation is in the parent part's
frame, around the joint:

| Motion | Rotation |
|---|---|
| Raise an arm forward (shoulder), bend a thigh forward (hip) | **+X** |
| Bend an elbow (forearm comes forward/up) | **+X** on the LowerArm |
| Bend a knee (shin goes back) | **−X** on the LowerLeg |
| Bend the torso or head forward / down | **−X** on UpperTorso / Head |
| Lean back, look up | **+X** |
| Turn the torso or head to the character's left | **+Y** |
| Raise the right arm out to the side | **+Z** on RightUpperArm (left arm: −Z) |
| Tilt the head toward the right shoulder | **−Z** on Head |
| Point the toes down | **−X** on the Foot |

`LowerTorso` rotations rotate the whole body around the hips. When you lower the body with
`LowerTorso.p` (for example `[0, -0.4, 0]`), bend the hips and knees so the feet stay on the floor. The
linter reports feet going through the floor or sliding.

## The sword in the right hand

Props attach the way Roblox attaches tools: the RightHand's `RightGripAttachment` (-0.15 below the
hand, rotated -90° about X) is the sword frame, with +Y along the blade.

- With the arm hanging and the hand unrotated, the blade points **straight forward**.
- `RightHand.r.x` negative tilts the blade down. Our neutral stance uses `-62`, which angles it down
  and forward.
- With `RightUpperArm.r.x` about 90 (arm forward), the blade points **up**. That's the "showing the
  sword" orientation.
- The flat of the blade faces forward and back in that raised pose, so the camera in front of the
  character sees the flat and the jagged break.

Neutral stance (start and end near it so animations blend):

```json
"UpperTorso": {"r": [-3, 0, 0]}, "Head": {"r": [2, 0, 0]},
"RightUpperArm": {"r": [10, 0, 7]}, "RightLowerArm": {"r": [28, 0, 0]}, "RightHand": {"r": [-62, 0, 0]},
"LeftUpperArm": {"r": [4, 0, -6]}, "LeftLowerArm": {"r": [12, 0, 0]}
```

## Tools

Run from the repo root (the previewer needs `tools/weapongen/preview/node_modules`, see the README):

```
node tools/introgen/preview/lint.mjs Intro_CatchBreath
node tools/introgen/preview/animshot.mjs sheet out.png Intro_CatchBreath views=front0,side n=10 cols=5
node tools/introgen/preview/animshot.mjs still out.png Intro_CatchBreath t=0.8 view=close
node tools/introgen/preview/animshot.mjs frames outdir Intro_CatchBreath view=front fps=30
```

Views: `front0` (straight on, the player's view), `front` and `frontl` (3/4 from the character's right
and left), `side` (from its right; it faces screen-right), `left`, `back`, `top`, `close`. Sheets
take `times=0,0.2,0.5` to pick exact moments.
