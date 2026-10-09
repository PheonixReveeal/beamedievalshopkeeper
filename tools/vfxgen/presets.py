"""VFX presets for the special weapons -> Roblox ModuleScript (Presets.lua) + JSON for the previewer.

Positions are written in each model's build coordinates (the same numbers used in
tools/weapongen) and converted to offsets from the MeshPart's centre, which is how Roblox
positions things on an imported mesh.

Usage:  python presets.py <assets_dir>     (reads stats.json files, writes assets/vfx/...)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "weapongen"))


def hexc(h):
    h = h.lstrip("#")
    return [round(int(h[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)]


def seq(*pts):
    """Number sequence: seq((0, a), (0.5, b), (1, c)) or seq(a, b) for a straight ramp."""
    if all(isinstance(p, (int, float)) for p in pts):
        n = len(pts)
        return [[i / (n - 1), float(v)] for i, v in enumerate(pts)]
    return [[float(t), float(v)] + ([float(e[0])] if e else []) for t, v, *e in pts]


def cseq(*cols):
    n = len(cols)
    return [[i / (n - 1), hexc(c)] for i, c in enumerate(cols)]


def emitter(name, at, texture, color, size, transparency, lifetime, rate, speed=(0, 0), spread=(0, 0), accel=(0, 0, 0),
            drag=0.0, rotation=(0, 360), rot_speed=(0, 0), light_emission=1.0, light_influence=0.0, brightness=1.0,
            z_offset=0.0, orientation="FacingCamera", direction="Top", shape="Box", shape_style="Volume",
            shape_inout="Outward", locked=False, squash=None, flipbook=None, flip_mode="Loop", fps=(20, 30),
            flip_random_start=True, mode="idle", burst=0, swing_burst=0, vel_inherit=0.0):
    d = dict(name=name, at=at, texture=texture, color=color, size=size, transparency=transparency,
             lifetime=list(lifetime), rate=rate, speed=list(speed), spread=list(spread), accel=list(accel), drag=drag,
             rotation=list(rotation), rotSpeed=list(rot_speed), lightEmission=light_emission,
             lightInfluence=light_influence, brightness=brightness, zOffset=z_offset, orientation=orientation,
             direction=direction, shape=shape, shapeStyle=shape_style, shapeInOut=shape_inout, locked=locked,
             mode=mode, burst=burst, swingBurst=swing_burst, velInherit=vel_inherit)
    if squash:
        d["squash"] = squash
    if flipbook:
        d.update(flipbook=flipbook, flipMode=flip_mode, fps=list(fps), flipRandomStart=flip_random_start)
    return d


def trail(name, a0, a1, texture, color, transparency, lifetime=0.3, width=None, light_emission=1.0, brightness=1.5,
          mode="swing", face_camera=False):
    return dict(name=name, a0=a0, a1=a1, texture=texture, color=color, transparency=transparency, lifetime=lifetime,
                width=width or seq(1, 1), lightEmission=light_emission, brightness=brightness, mode=mode,
                faceCamera=face_camera)


def bolt(name, frm, to, color, width=(0.12, 0.08), curve=1.2, interval=(0.05, 0.12), chance=0.75, brightness=3.0,
         texture="Lightning", texture_speed=4.0, segments=12, transparency=None):
    """A crackling lightning beam: both ends jump to random points inside the from/to boxes."""
    return dict(kind="bolt", name=name, frm=frm, to=to, color=color, width=list(width), curve=curve,
                interval=list(interval), chance=chance, brightness=brightness, texture=texture,
                textureSpeed=texture_speed, segments=segments,
                transparency=transparency or seq((0, 0.1), (0.5, 0.0), (1, 0.1)))


def beam(name, a0, a1, color, width=(0.2, 0.2), curve=(0, 0), texture="TrailStreak", texture_speed=1.0,
         texture_length=1.0, brightness=2.0, transparency=None, segments=10, light_emission=1.0):
    return dict(kind="beam", name=name, a0=a0, a1=a1, color=color, width=list(width), curve=list(curve),
                texture=texture, textureSpeed=texture_speed, textureLength=texture_length, brightness=brightness,
                transparency=transparency or seq(0.2, 0.2), segments=segments, lightEmission=light_emission)


def rays(name, at, color, count=6, length=1.6, axis=(0, 1, 0), cone=70, width=(0.35, 0.0), speed=0.4,
         brightness=2.0, transparency=None, texture="Ray"):
    """Light shafts fanning out of an anchor and slowly turning around `axis`."""
    return dict(kind="rays", name=name, at=at, color=color, count=count, length=length, axis=list(axis), cone=cone,
                width=list(width), speed=speed, brightness=brightness, texture=texture,
                transparency=transparency or seq((0, 0.35), (1, 1.0)))


def light(at, color, brightness=2.0, range_=10.0, flicker=0.0, pulse=(0.0, 0.0)):
    return dict(at=at, color=hexc(color), brightness=brightness, range=range_, flicker=flicker, pulse=list(pulse))


def orbit(name, center, radius, speed, count=3, axis=(0, 1, 0), tilt=0.0, wobble=0.0):
    return dict(name=name, center=list(center), radius=radius, speed=speed, count=count, axis=list(axis), tilt=tilt,
                wobble=wobble)


def box(center, size):
    return dict(center=list(center), size=list(size))


# Shared building blocks -------------------------------------------------------------------

def sparkles(at, c1, c2, rate=16, size=0.22, life=(0.3, 0.6), name="Sparkles", speed=(0, 0.2)):
    return emitter(name, at, "Spark", cseq(c1, c2), seq((0, 0), (0.25, size), (1, 0)), seq(0, 0, 0.2),
                   life, rate, speed=speed, spread=(180, 180), rotation=(0, 90), rot_speed=(-60, 60), brightness=2.5)


def burst_ring(at, c1, c2, size=4.0, life=0.4, name="Shockwave", count=1):
    return emitter(name, at, "Ring", cseq(c1, c2), seq((0, 0.4), (1, size)), seq((0, 0.25), (0.6, 0.6), (1, 1)),
                   (life, life), 0, rotation=(0, 360), brightness=1.6, mode="burst", burst=count, z_offset=0.5)


# ======================================================================= presets

def presets():
    P = {}

    # ------------------------------------------------------------- Voidrender: tearing void
    P["Voidrender"] = dict(
        model="Voidrender",
        anchors=dict(base=(0, 0.12, 0), tip=(0, 3.22, 0), mid=(0, 1.6, 0), gem=(0, 0, 0), pommel=(0, -1.05, 0)),
        regions=dict(blade=box((0, 1.65, 0), (0.42, 3.1, 0.1)), edges=box((0, 1.65, 0), (0.46, 3.1, 0.02))),
        emitters=[
            emitter("VoidSmoke", "blade", "Smoke", cseq("2a0845", "12001f", "000000"), seq((0, 0.5), (1, 1.6)),
                    seq((0, 1), (0.15, 0.25), (1, 1)), (1.2, 2.0), 22, speed=(0.2, 0.6), spread=(30, 30),
                    accel=(0, 0.5, 0), drag=1.0, rot_speed=(-40, 40), light_emission=0, light_influence=0.3,
                    flipbook="4x4", fps=(10, 14), flip_mode="OneShot", z_offset=-0.5),
            emitter("VoidWisps", "blade", "Mist", cseq("b46bff", "6a00ff", "2b0066"), seq((0, 0.35), (1, 0.9)),
                    seq((0, 1), (0.2, 0.45), (1, 1)), (0.6, 1.0), 14, speed=(0.1, 0.4), spread=(180, 180),
                    rot_speed=(-90, 90), brightness=2),
            emitter("Runes", "blade", "Runes", cseq("e2b8ff", "a24bff"), seq((0, 0), (0.15, 0.24), (0.85, 0.24), (1, 0)),
                    seq((0, 1), (0.2, 0), (0.8, 0.1), (1, 1)), (1.4, 2.2), 7, speed=(0.15, 0.35), spread=(180, 180),
                    accel=(0, 0.35, 0), rotation=(0, 0), brightness=3, flipbook="4x4", flip_mode="Random"),
            sparkles("edges", "ffd6ff", "c04dff", rate=22),
            emitter("PommelVortex", "pommel", "Swirl", cseq("c77dff", "5a00c8"), seq(0.55, 0.75), seq((0, 1), (0.3, 0.3), (1, 1)),
                    (0.9, 1.1), 3, rot_speed=(240, 300), locked=True, brightness=2.5),
            emitter("SwingRunes", "blade", "Runes", cseq("ffffff", "b45cff"), seq((0, 0.3), (1, 0)), seq(0, 1),
                    (0.4, 0.7), 60, speed=(1, 3), spread=(180, 180), drag=2, rotation=(0, 0), brightness=4,
                    flipbook="4x4", flip_mode="Random", mode="swing"),
            emitter("Implosion", "mid", "Swirl", cseq("d9a6ff", "6a00ff"), seq((0, 2.6), (1, 0.2)), seq((0, 1), (0.3, 0.25), (1, 1)),
                    (0.35, 0.35), 0, rot_speed=(-500, -500), brightness=2, mode="burst", burst=1),
            burst_ring("mid", "e6c2ff", "6a00ff", size=5.0),
            emitter("BurstSparks", "blade", "Spark", cseq("ffffff", "c04dff"), seq((0, 0.35), (1, 0)), seq(0, 1),
                    (0.3, 0.6), 0, speed=(4, 9), spread=(180, 180), drag=3, orientation="VelocityParallel",
                    squash=seq((0, 1.2), (1, 0.4)), brightness=3, mode="burst", burst=40),
        ],
        beams=[bolt("Crackle1", box((0, 0.6, 0), (0.44, 0.6, 0.02)), box((0, 2.4, 0), (0.44, 1.4, 0.02)),
                    cseq("ffffff", "c77dff", "ffffff"), width=(0.1, 0.06), curve=0.8),
               bolt("Crackle2", box((0, 1.4, 0), (0.44, 1.2, 0.02)), box((0, 3.0, 0), (0.3, 0.4, 0.02)),
                    cseq("e6c2ff", "8a2be2", "e6c2ff"), width=(0.08, 0.04), curve=0.6, chance=0.55)],
        trails=[trail("SwingTrail", "base", "tip", "TrailWisp", cseq("f0d9ff", "9b30ff", "1a0033"),
                      seq((0, 0.0), (0.6, 0.4), (1, 1)), lifetime=0.35, light_emission=0.7)],
        lights=[light("mid", "9b30ff", 2.5, 11, flicker=0.25, pulse=(2.0, 0.25))],
    )

    # ------------------------------------------------------------- Emberfang: living fire
    P["Emberfang"] = dict(
        model="Emberfang",
        anchors=dict(base=(0, 0.12, 0), tip=(0, 3.08, 0), mid=(0, 1.5, 0), pommel=(0, -0.96, 0)),
        regions=dict(blade=box((0, 1.5, 0), (0.3, 2.9, 0.09)), core=box((0, 1.5, 0), (0.12, 2.9, 0.05))),
        emitters=[
            emitter("Flames", "blade", "Flames", cseq("ffd27a", "ff8a1f", "ff3d00", "7a0e00"), seq((0, 0.5), (1, 0.18)),
                    seq((0, 0.12), (0.6, 0.4), (1, 1)), (0.35, 0.6), 55, speed=(0.6, 1.4), spread=(12, 12),
                    accel=(0, 2.5, 0), rotation=(-12, 12), brightness=1.7, flipbook="4x4", fps=(24, 32),
                    flip_mode="OneShot", orientation="FacingCameraWorldUp"),
            emitter("Embers", "blade", "Ember", cseq("fff0a0", "ff8a00", "ff2a00"), seq((0, 0.1), (1, 0)), seq(0, 0, 1),
                    (1.0, 2.0), 30, speed=(0.8, 2.2), spread=(45, 45), accel=(0, 1.6, 0), drag=0.6, brightness=3,
                    orientation="VelocityParallel", squash=seq(0.6, 0.6)),
            emitter("HeatSmoke", "blade", "Smoke", cseq("3a2a22", "1a1a1a"), seq((0, 0.5), (1, 1.6)),
                    seq((0, 1), (0.2, 0.65), (1, 1)), (1.6, 2.6), 9, speed=(0.6, 1.2), spread=(20, 20),
                    accel=(0, 0.8, 0), drag=0.5, rot_speed=(-30, 30), light_emission=0, light_influence=0.5,
                    flipbook="4x4", fps=(8, 10), flip_mode="OneShot", z_offset=-1),
            emitter("CoreGlow", "core", "Glow", cseq("ffb050", "ff5a00"), seq(0.55, 0.7), seq((0, 0.8), (1, 1)),
                    (0.25, 0.35), 12, locked=True, brightness=1.2),
            emitter("PommelFire", "pommel", "Flames", cseq("ffc060", "ff5a00"), seq((0, 0.22), (1, 0.08)), seq((0, 0.3), (1, 1)),
                    (0.3, 0.45), 14, speed=(0.3, 0.6), spread=(10, 10), accel=(0, 1.5, 0), brightness=1.3,
                    flipbook="4x4", fps=(24, 32), flip_mode="OneShot", orientation="FacingCameraWorldUp"),
            emitter("SwingFire", "blade", "Flames", cseq("ffc060", "ff6a00", "a01800"), seq((0, 0.6), (1, 0.25)),
                    seq((0, 0.3), (1, 1)), (0.25, 0.45), 55, speed=(0.5, 1.5), spread=(60, 60), brightness=1.4,
                    flipbook="4x4", fps=(30, 40), flip_mode="OneShot", mode="swing"),
            emitter("FireBurst", "blade", "Flames", cseq("ffd27a", "ff8a1f", "ff3c00"), seq((0, 0.7), (1, 1.3)), seq((0, 0.2), (1, 1)),
                    (0.35, 0.55), 0, speed=(3, 6), spread=(180, 180), drag=4, brightness=1.5, flipbook="4x4",
                    fps=(30, 40), flip_mode="OneShot", mode="burst", burst=16),
            emitter("EmberBurst", "blade", "Ember", cseq("ffffff", "ff8a00"), seq((0, 0.14), (1, 0)), seq(0, 1),
                    (0.6, 1.2), 0, speed=(5, 10), spread=(180, 180), accel=(0, -6, 0), drag=1.5,
                    orientation="VelocityParallel", squash=seq(1, 0.5), brightness=3, mode="burst", burst=50),
            burst_ring("mid", "ffd27a", "ff3c00", size=5.0),
        ],
        trails=[trail("SwingTrail", "base", "tip", "TrailStreak", cseq("fff6c8", "ff9a1f", "c21d00"),
                      seq((0, 0.0), (0.5, 0.3), (1, 1)), lifetime=0.3, brightness=2.5)],
        lights=[light("mid", "ff7a1a", 3.0, 13, flicker=0.45)],
    )

    # ------------------------------------------------------------- Frostbrand: winter's breath
    P["Frostbrand"] = dict(
        model="Frostbrand",
        anchors=dict(base=(0, 0.12, 0), tip=(0, 2.98, 0), mid=(0, 1.4, 0), pommel=(0, -1.05, 0), clasp=(0, 0.95, 0)),
        regions=dict(blade=box((0, 1.5, 0), (0.38, 2.8, 0.1))),
        emitters=[
            emitter("ColdMist", "blade", "Mist", cseq("e8fbff", "9fe3ff"), seq((0, 0.5), (1, 1.5)),
                    seq((0, 1), (0.3, 0.72), (1, 1)), (1.4, 2.4), 10, speed=(0.05, 0.25), spread=(180, 180),
                    accel=(0, -0.7, 0), drag=0.6, rot_speed=(-25, 25), light_emission=0.35, brightness=0.9),
            emitter("Snow", "blade", "Snowflake", cseq("ffffff", "c8f2ff"), seq((0, 0.13), (1, 0.08)), seq((0, 0.1), (0.8, 0.2), (1, 1)),
                    (1.8, 2.8), 12, speed=(0.2, 0.6), spread=(180, 180), accel=(0, -0.45, 0), drag=0.4,
                    rot_speed=(-80, 80), light_emission=0.5, brightness=1.5),
            sparkles("blade", "ffffff", "6fd8ff", rate=18, size=0.26),
            emitter("Shards", "blade", "Shards", cseq("e8fbff", "7fd6ff"), seq((0, 0.14), (1, 0.08)), seq((0, 0), (0.8, 0.2), (1, 1)),
                    (0.8, 1.2), 3, speed=(0.4, 1.0), spread=(90, 90), accel=(0, -3, 0), rot_speed=(-200, 200),
                    light_emission=0.4, brightness=1.5, flipbook="2x2", flip_mode="Random"),
            emitter("FrostCore", "pommel", "Glow", cseq("dff8ff", "3fb8ff"), seq(0.6, 0.7), seq((0, 0.5), (1, 1)),
                    (0.4, 0.5), 6, locked=True, brightness=2),
            emitter("SwingFrost", "blade", "Mist", cseq("d8f6ff", "8fdcff"), seq((0, 0.35), (1, 1.0)), seq((0, 0.55), (1, 1)),
                    (0.5, 0.8), 30, speed=(0.2, 0.8), spread=(180, 180), drag=1.5, light_emission=0.5, mode="swing"),
            emitter("ShardBurst", "blade", "Shards", cseq("ffffff", "7fd6ff"), seq((0, 0.3), (1, 0.15)), seq((0, 0), (0.7, 0.1), (1, 1)),
                    (0.6, 1.0), 0, speed=(4, 8), spread=(180, 180), accel=(0, -10, 0), drag=1, rot_speed=(-400, 400),
                    brightness=2, flipbook="2x2", flip_mode="Random", mode="burst", burst=30),
            emitter("SnowBurst", "blade", "Snowflake", cseq("ffffff", "aeeaff"), seq((0, 0.2), (1, 0.1)), seq(0, 1),
                    (0.8, 1.4), 0, speed=(2, 5), spread=(180, 180), drag=2, rot_speed=(-200, 200),
                    light_emission=0.5, mode="burst", burst=30),
            burst_ring("mid", "ffffff", "4fc3ff", size=4.5),
        ],
        trails=[trail("SwingTrail", "base", "tip", "TrailStreak", cseq("ffffff", "a8ecff", "2f9bff"),
                      seq((0, 0.0), (0.5, 0.35), (1, 1)), lifetime=0.35, brightness=2)],
        lights=[light("mid", "7fd6ff", 2.2, 11, pulse=(1.2, 0.2))],
    )

    # ------------------------------------------------------------- Tidecrystal Shard: tidal currents
    P["TidecrystalShard"] = dict(
        model="TidecrystalShard",
        anchors=dict(base=(0, 0.12, 0), tip=(0, 3.02, 0), mid=(0, 1.6, 0), gem=(0, 1.68, 0)),
        regions=dict(blade=box((0, 1.5, 0), (0.42, 2.9, 0.1))),
        orbits=[orbit("Current", (0, 1.5, 0), 0.42, 2.6, count=3, wobble=1.1)],
        emitters=[
            emitter("CurrentDrops", "orbit:Current", "Droplet", cseq("e9ffff", "33d6d0", "0b6f8a"), seq((0, 0.14), (1, 0.02)),
                    seq((0, 0.0), (1, 1)), (0.45, 0.6), 40, light_emission=0.4, brightness=1.6, rotation=(0, 0)),
            emitter("Bubbles", "blade", "Bubble", cseq("ffffff", "8ff5ef"), seq((0, 0.06), (1, 0.16)), seq((0, 0.2), (0.85, 0.3), (1, 1)),
                    (1.4, 2.4), 14, speed=(0.3, 0.7), spread=(25, 25), accel=(0, 0.5, 0), light_emission=0.3,
                    brightness=1.4),
            emitter("SeaMist", "blade", "Mist", cseq("bffff9", "2fb8c6"), seq((0, 0.5), (1, 1.2)), seq((0, 1), (0.3, 0.7), (1, 1)),
                    (1.2, 1.8), 8, speed=(0.1, 0.3), spread=(180, 180), light_emission=0.5, brightness=1.2),
            sparkles("blade", "ffffff", "37e5d8", rate=16),
            emitter("SwingSpray", "blade", "Droplet", cseq("ffffff", "41d9d0"), seq((0, 0.16), (1, 0.05)), seq(0, 1),
                    (0.4, 0.7), 90, speed=(1, 3), spread=(90, 90), accel=(0, -9, 0), light_emission=0.4,
                    orientation="VelocityParallel", mode="swing"),
            emitter("Splash", "blade", "Droplet", cseq("ffffff", "2fc4c9"), seq((0, 0.22), (1, 0.08)), seq((0, 0), (1, 1)),
                    (0.6, 1.0), 0, speed=(4, 8), spread=(180, 180), accel=(0, -14, 0), light_emission=0.4,
                    orientation="VelocityParallel", mode="burst", burst=45),
            burst_ring("mid", "e9ffff", "1fa8b8", size=4.5),
        ],
        trails=[trail("SwingTrail", "base", "tip", "TrailWisp", cseq("ffffff", "5cf0e4", "0a6d8f"),
                      seq((0, 0.0), (0.6, 0.35), (1, 1)), lifetime=0.4, light_emission=0.6)],
        lights=[light("mid", "33e0d2", 2.2, 10, pulse=(1.6, 0.2))],
    )

    # ------------------------------------------------------------- Sunsteel Falchion: radiant sun
    P["SunsteelFalchion"] = dict(
        model="SunsteelFalchion",
        anchors=dict(base=(0.07, 0.1, 0), tip=(0.1, 2.5, 0), mid=(0.08, 1.3, 0), guard=(0, 0.0, 0)),
        regions=dict(blade=box((0.08, 1.3, 0), (0.36, 2.4, 0.09))),
        emitters=[
            emitter("Flares", "blade", "Star", cseq("ffffff", "ffd24a"), seq((0, 0), (0.3, 0.55), (1, 0)), seq(0, 0, 0.3),
                    (0.4, 0.7), 7, rotation=(0, 45), rot_speed=(-20, 20), brightness=3, locked=True),
            emitter("Motes", "blade", "Ember", cseq("fff7d6", "ffc93c", "ff9a1f"), seq((0, 0.0), (0.2, 0.09), (1, 0)), seq(0, 0, 1),
                    (1.6, 2.6), 30, speed=(0.1, 0.5), spread=(180, 180), accel=(0, 0.45, 0), drag=0.8, brightness=3),
            emitter("Halo", "guard", "Ring", cseq("fff2b8", "ffbf2e"), seq(0.9, 1.15), seq((0, 1), (0.3, 0.45), (1, 1)),
                    (1.1, 1.3), 2, rot_speed=(30, 30), locked=True, brightness=2.5),
            emitter("SunGlow", "blade", "Glow", cseq("ffe7a8", "ffb000"), seq(0.5, 0.65), seq((0, 0.82), (1, 1)),
                    (0.3, 0.4), 8, locked=True, brightness=1.2),
            emitter("SwingFlares", "blade", "Star", cseq("fff2c4", "ffcf40"), seq((0, 0.55), (1, 0)), seq(0.2, 1),
                    (0.25, 0.4), 22, speed=(0.5, 1.5), spread=(180, 180), brightness=1.8, mode="swing"),
            emitter("Sunburst", "mid", "Star", cseq("fff2c4", "ffcf40"), seq((0, 1.0), (0.2, 3.0), (1, 0)), seq(0.2, 0.35, 1),
                    (0.45, 0.45), 0, rotation=(0, 45), rot_speed=(40, 40), brightness=2, mode="burst", burst=1,
                    z_offset=1),
            emitter("MoteBurst", "blade", "Ember", cseq("ffffff", "ffc93c"), seq((0, 0.15), (1, 0)), seq(0, 1),
                    (0.6, 1.2), 0, speed=(3, 7), spread=(180, 180), drag=3, brightness=3, mode="burst", burst=45),
            burst_ring("mid", "fff2b8", "ffae00", size=4.5),
        ],
        beams=[rays("SunRays", "mid", cseq("fff2c4", "ffc93c"), count=5, length=1.5, axis=(0, 1, 0), cone=80,
                    width=(0.3, 0.02), speed=0.35, brightness=1.1, transparency=seq((0, 0.55), (1, 1.0)))],
        trails=[trail("SwingTrail", "base", "tip", "TrailStreak", cseq("ffffff", "ffe27a", "ff9a1f"),
                      seq((0, 0.0), (0.5, 0.3), (1, 1)), lifetime=0.3, brightness=2.5)],
        lights=[light("mid", "ffc24a", 2.6, 12, pulse=(0.8, 0.12))],
    )

    # ------------------------------------------------------------- Glacier Cleaver: blizzard
    yh = 4.1
    P["GlacierCleaver"] = dict(
        model="GlacierCleaver",
        anchors=dict(head=(0, yh, 0), left=(-1.08, yh, 0), right=(1.08, yh, 0), spike=(0, 4.95, 0),
                     haft=(0, 3.4, 0), top=(0, 4.9, 0)),
        regions=dict(head=box((0, yh, 0), (2.1, 1.4, 0.14)), lblade=box((-0.75, yh, 0), (0.6, 1.2, 0.1)),
                     rblade=box((0.75, yh, 0), (0.6, 1.2, 0.1))),
        orbits=[orbit("Blizzard", (0, yh, 0), 1.25, 3.2, count=4, tilt=0.35, wobble=0.6)],
        emitters=[
            emitter("BlizzardSnow", "orbit:Blizzard", "Snowflake", cseq("ffffff", "bdeeff"), seq((0, 0.14), (1, 0.05)),
                    seq((0, 0.1), (1, 1)), (0.6, 1.0), 14, speed=(0.1, 0.4), spread=(180, 180), rot_speed=(-120, 120),
                    light_emission=0.5, brightness=1.5),
            emitter("BlizzardMist", "orbit:Blizzard", "Mist", cseq("f2fdff", "9fdcff"), seq((0, 0.35), (1, 0.8)),
                    seq((0, 0.6), (1, 1)), (0.5, 0.8), 10, light_emission=0.3, brightness=1.2),
            emitter("ColdMistL", "lblade", "Mist", cseq("e8fbff", "9fe3ff"), seq((0, 0.5), (1, 1.4)), seq((0, 1), (0.3, 0.75), (1, 1)),
                    (1.4, 2.2), 6, speed=(0.05, 0.2), spread=(180, 180), accel=(0, -0.8, 0), light_emission=0.35),
            emitter("ColdMistR", "rblade", "Mist", cseq("e8fbff", "9fe3ff"), seq((0, 0.5), (1, 1.4)), seq((0, 1), (0.3, 0.75), (1, 1)),
                    (1.4, 2.2), 6, speed=(0.05, 0.2), spread=(180, 180), accel=(0, -0.8, 0), light_emission=0.35),
            emitter("FrostRunes", "head", "Runes", cseq("ffffff", "6fe6ff"), seq((0, 0), (0.15, 0.3), (0.85, 0.3), (1, 0)),
                    seq((0, 1), (0.2, 0), (0.8, 0.1), (1, 1)), (1.2, 1.8), 5, speed=(0.1, 0.3), spread=(180, 180),
                    rotation=(0, 0), brightness=3, flipbook="4x4", flip_mode="Random"),
            sparkles("head", "ffffff", "5fd0ff", rate=22, size=0.3),
            emitter("ShardBurst", "head", "Shards", cseq("ffffff", "7fd6ff"), seq((0, 0.4), (1, 0.2)), seq((0, 0), (0.7, 0.1), (1, 1)),
                    (0.7, 1.1), 0, speed=(5, 10), spread=(180, 180), accel=(0, -12, 0), drag=1, rot_speed=(-400, 400),
                    brightness=2, flipbook="2x2", flip_mode="Random", mode="burst", burst=40),
            emitter("SwingSnow", "head", "Snowflake", cseq("ffffff", "aeeaff"), seq((0, 0.2), (1, 0.08)), seq(0, 1),
                    (0.5, 0.9), 80, speed=(0.5, 2), spread=(180, 180), drag=2, rot_speed=(-200, 200),
                    light_emission=0.5, mode="swing"),
            burst_ring("head", "ffffff", "4fc3ff", size=7.0),
        ],
        beams=[bolt("FrostArc", box((-1.0, yh, 0), (0.1, 1.2, 0.05)), box((1.0, yh, 0), (0.1, 1.2, 0.05)),
                    cseq("ffffff", "7fe0ff", "ffffff"), width=(0.12, 0.12), curve=1.6, interval=(0.08, 0.16),
                    chance=0.6)],
        trails=[trail("SwingTrail", "left", "right", "TrailStreak", cseq("ffffff", "a8ecff", "2f9bff"),
                      seq((0, 0.1), (0.5, 0.4), (1, 1)), lifetime=0.35, brightness=2)],
        lights=[light("head", "86dcff", 2.8, 14, pulse=(1.0, 0.2))],
    )

    # ------------------------------------------------------------- Duskforged Warhammer: storm
    yh = 4.2
    P["DuskforgedWarhammer"] = dict(
        model="DuskforgedWarhammer",
        anchors=dict(head=(0, yh, 0), front=(0.62, yh, 0), back=(-0.62, yh, 0), crystal=(-0.95, yh, 0),
                     top=(0, yh + 0.55, 0)),
        regions=dict(head=box((0, yh, 0), (1.3, 0.62, 0.56)), crystal=box((-0.85, yh, 0), (0.35, 0.4, 0.4)),
                     face=box((0.72, yh, 0), (0.08, 0.5, 0.45)), cloud=box((0, yh + 0.55, 0), (1.2, 0.2, 0.5))),
        emitters=[
            emitter("Zaps", "head", "Zaps", cseq("ffffff", "c9a2ff"), seq((0, 0.45), (1, 0.6)), seq(0, 0.3),
                    (0.08, 0.14), 14, rotation=(0, 360), brightness=4, flipbook="2x2", flip_mode="Random",
                    shape_style="Surface"),
            emitter("CrystalZaps", "crystal", "Zaps", cseq("ffffff", "d58bff"), seq((0, 0.35), (1, 0.45)), seq(0, 0.3),
                    (0.06, 0.12), 12, rotation=(0, 360), brightness=4, flipbook="2x2", flip_mode="Random"),
            emitter("Sparks", "head", "Spark", cseq("ffffff", "b48cff"), seq((0, 0.13), (1, 0)), seq(0, 1),
                    (0.25, 0.5), 26, speed=(2, 5), spread=(180, 180), accel=(0, -9, 0), drag=2,
                    orientation="VelocityParallel", squash=seq(1.2, 0.6), brightness=3, shape_style="Surface"),
            emitter("StormCloud", "cloud", "Smoke", cseq("4a3f6b", "2a2440"), seq((0, 0.6), (1, 1.4)),
                    seq((0, 1), (0.3, 0.55), (1, 1)), (1.6, 2.4), 7, speed=(0.15, 0.4), spread=(40, 40),
                    accel=(0, 0.25, 0), rot_speed=(-20, 20), light_emission=0.1, light_influence=0.4,
                    flipbook="4x4", fps=(8, 10), flip_mode="OneShot", z_offset=-1),
            emitter("FaceGlow", "face", "Glow", cseq("e9d4ff", "8a4bff"), seq(0.8, 1.0), seq((0, 0.65), (1, 1)),
                    (0.2, 0.3), 10, locked=True, brightness=2),
            emitter("SwingZaps", "head", "Zaps", cseq("ffffff", "c9a2ff"), seq((0, 0.7), (1, 0.9)), seq(0, 0.5),
                    (0.08, 0.12), 60, brightness=4, flipbook="2x2", flip_mode="Random", mode="swing"),
            emitter("ImpactZaps", "head", "Zaps", cseq("ffffff", "b48cff"), seq((0, 1.2), (1, 1.6)), seq(0, 1),
                    (0.12, 0.2), 0, speed=(2, 5), spread=(180, 180), brightness=5, flipbook="2x2", flip_mode="Random",
                    mode="burst", burst=16),
            emitter("ImpactSparks", "head", "Spark", cseq("ffffff", "a98bff"), seq((0, 0.2), (1, 0)), seq(0, 1),
                    (0.4, 0.8), 0, speed=(6, 14), spread=(180, 180), accel=(0, -18, 0), drag=1.5,
                    orientation="VelocityParallel", squash=seq(1.5, 0.5), brightness=4, mode="burst", burst=70),
            emitter("ImpactDust", "head", "Smoke", cseq("8e86a8", "3b3550"), seq((0, 0.8), (1, 2.6)), seq((0, 0.4), (1, 1)),
                    (0.8, 1.2), 0, speed=(2, 4), spread=(180, 15), drag=3, light_emission=0, light_influence=0.6,
                    flipbook="4x4", fps=(14, 18), flip_mode="OneShot", mode="burst", burst=10),
            burst_ring("head", "ffffff", "8a4bff", size=8.0),
        ],
        beams=[bolt("Arc1", "crystal", box((0.3, yh, 0), (0.6, 0.55, 0.5)), cseq("ffffff", "b48cff", "ffffff"),
                    width=(0.14, 0.08), curve=1.0, interval=(0.04, 0.09)),
               bolt("Arc2", "crystal", box((0.66, yh, 0), (0.06, 0.5, 0.45)), cseq("e9d4ff", "8a4bff", "e9d4ff"),
                    width=(0.1, 0.05), curve=1.4, interval=(0.05, 0.11), chance=0.6),
               bolt("Arc3", box((-0.3, yh + 0.32, 0), (0.6, 0.02, 0.4)), box((0.3, yh - 0.32, 0), (0.6, 0.02, 0.4)),
                    cseq("ffffff", "c9a2ff", "ffffff"), width=(0.08, 0.05), curve=0.8, interval=(0.06, 0.13), chance=0.5)],
        trails=[trail("SwingTrail", "back", "front", "TrailStreak", cseq("ffffff", "c9a2ff", "4b1fa8"),
                      seq((0, 0.0), (0.5, 0.35), (1, 1)), lifetime=0.3, brightness=2.5)],
        lights=[light("head", "a173ff", 3.0, 14, flicker=0.7)],
    )

    # ------------------------------------------------------------- Royal Sapphire Scepter: royal radiance
    P["RoyalSapphireScepter"] = dict(
        model="RoyalSapphireScepter",
        anchors=dict(gem=(0, 5.0, 0), finial=(0, 5.45, 0), crown=(0, 4.7, 0), knot=(0, 2.61, 0), low=(0, 4.6, 0),
                     high=(0, 5.45, 0)),
        regions=dict(crown=box((0, 4.95, 0), (0.6, 0.75, 0.6)), aura=box((0, 5.0, 0), (1.4, 1.2, 1.4))),
        emitters=[
            sparkles("crown", "ffffff", "4d7cff", rate=24, size=0.25),
            emitter("GoldDust", "aura", "Ember", cseq("fff7d6", "ffcf4a"), seq((0, 0), (0.2, 0.08), (1, 0)), seq(0, 0, 1),
                    (1.8, 2.8), 22, speed=(0.05, 0.25), spread=(180, 180), accel=(0, -0.3, 0), drag=0.5, brightness=2.5),
            emitter("SapphireGlow", "gem", "Glow", cseq("cfe0ff", "2f5bff"), seq(1.1, 1.3), seq((0, 0.55), (1, 1)),
                    (0.3, 0.4), 10, locked=True, brightness=2.5),
            emitter("Crownlight", "finial", "Star", cseq("ffffff", "8fb0ff"), seq((0, 0), (0.4, 0.7), (1, 0)), seq(0, 0.1, 0.4),
                    (0.8, 1.0), 2, rotation=(0, 45), rot_speed=(15, 15), locked=True, brightness=3),
            emitter("Halo", "finial", "Ring", cseq("fff2c2", "ffcc40"), seq(0.7, 0.8), seq((0, 1), (0.3, 0.5), (1, 1)),
                    (1.4, 1.6), 1.5, rot_speed=(20, 20), locked=True, brightness=2),
            emitter("SwingStars", "crown", "Spark", cseq("ffffff", "6f95ff"), seq((0, 0.35), (1, 0)), seq(0, 1),
                    (0.3, 0.6), 60, speed=(0.5, 2), spread=(180, 180), drag=2, brightness=3, mode="swing"),
            emitter("RoyalFlash", "gem", "Star", cseq("ffffff", "6f95ff"), seq((0, 1), (0.2, 4), (1, 0)), seq(0, 0.2, 1),
                    (0.5, 0.5), 0, rotation=(0, 45), brightness=4, mode="burst", burst=1, z_offset=1),
            emitter("GoldBurst", "gem", "Ember", cseq("ffffff", "ffcf4a"), seq((0, 0.14), (1, 0)), seq(0, 1),
                    (0.8, 1.4), 0, speed=(3, 7), spread=(180, 180), drag=2.5, brightness=3, mode="burst", burst=50),
            burst_ring("gem", "dfe8ff", "2f5bff", size=5.0),
        ],
        beams=[rays("Radiance", "gem", cseq("ffffff", "8fb0ff"), count=7, length=1.8, axis=(0, 1, 0), cone=65,
                    width=(0.35, 0.0), speed=0.3, brightness=2.2)],
        trails=[trail("SwingTrail", "low", "high", "TrailStreak", cseq("ffffff", "8fb0ff", "ffcf4a"),
                      seq((0, 0.0), (0.5, 0.35), (1, 1)), lifetime=0.35, brightness=2)],
        lights=[light("gem", "5b86ff", 3.0, 14, pulse=(1.0, 0.15))],
    )

    # ------------------------------------------------------------- Arcane Amethyst Staff: arcane power
    top = 4.95
    P["ArcaneAmethystStaff"] = dict(
        model="ArcaneAmethystStaff",
        anchors=dict(crystal=(0, top + 0.5, 0), cage_low=(0, top + 0.05, 0), cage_high=(0, top + 1.05, 0),
                     ring=(0, top + 0.5, 0)),
        regions=dict(cage=box((0, top + 0.5, 0), (0.55, 1.0, 0.55)), aura=box((0, top + 0.5, 0), (1.3, 1.4, 1.3))),
        orbits=[orbit("Wisps", (0, top + 0.5, 0), 0.5, 2.8, count=3, tilt=0.55, wobble=0.0)],
        emitters=[
            emitter("OrbTrails", "orbit:Wisps", "Orb", cseq("ffffff", "d26bff", "6a1fd1"), seq((0, 0.2), (1, 0)), seq((0, 0), (1, 1)),
                    (0.45, 0.6), 45, rotation=(0, 0), brightness=2.5),
            emitter("Runes", "aura", "Runes", cseq("ffe0ff", "c04dff"), seq((0, 0), (0.15, 0.22), (0.85, 0.22), (1, 0)),
                    seq((0, 1), (0.2, 0), (0.8, 0.1), (1, 1)), (2.0, 3.0), 6, speed=(0.1, 0.3), spread=(180, 180),
                    accel=(0, 0.25, 0), rotation=(0, 0), brightness=3, flipbook="4x4", flip_mode="Random"),
            emitter("Vortex", "crystal", "Swirl", cseq("ffd6ff", "8a2be2"), seq((0, 0.9), (1, 1.3)), seq((0, 1), (0.3, 0.45), (1, 1)),
                    (1.4, 1.6), 2, rot_speed=(120, 160), locked=True, brightness=2.2),
            emitter("SpellCircle", "ring", "MagicCircle", cseq("ffe6ff", "b45cff"), seq(1.5, 1.5), seq((0, 1), (0.2, 0.3), (0.8, 0.3), (1, 1)),
                    (3.0, 3.0), 0.34, speed=(0.01, 0.01), rot_speed=(25, 25), orientation="VelocityPerpendicular",
                    brightness=2.5, locked=True),
            sparkles("cage", "ffffff", "d26bff", rate=20),
            emitter("SwingOrbs", "cage", "Orb", cseq("ffffff", "b45cff"), seq((0, 0.25), (1, 0)), seq(0, 1),
                    (0.4, 0.7), 50, speed=(0.5, 2), spread=(180, 180), drag=2, brightness=3, mode="swing"),
            emitter("CastFlash", "crystal", "Orb", cseq("ffffff", "c04dff"), seq((0, 0.5), (1, 3.0)), seq((0, 0), (1, 1)),
                    (0.35, 0.35), 0, brightness=4, mode="burst", burst=1, z_offset=1),
            emitter("CastRunes", "crystal", "Runes", cseq("ffffff", "c04dff"), seq((0, 0.35), (1, 0.1)), seq(0, 1),
                    (0.6, 1.0), 0, speed=(3, 6), spread=(180, 180), drag=3, rotation=(0, 0), brightness=3,
                    flipbook="4x4", flip_mode="Random", mode="burst", burst=24),
            burst_ring("crystal", "ffe6ff", "8a2be2", size=5.0),
        ],
        trails=[trail("SwingTrail", "cage_low", "cage_high", "TrailWisp", cseq("ffffff", "d26bff", "4a0d8f"),
                      seq((0, 0.0), (0.6, 0.35), (1, 1)), lifetime=0.4, light_emission=0.8)],
        lights=[light("crystal", "b45cff", 3.0, 13, pulse=(1.8, 0.25))],
    )

    # ------------------------------------------------------------- Glacier Bow: frozen string
    P["GlacierBow"] = dict(
        model="GlacierBow",
        anchors=dict(top_tip=(0.17, 2.3, 0), bottom_tip=(0.17, -2.3, 0), grip=(0, 0, 0), nock=(0.17, 0, 0)),
        regions=dict(upper=box((0.13, 1.25, 0), (0.3, 2.1, 0.12)), lower=box((0.13, -1.25, 0), (0.3, 2.1, 0.12))),
        emitters=[
            emitter("MistUpper", "upper", "Mist", cseq("e8fbff", "9fe3ff"), seq((0, 0.4), (1, 1.1)), seq((0, 1), (0.3, 0.75), (1, 1)),
                    (1.2, 2.0), 6, speed=(0.05, 0.2), spread=(180, 180), accel=(0, -0.6, 0), light_emission=0.35),
            emitter("MistLower", "lower", "Mist", cseq("e8fbff", "9fe3ff"), seq((0, 0.4), (1, 1.1)), seq((0, 1), (0.3, 0.75), (1, 1)),
                    (1.2, 2.0), 6, speed=(0.05, 0.2), spread=(180, 180), accel=(0, -0.6, 0), light_emission=0.35),
            emitter("SnowUpper", "upper", "Snowflake", cseq("ffffff", "c8f2ff"), seq((0, 0.12), (1, 0.06)), seq((0, 0.1), (1, 1)),
                    (1.6, 2.6), 7, speed=(0.2, 0.5), spread=(180, 180), accel=(0, -0.4, 0), rot_speed=(-80, 80),
                    light_emission=0.5),
            emitter("SnowLower", "lower", "Snowflake", cseq("ffffff", "c8f2ff"), seq((0, 0.12), (1, 0.06)), seq((0, 0.1), (1, 1)),
                    (1.6, 2.6), 7, speed=(0.2, 0.5), spread=(180, 180), accel=(0, -0.4, 0), rot_speed=(-80, 80),
                    light_emission=0.5),
            sparkles("upper", "ffffff", "6fd8ff", rate=10),
            sparkles("lower", "ffffff", "6fd8ff", rate=10, name="Sparkles2"),
            emitter("ShotFrost", "nock", "Mist", cseq("ffffff", "8fdcff"), seq((0, 0.3), (1, 1.4)), seq((0, 0.1), (1, 1)),
                    (0.5, 0.8), 0, speed=(2, 5), spread=(25, 25), direction="Front", drag=3, light_emission=0.6,
                    mode="burst", burst=16),
            burst_ring("nock", "ffffff", "4fc3ff", size=3.0),
        ],
        beams=[beam("StringGlowTop", "top_tip", "nock", cseq("ffffff", "7fe0ff"), width=(0.07, 0.07),
                    texture="Lightning", texture_speed=2.5, texture_length=1.2, brightness=2.5,
                    transparency=seq(0.15, 0.15)),
               beam("StringGlowBottom", "nock", "bottom_tip", cseq("7fe0ff", "ffffff"), width=(0.07, 0.07),
                    texture="Lightning", texture_speed=-2.5, texture_length=1.2, brightness=2.5,
                    transparency=seq(0.15, 0.15))],
        lights=[light("grip", "7fd6ff", 2.0, 10, pulse=(1.2, 0.2))],
    )

    # ------------------------------------------------------------- Dragonbane Arbalest: dragon fire
    fp = 1.22
    P["DragonbaneArbalest"] = dict(
        model="DragonbaneArbalest", category="Crossbows",
        anchors=dict(snout=(0, 0.02, -1.74), head=(0, 0.02, -1.5), ltip=(-1.44, 0.25, -fp + 0.59),
                     rtip=(1.44, 0.25, -fp + 0.59), nut=(0, 0.095, -0.05), bolt=(0, 0.1, -1.6)),
        regions=dict(lwing=box((-0.8, 0.06, -fp + 0.25), (1.1, 0.06, 0.45)),
                     rwing=box((0.8, 0.06, -fp + 0.25), (1.1, 0.06, 0.45)),
                     stock=box((0, 0.0, 0.3), (0.18, 0.2, 2.6))),
        emitters=[
            emitter("Breath", "snout", "Flames", cseq("fff3b0", "ff8a00", "a01800"), seq((0, 0.25), (1, 0.5)),
                    seq((0, 0.2), (1, 1)), (0.25, 0.4), 30, speed=(0.8, 1.6), spread=(12, 12), direction="Front",
                    accel=(0, 1.2, 0), brightness=2.5, flipbook="4x4", fps=(28, 36), flip_mode="OneShot"),
            emitter("NostrilSmoke", "snout", "Smoke", cseq("3a2a22", "151515"), seq((0, 0.25), (1, 0.9)),
                    seq((0, 1), (0.2, 0.55), (1, 1)), (1.2, 1.8), 7, speed=(0.4, 0.8), spread=(20, 20),
                    direction="Front", accel=(0, 0.9, 0), light_emission=0, light_influence=0.5, flipbook="4x4",
                    fps=(8, 10), flip_mode="OneShot", z_offset=-0.5),
            emitter("WingEmbersL", "lwing", "Ember", cseq("fff0a0", "ff6a00"), seq((0, 0.08), (1, 0)), seq(0, 0, 1),
                    (1.0, 1.8), 14, speed=(0.3, 1.0), spread=(30, 30), accel=(0, 1.2, 0), brightness=3),
            emitter("WingEmbersR", "rwing", "Ember", cseq("fff0a0", "ff6a00"), seq((0, 0.08), (1, 0)), seq(0, 0, 1),
                    (1.0, 1.8), 14, speed=(0.3, 1.0), spread=(30, 30), accel=(0, 1.2, 0), brightness=3),
            emitter("RuneGlow", "stock", "Runes", cseq("ffd27a", "ff3c00"), seq((0, 0), (0.2, 0.16), (1, 0)), seq((0, 1), (0.3, 0.1), (1, 1)),
                    (1.0, 1.6), 5, speed=(0.1, 0.3), spread=(180, 180), accel=(0, 0.4, 0), rotation=(0, 0),
                    brightness=3, flipbook="4x4", flip_mode="Random"),
            emitter("MuzzleBlast", "snout", "Flames", cseq("ffd27a", "ff8a1f", "ff3c00"), seq((0, 0.5), (1, 1.3)), seq((0, 0.2), (1, 1)),
                    (0.3, 0.5), 0, speed=(4, 8), spread=(25, 25), direction="Front", drag=4, brightness=1.6,
                    flipbook="4x4", fps=(30, 40), flip_mode="OneShot", mode="burst", burst=26),
            emitter("MuzzleEmbers", "snout", "Ember", cseq("ffffff", "ff8a00"), seq((0, 0.14), (1, 0)), seq(0, 1),
                    (0.5, 1.0), 0, speed=(6, 12), spread=(30, 30), direction="Front", drag=1.5,
                    orientation="VelocityParallel", squash=seq(1, 0.5), brightness=3, mode="burst", burst=40),
            burst_ring("snout", "ff9a3c", "ff3c00", size=2.2),
        ],
        beams=[beam("StringFireL", "ltip", "nut", cseq("ffd27a", "ff5a00"), width=(0.06, 0.06), texture="Lightning",
                    texture_speed=3, texture_length=1.5, brightness=2.5),
               beam("StringFireR", "nut", "rtip", cseq("ff5a00", "ffd27a"), width=(0.06, 0.06), texture="Lightning",
                    texture_speed=-3, texture_length=1.5, brightness=2.5)],
        lights=[light("head", "ff7a1a", 2.5, 10, flicker=0.5)],
    )
    for p in P.values():
        for t in p.get("trails", []):
            c = t["color"]
            if len(c) > 1:                                  # saturated theme colour, not white-hot
                c[0][1] = list(c[1][1])
            t["brightness"] = min(t["brightness"], 1.25)
            t["transparency"][0][1] = max(t["transparency"][0][1], 0.3)
        for e in p.get("emitters", []):
            if e["name"] == "Shockwave" and len(e["color"]) > 1:
                e["color"][0][1] = [round(0.5 + 0.5 * x, 4) for x in e["color"][1][1]]
    return P


# ======================================================================= export

def load_geometry(assets):
    """Mesh centre (in build coords) and size for each model, from the generators + stats.json."""
    geo = {}
    for stats_path, kind in ((os.path.join(assets, "weapons", "stats.json"), "weapon"),
                             (os.path.join(assets, "items", "stats.json"), "item")):
        if os.path.exists(stats_path):
            for k, v in json.load(open(stats_path)).items():
                geo[k] = (v["bbox_min"], v["bbox_max"])
    return geo


def origins(names):
    from weapons import WEAPONS
    from items_crossbows import CROSSBOWS
    out = {}
    for n in names:
        fn = WEAPONS.get(n) or CROSSBOWS.get(n)
        out[n] = fn()[1]
    return out


def convert(P, assets):
    geo = load_geometry(assets)
    org = origins({p["model"] for p in P.values()})
    out = {}
    for name, p in P.items():
        lo, hi = geo[p["model"]]
        o = org[p["model"]]
        c = [(a + b) / 2 + oo for a, b, oo in zip(lo, hi, o)]       # mesh centre in build coords
        loc = lambda q: [round(q[i] - c[i], 4) for i in range(3)]
        q = dict(meshSize=[round(b - a, 4) for a, b in zip(lo, hi)])
        q["anchors"] = {k: loc(v) for k, v in p.get("anchors", {}).items()}
        q["regions"] = {k: dict(center=loc(r["center"]), size=r["size"]) for k, r in p.get("regions", {}).items()}
        q["orbits"] = [dict(o_, center=loc(o_["center"])) for o_ in p.get("orbits", [])]
        q["emitters"] = p.get("emitters", [])
        q["trails"] = p.get("trails", [])
        q["lights"] = p.get("lights", [])
        beams = []
        for b in p.get("beams", []):
            b = dict(b)
            for key in ("frm", "to"):
                if isinstance(b.get(key), dict):
                    b[key] = dict(center=loc(b[key]["center"]), size=b[key]["size"])
            beams.append(b)
        q["beams"] = beams
        out[name] = q
    return out


def to_lua(v, indent=1, width=110):
    """Serialise to a Luau table literal, keeping short tables on one line."""
    def flat(x):
        if isinstance(x, bool):
            return "true" if x else "false"
        if isinstance(x, (int, float)):
            return repr(round(float(x), 4)) if isinstance(x, float) else str(x)
        if isinstance(x, str):
            return '"' + x + '"'
        if isinstance(x, (list, tuple)):
            return "{" + ", ".join(flat(y) for y in x) + "}"
        return "{" + ", ".join(f"{key(k)} = {flat(y)}" for k, y in x.items()) + "}"

    def key(k):
        return k if k.isidentifier() else f'["{k}"]'

    one = flat(v)
    if not isinstance(v, (list, tuple, dict)) or len(one) + indent * 4 <= width:
        return one
    pad = "\t" * indent
    if isinstance(v, (list, tuple)):
        body = "".join(f"{pad}{to_lua(x, indent + 1, width)},\n" for x in v)
    else:
        body = "".join(f"{pad}{key(k)} = {to_lua(x, indent + 1, width)},\n" for k, x in v.items())
    return "{\n" + body + "\t" * (indent - 1) + "}"


if __name__ == "__main__":
    assets = sys.argv[1] if len(sys.argv) > 1 else "assets"
    data = convert(presets(), assets)
    vfx = os.path.join(assets, "vfx")
    os.makedirs(os.path.join(vfx, "WeaponVFX"), exist_ok=True)
    json.dump(data, open(os.path.join(vfx, "presets.json"), "w"), indent=1)
    header = ("-- GENERATED by tools/vfxgen/presets.py -- edit the Python and regenerate, or tweak values here.\n"
              "-- Positions are offsets from the weapon MeshPart's centre (studs, at the mesh's imported size).\n"
              "-- Colours are {r, g, b} 0-1; sequences are {{time, value[, envelope]}, ...}.\n")
    open(os.path.join(vfx, "WeaponVFX", "Presets.lua"), "w").write(header + "return " + to_lua(data) + "\n")
    for k, v in data.items():
        print(f"{k:22s} emitters={len(v['emitters']):2d} beams={len(v['beams'])} trails={len(v['trails'])} "
              f"lights={len(v['lights'])} orbits={len(v['orbits'])}")
