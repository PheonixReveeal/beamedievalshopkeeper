"""Package the Luau sources as Roblox model files (.rbxmx) for Studio's "Insert from File".

    python tools/vfxgen/bundle.py      -> assets/vfx/roblox/*.rbxmx
"""
import os
from xml.sax.saxutils import escape

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VFX = os.path.join(ROOT, "assets", "vfx")
_ref = [0]


def item(cls, name, source=None, children=()):
    _ref[0] += 1
    props = f'<string name="Name">{escape(name)}</string>'
    if source is not None:
        assert "]]>" not in source, f"{name}: source contains ']]>'"
        props += f'<ProtectedString name="Source"><![CDATA[{source}]]></ProtectedString>'
    kids = "".join(children)
    return f'<Item class="{cls}" referent="RBX{_ref[0]}"><Properties>{props}</Properties>{kids}</Item>'


def model(*items):
    return ('<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">'
            + "".join(items) + "</roblox>\n")


def src(*p):
    return open(os.path.join(VFX, *p)).read()


if __name__ == "__main__":
    out = os.path.join(VFX, "roblox")
    os.makedirs(out, exist_ok=True)
    files = {
        "WeaponVFX.rbxmx": model(item("ModuleScript", "WeaponVFX", src("WeaponVFX", "init.lua"), [
            item("ModuleScript", "Presets", src("WeaponVFX", "Presets.lua")),
            item("ModuleScript", "Textures", src("WeaponVFX", "Textures.lua")),
        ])),
        "WeaponVFXClient.rbxmx": model(item("LocalScript", "WeaponVFXClient", src("WeaponVFXClient.client.lua"))),
        "WeaponVFXTool.rbxmx": model(item("Script", "WeaponVFXTool", src("WeaponVFXTool.server.lua"))),
    }
    for name, xml in files.items():
        open(os.path.join(out, name), "w").write(xml)
        print(name, len(xml), "bytes")
