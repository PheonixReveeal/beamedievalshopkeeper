# swordgen

Procedural sword generator. Builds detailed, textured (PBR) sword models as `.glb` files.

```
pip install numpy trimesh pillow scipy
python tools/swordgen/swordgen.py assets/models
```

Import into Roblox Studio with **File → Import 3D** (or the Avatar/3D Importer) and pick the `.glb`.
Each part (Blade, Guard, Grip, Pommel, ...) comes in as its own MeshPart and stays under Roblox's
20k-triangle-per-mesh limit. The origin is the centre of the crossguard (the hand position),
which makes it easy to use as a Tool's Handle.
