-- Offset from each item's MeshPart centre to its origin, in studs: the trigger hand (crossbows),
-- the grip (shields), the head centre (helmets, crowns), the ring/pendant centre, or the base
-- (goblets, potions, elixirs). Roblox centres imported meshes, so use this to line items up, e.g.
--   tool.Grip = CFrame.new(ItemOrigins.SiegeCrossbow)
--   accessory.Handle.FaceCenterAttachment.Position = ItemOrigins.JeweledCrown  -- head-centred items
return {
	-- Crossbows
	Crossbow = Vector3.new(0, 0.004, 0.443),
	HuntersCrossbow = Vector3.new(0, 0.004, 0.4),
	SiegeCrossbow = Vector3.new(0, -0.045, 0.594),
	RepeatingCrossbow = Vector3.new(0, -0.1, 0.325),
	DragonbaneArbalest = Vector3.new(0, -0.056, 0.516),
	-- Shields
	Shield = Vector3.new(0, -0.05, 0.213),
	OakBuckler = Vector3.new(0, -0.05, 0.288),
	WardensShield = Vector3.new(0, -0.05, 0.131),
	SunburstShield = Vector3.new(0, -0.05, 0.173),
	DragonscaleAegis = Vector3.new(0, -0.07, 0.13),
	RoyalShield = Vector3.new(0, -0.05, 0.133),
	PolishedRoyalShield = Vector3.new(0, -0.05, 0.13),
	KingsguardRoyalShield = Vector3.new(0, -0.05, 0.122),
	SunwardRoyalShield = Vector3.new(0, -0.05, 0.128),
	SovereignRoyalShield = Vector3.new(0, -0.292, 0.124),
	-- Helmets
	Helmet = Vector3.new(0, -0.266, 0.007),
	ScoutsCap = Vector3.new(-0.125, -0.175, 0.067),
	KnightsVisor = Vector3.new(0, -0.416, -0.035),
	EmberHelm = Vector3.new(0, -0.327, 0.014),
	ChampionsHelm = Vector3.new(0, -0.276, -0.109),
	-- Rings
	Ring = Vector3.new(0, -0.036, 0),
	SapphireBand = Vector3.new(0, -0.045, 0),
	MoonstoneRing = Vector3.new(0, -0.038, 0),
	EmberheartRing = Vector3.new(0, -0.072, 0),
	RingOfKings = Vector3.new(0, -0.052, 0),
	-- Amulets
	Amulet = Vector3.new(0, -0.701, 0),
	LuckyCharm = Vector3.new(0, -0.693, 0),
	OwlEyeAmulet = Vector3.new(0, -0.655, 0.018),
	WyrmscaleAmulet = Vector3.new(0, -0.674, 0.017),
	HeartOfTheSun = Vector3.new(0.013, -0.687, 0.006),
	StarAmulet = Vector3.new(0, -0.727, 0),
	PolishedStarAmulet = Vector3.new(0, -0.725, 0),
	MoonstoneStarAmulet = Vector3.new(-0.017, -0.673, 0.004),
	CelestialStarAmulet = Vector3.new(0, -0.703, 0.005),
	NorthStarAmulet = Vector3.new(0, -0.75, 0.008),
	-- Goblets
	Goblet = Vector3.new(0, -0.481, 0),
	FeastGoblet = Vector3.new(0, -0.506, 0),
	MoonlitGoblet = Vector3.new(0, -0.631, 0),
	RoyalChalice = Vector3.new(0, -0.531, 0),
	GrailOfAges = Vector3.new(0, -0.506, 0.003),
	-- Crowns
	Crown = Vector3.new(0, -0.55, 0),
	SilverCirclet = Vector3.new(0, -0.4, 0.017),
	JeweledCrown = Vector3.new(0, -0.74, 0),
	FrostQueensCrown = Vector3.new(0, -0.605, 0.021),
	DragonCrown = Vector3.new(0, -0.522, 0.008),
	-- Potions
	Potion = Vector3.new(0, -0.502, 0),
	HealersDraught = Vector3.new(0, -0.5, 0),
	SwiftfootTonic = Vector3.new(0, -0.637, 0),
	GiantsStrengthBrew = Vector3.new(-0.033, -0.562, 0),
	PhoenixTears = Vector3.new(0, -0.615, 0),
	-- Elixirs
	Elixir = Vector3.new(0, -0.666, 0),
	ElixirOfClarity = Vector3.new(0, -0.529, 0),
	MoonwellElixir = Vector3.new(0, -0.546, 0.009),
	ElixirOfAges = Vector3.new(0, -0.546, 0),
	StarlightElixir = Vector3.new(-0.018, -0.68, 0),
}
