"""Registry of shop items by category (folder name -> {ModelName: builder})."""
from items_crossbows import CROSSBOWS
from items_headwear import CROWNS, HELMETS
from items_jewelry import AMULETS, RINGS
from items_shields import SHIELDS
from items_vessels import ELIXIRS, GOBLETS, POTIONS

CATEGORIES = {
    "Crossbows": CROSSBOWS,
    "Shields": SHIELDS,
    "Helmets": HELMETS,
    "Rings": RINGS,
    "Amulets": AMULETS,
    "Goblets": GOBLETS,
    "Crowns": CROWNS,
    "Potions": POTIONS,
    "Elixirs": ELIXIRS,
}

# Texture atlas size per category: small items never fill the screen, so 512 is plenty.
ATLAS_SIZE = {"Crossbows": 1024, "Shields": 1024, "Helmets": 1024, "Crowns": 1024,
              "Rings": 512, "Amulets": 512, "Goblets": 512, "Potions": 512, "Elixirs": 512}
