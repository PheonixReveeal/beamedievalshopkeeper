"""Run WeaponVFX under the Luau CLI against a strict Roblox mock.

    python tools/vfxgen/tests/run_tests.py <path/to/luau>

Checks every preset: attach, idle animation, swing on/off, burst, distance culling, held vs
display rates, resized + mirrored handles, and that Destroy() cleans up every instance.
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
VFX = os.path.join(ROOT, "assets", "vfx")

TESTS = r'''
local Presets = __modules.Presets
local names = {}
for n in pairs(Presets) do table.insert(names, n) end
table.sort(names)

local function count(list, pred)
	local n = 0
	for _, x in ipairs(list) do if pred(x) then n += 1 end end
	return n
end

local function makeWeapon(name, size, held)
	local holder = workspace
	if held then
		local character = newInstance("Model")
		character.Name = "Character"
		newInstance("Humanoid").Parent = character
		character.Parent = workspace
		holder = character
	end
	local tool = newInstance("Tool")
	tool.Name = name
	local handle = newInstance("MeshPart")
	handle.Name = "Handle"
	handle.Size = size
	handle.CFrame = CFrame.new(0, 3, 0)
	handle.Parent = tool
	tool.Parent = holder
	return tool, handle
end

local totalInstances = 0
for _, name in ipairs(names) do
	local p = Presets[name]
	local size = Vector3.new(p.meshSize[1], p.meshSize[2], p.meshSize[3])
	local tool, handle = makeWeapon(name, size, false)
	local liveBefore = stats.live
	local c = WeaponVFX.Attach(handle, name)
	assert(c, name .. ": attach failed")
	local made = stats.live - liveBefore
	totalInstances += made
	runFrames(90, 1 / 60)

	local idle = count(c.emitters, function(e) return e.def.mode == "idle" end)
	local idleOn = count(c.emitters, function(e) return e.def.mode == "idle" and e.inst.Enabled end)
	assert(idle > 0 and idleOn == idle, name .. ": idle emitters should be on")
	local displayRate = c.emitters[1].inst.Rate
	for _, l in ipairs(c.lights) do assert(l.inst.Enabled and l.inst.Brightness >= 0, name .. ": light") end

	-- Swing turns trails / swing emitters on, then off again.
	c:Swing()
	runFrames(3, 1 / 60)
	for _, t in ipairs(c.trails) do assert(t.inst.Enabled, name .. ": trail should be on mid-swing") end
	assert(count(c.emitters, function(e) return e.def.mode == "swing" and not e.inst.Enabled end) == 0, name .. ": swing emitters")
	runFrames(40, 1 / 60)
	for _, t in ipairs(c.trails) do assert(not t.inst.Enabled, name .. ": trail should stop after the swing") end

	-- Burst emits.
	local before = stats.emitted
	c:Burst()
	assert(stats.emitted > before, name .. ": burst emitted nothing")

	-- Lightning bolts actually flicker.
	for _, b in ipairs(c.bolts) do
		local seen = {}
		for _ = 1, 30 do runFrames(3, 1 / 60); seen[tostring(b.beam.CurveSize0)] = true end
		local n = 0
		for _ in pairs(seen) do n += 1 end
		assert(n > 3, name .. ": bolt " .. b.def.name .. " is not animating")
	end

	-- Distance culling.
	camera.CFrame = CFrame.new(0, 0, 500)
	runFrames(20, 1 / 60)
	assert(count(c.emitters, function(e) return e.inst.Enabled end) == 0, name .. ": should cull when far")
	camera.CFrame = CFrame.new(0, 2, 12)
	runFrames(20, 1 / 60)
	assert(count(c.emitters, function(e) return e.def.mode == "idle" and e.inst.Enabled end) == idle, name .. ": should resume")

	c:Destroy()
	assert(stats.live == liveBefore, name .. (": leaked %d instances"):format(stats.live - liveBefore))

	-- Held weapons run at full rate; resized + mirrored handles still build.
	WeaponVFX.Settings.FlipXZ = true
	local tool2, handle2 = makeWeapon(name, size * 1.5, true)
	local c2 = WeaponVFX.Attach(handle2, name)
	runFrames(30, 1 / 60)
	assert(c2.held, name .. ": should detect it is held")
	assert(c2.emitters[1].inst.Rate > displayRate, name .. ": held rate should beat display rate")
	c2:Destroy()
	WeaponVFX.Settings.FlipXZ = false
	print(("ok  %-22s %3d instances  %2d emitters  %d beams/bolts/rays  %d trails"):format(
		name, made, #c.emitters, #c.staticBeams + #c.bolts + #c.raySets, #c.trails))
end
assert(#heartbeat == 0, "heartbeat loop should stop when no weapons are left")
print(("all %d presets passed (%d instances total at rest)"):format(#names, totalInstances))
'''


def read(*p):
    return open(os.path.join(*p)).read()


def main():
    luau = sys.argv[1] if len(sys.argv) > 1 else "luau"
    bundle = "\n".join([
        read(HERE, "mock_roblox.luau"),
        "local __modules = {}",
        "__modules.Presets = (function()\n" + read(VFX, "WeaponVFX", "Presets.lua") + "\nend)()",
        "__modules.Textures = (function()\n" + read(VFX, "WeaponVFX", "Textures.lua") + "\nend)()",
        "local script = { WaitForChild = function(_, n) return { __module = n } end }",
        "local function require(m) return __modules[m.__module] end",
        "local WeaponVFX = (function()\n" + read(VFX, "WeaponVFX", "init.lua") + "\nend)()",
        TESTS,
    ])
    with tempfile.NamedTemporaryFile("w", suffix=".luau", delete=False) as f:
        f.write(bundle)
    r = subprocess.run([luau, f.name], capture_output=True, text=True)
    print(r.stdout + r.stderr)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
