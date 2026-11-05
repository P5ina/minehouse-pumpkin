"""One GameTest per mob (every summonable mob of 26.3).

Each test checks one vanilla behaviour of that mob that can be observed with
commands, picked so it is deterministic on the vanilla server:

  fall      summoned 4 blocks up, lands on the floor (gravity + collision)
  exists    flying/huge mobs: summoned and still there next tick
  breed     two adults in love (InLove) make a baby
  convert   turns into another mob (lightning, water, powder snow, Nether-only mobs)
  shear     a dispenser with shears shears it
  burn      burns to death in daylight
  kill      kills another mob (target carries a marker passenger, so "gone" can't
            pass before the target exists)
  custom    anything else (split on death, golem from blocks, growth...)

Layout: start block at (0,1,2) with the checker column on top (see
gen_tests.Test.checker); up to three impulse command blocks at (1,1,2),
(0,1,1) and (0,1,3) run the setup commands from the start pulse. The pen is a
glass box starting at x=3. Selectors use the pen volume (`positioned` + dx/dy/dz)
so tests placed next to each other never see each other's mobs.
"""
import json
import math
from pathlib import Path

ENTITIES = json.loads((Path(__file__).resolve().parents[2] / "assets/entities.json").read_text())

START = (0, 1, 2)
IMPULSES = [(1, 1, 2), (0, 1, 1), (0, 1, 3)]
PEN_X = 3
PERSIST = "PersistenceRequired:1b"


def mob_size(mob):
    w, h = ENTITIES[mob]["dimension"]
    return w, h


class Pen:
    def __init__(self, t, inner_w, inner_h, walls=3, roof=False, floor=None):
        self.t, self.w, self.h = t, inner_w, inner_h
        self.x0, self.z0 = PEN_X + 1, 1  # first interior block
        x1, z1 = self.x0 + inner_w, self.z0 + inner_w
        for x in range(PEN_X, x1 + 1):
            for z in range(0, z1 + 1):
                edge = x in (PEN_X, x1) or z in (0, z1)
                for y in range(1, walls + 1):
                    if edge:
                        t.set((x, y, z), "minecraft:glass")
                if roof:
                    t.set((x, walls + 1, z), "minecraft:glass")
                if floor and not edge:
                    t.set((x, 0, z), floor)

    @property
    def center(self):
        return (self.x0 + self.w / 2, 1.0, self.z0 + self.w / 2)

    def fill(self, block, y_from=1, y_to=1):
        for x in range(self.x0, self.x0 + self.w):
            for z in range(self.z0, self.z0 + self.w):
                for y in range(y_from, y_to + 1):
                    self.t.set((x, y, z), block)

    def box(self, selector, dy=None):
        dy = self.h if dy is None else dy
        return f"@e[{selector},dx={self.w - 1},dy={dy},dz={self.w - 1}]"

    def at(self, rel, y=1.0):
        return f"positioned {rel((float(self.x0), y, float(self.z0)))}"

    def back(self, rel, y=1.0):
        """Undo at(): `run setblock ~ ~1 ~` must still be relative to the checker."""
        offs = rel((float(self.x0), y, float(self.z0))).split()
        neg = []
        for o in offs:
            v = float(o[1:] or 0)
            neg.append(f"~{-v:g}" if v else "~")
        return "positioned " + " ".join(neg)

    def sel(self, rel, selector, y=1.0, dy=None):
        """`positioned … if entity @e[…]` limited to the pen interior."""
        return f"{self.at(rel, y)} if entity {self.box(selector, dy)} {self.back(rel, y)}"

    def gone(self, rel, mob_selector):
        """The marker stand is in the pen and the marked mob is not."""
        return (f"{self.at(rel)} if entity {self.box('type=minecraft:armor_stand,tag=mh_mark')}"
                f" unless entity {self.box(mob_selector)} {self.back(rel)}")


def pen_for(t, mob, walls=3, roof=False, extra=0, floor=None):
    w, h = mob_size(mob)
    inner = max(3, math.ceil(w) + 2) + extra
    return Pen(t, inner, math.ceil(h) + 1, walls=max(walls, 2), roof=roof, floor=floor)


def at(rel, p):
    return rel(p)


def size_for(pen):
    return (pen.x0 + pen.w + 1, 12, max(5, pen.z0 + pen.w + 1))


class MobTestBuilder:
    def __init__(self, Test):
        self.Test = Test
        self.tests = []

    def make(self, name, mob, max_ticks, build):
        """build(t) -> (pen, condition(rel) -> str, [command(rel) -> str])"""
        Test = self.Test

        def fn():
            t = Test(f"mob_{mob}", (1, 1, 1), max_ticks=max_ticks)
            pen, cond, cmds = build(t)
            sx, sy, sz = size_for(pen)
            t.size = (sx, max(sy, pen.h + 8), sz)
            # floor under the whole structure
            for x in range(sx):
                for z in range(sz):
                    t.blocks.setdefault((x, 0, z), ("minecraft:stone", {}, None))
            t.checker(START, cond)
            assert len(cmds) <= len(IMPULSES), name
            for pos, cmd in zip(IMPULSES, cmds):
                cx, cy, cz = pos
                rel = lambda p, cx=cx, cy=cy, cz=cz: _rel((cx, cy, cz), p)
                t.command(pos, cmd(rel))
            return t

        fn.__name__ = name
        self.tests.append(fn)


def _rel(cmd_block, p):
    """Relative coordinates from a command block (executes at its block centre)
    to point p. Integer components of p mean the block's centre."""
    out = []
    for c, v in zip(cmd_block, p):
        target = v + 0.5 if isinstance(v, int) else v
        d = round(target - (c + 0.5), 3)
        out.append(f"~{d:g}" if d else "~")
    return " ".join(out)


def tag(mob):
    return f"mh_{mob}"


def summon(mob, pos, nbt=""):
    extra = f",{nbt}" if nbt else ""
    return lambda rel: f"summon {mob} {rel(pos)} {{{PERSIST},Tags:[\"{tag(mob)}\"]{extra}}}"


def with_marker(mob, pos, nbt=""):
    """Summon `mob` with an invisible armor stand riding it. The stand stays
    when the mob dies, so `if stand unless mob` means "the mob was there and is
    gone now"."""
    extra = f",{nbt}" if nbt else ""
    stand = '{id:"minecraft:armor_stand",Invisible:1b,Marker:1b,NoGravity:1b,Tags:["mh_mark"]}'
    return lambda rel: (f"summon {mob} {rel(pos)} {{{PERSIST},Tags:[\"{tag(mob)}_t\"],"
                        f"Passengers:[{stand}]{extra}}}")


def register(b):
    """All mob tests. `b` is a MobTestBuilder."""

    # ---------------- fall: lands on the floor ----------------
    for mob in [
        "dolphin", "turtle", "polar_bear", "sniffer", "mule", "skeleton_horse", "zombie_horse",
        "camel_husk", "wandering_trader", "witch", "wither_skeleton", "zombified_piglin",
        "illusioner", "giant", "spider", "cave_spider", "endermite", "silverfish", "warden",
        "breeze", "creaking", "parched", "sulfur_cube", "nautilus", "zombie_nautilus",
        "elder_guardian",  # did not kill a squid reliably within 1500 ticks
        "goat",  # goat breeding is random (rams, long jumps), so goats only get the fall test
    ]:
        def build(t, mob=mob):
            pen = pen_for(t, mob, walls=2)
            cx, _, cz = pen.center
            cmd = summon(mob, (cx, 5.0, cz), "NoAI:0b")
            # feet below y=2 means it fell from y=5 and stands on the floor
            cond = lambda rel: pen.sel(rel, f"type=minecraft:{mob},tag={tag(mob)}", y=1.0, dy=0)
            return pen, cond, [cmd]
        b.make(f"mob_{mob}", mob, 80, build)

    # ---------------- exists: flying or huge mobs ----------------
    for mob in ["parrot", "bat", "allay", "vex", "blaze", "ghast", "happy_ghast", "phantom", "shulker",
                "ender_dragon", "wither"]:
        def build(t, mob=mob):
            pen = pen_for(t, mob, walls=2)
            cx, _, cz = pen.center
            cmd = summon(mob, (cx, 1.0, cz), "NoAI:1b")
            cond = lambda rel: pen.sel(rel, f"type=minecraft:{mob},tag={tag(mob)}", dy=pen.h + 2)
            return pen, cond, [cmd]
        b.make(f"mob_{mob}", mob, 40, build)

    # ---------------- breed: two adults in love make a baby ----------------
    breeders = {
        "cow": "", "chicken": "", "rabbit": "", "fox": "",
        "bee": "", "strider": "", "camel": "", "armadillo": "", "axolotl": "",
        "ocelot": "", "panda": "",
        "horse": "Tame:1b", "donkey": "Tame:1b", "llama": "Tame:1b", "trader_llama": "Tame:1b",
    }
    for mob, nbt in breeders.items():
        def build(t, mob=mob, nbt=nbt):
            pen = pen_for(t, mob, walls=3, roof=mob == "bee", extra=2 if mob == "panda" else 0)
            cx, _, cz = pen.center
            love = "InLove:600,Age:0" + (f",{nbt}" if nbt else "")
            a = summon(mob, (cx - 0.6, 1.0, cz), love)
            c = summon(mob, (cx + 0.6, 1.0, cz), love)
            if mob == "panda":
                # pandas only breed with bamboo nearby: a row along the back wall
                row = pen.z0 + pen.w - 1
                for i in range(pen.w):
                    t.set((pen.x0 + i, 0, row), "minecraft:dirt")
                    t.set((pen.x0 + i, 1, row), "minecraft:bamboo",
                          {"age": "0", "leaves": "none", "stage": "0"})
            # the baby is the one without our tag
            cond = lambda rel: pen.sel(rel, f"type=minecraft:{mob},tag=!{tag(mob)}")
            return pen, cond, [a, c]
        b.make(f"mob_{mob}", mob, 300, build)

    # ---------------- convert ----------------
    def lightning(mob, into, check=None):
        def build(t):
            pen = pen_for(t, mob, walls=3)
            p = pen.center
            cond = check or (lambda rel: pen.sel(rel, f"type=minecraft:{into}"))
            return pen, (lambda rel: cond(rel) if check is None else check(pen, rel)), [
                summon(mob, p, "NoAI:1b"),
                lambda rel: f"summon lightning_bolt {rel(p)}",
            ]
        b.make(f"mob_{mob}", mob, 60, build)

    lightning("pig", "zombified_piglin")
    lightning("villager", "witch")
    lightning("creeper", None, check=lambda pen, rel: pen.sel(rel, "type=minecraft:creeper,nbt={powered:1b}"))

    def nether_mob(mob, into):
        def build(t):
            pen = pen_for(t, mob, walls=3)
            return pen, (lambda rel: pen.sel(rel, f"type=minecraft:{into}")), [summon(mob, pen.center)]
        b.make(f"mob_{mob}", mob, 500, build)

    nether_mob("piglin", "zombified_piglin")
    nether_mob("piglin_brute", "zombified_piglin")
    nether_mob("hoglin", "zoglin")

    def submerged(mob, into, block, ticks):
        def build(t):
            pen = pen_for(t, mob, walls=4)
            pen.fill(block, 1, 3)
            return pen, (lambda rel: pen.sel(rel, f"type=minecraft:{into}")), [summon(mob, pen.center)]
        b.make(f"mob_{mob}", mob, ticks, build)

    submerged("zombie", "drowned", "minecraft:water", 1000)
    submerged("husk", "zombie", "minecraft:water", 1000)
    submerged("skeleton", "stray", "minecraft:powder_snow", 800)

    def tadpole(t):
        pen = pen_for(t, "tadpole", walls=3)
        pen.fill("minecraft:water", 1, 2)
        return pen, (lambda rel: pen.sel(rel, "type=minecraft:frog")), [
            summon("tadpole", pen.center, "Age:23980")]
    b.make("mob_tadpole", "tadpole", 80, tadpole)

    # ---------------- shear: dispenser with shears ----------------
    def shear(mob, cond_of):
        def build(t):
            pen = pen_for(t, mob, walls=3)
            # mob in the middle of the first row, dispenser in the wall facing it
            mx = pen.x0 + pen.w // 2
            disp = (mx, 1, 0)
            t.set(disp, "minecraft:dispenser", {"facing": "south", "triggered": "false"},
                  {"id": "minecraft:dispenser", "Items": [{"Slot": __import__("nbtlib").tag.Byte(0),
                   "id": "minecraft:shears", "count": __import__("nbtlib").tag.Int(1)}]})
            t.set((mx, 2, 0), "minecraft:glass")
            return pen, (lambda rel: cond_of(pen, rel)), [
                summon(mob, (mx + 0.5, 1.0, 1.5), "NoAI:1b"),
                lambda rel: f"setblock {rel((mx, 2, 0))} minecraft:redstone_block",
            ]
        b.make(f"mob_{mob}", mob, 60, build)

    item_sel = lambda item: f'type=minecraft:item,nbt={{Item:{{id:"minecraft:{item}"}}}}'
    shear("sheep", lambda pen, rel: pen.sel(rel, item_sel("white_wool")))
    shear("mooshroom", lambda pen, rel: pen.sel(rel, "type=minecraft:cow"))
    shear("bogged", lambda pen, rel: pen.sel(rel, "type=minecraft:item"))
    shear("snow_golem", lambda pen, rel: pen.sel(rel, item_sel("carved_pumpkin")))

    # ---------------- burn: dies in daylight ----------------
    for mob in ["drowned", "stray", "zombie_villager"]:
        def build(t, mob=mob):
            pen = pen_for(t, mob, walls=3, roof=True)
            gone = lambda rel: pen.gone(rel, f"type=minecraft:{mob}")
            return pen, gone, [
                lambda rel: "time set 6000",
                lambda rel: "weather clear",
                with_marker(mob, pen.center),
            ]
        b.make(f"mob_{mob}", mob, 1200, build)

    # ---------------- kill: attacker kills a marked target ----------------
    def kill(mob, target, attacker_nbt="", extra=1, water=False, target_nbt=""):
        def build(t):
            big = max(mob_size(mob)[0], mob_size(target)[0])
            pen = Pen(t, max(4, math.ceil(big) + 3) + extra, 4, walls=4, roof=True)
            if water:
                pen.fill("minecraft:water", 1, 4)
            x0, z0 = pen.x0, pen.z0
            far = pen.x0 + pen.w - 1
            gone = lambda rel: pen.gone(rel, f"type=minecraft:{target},tag={tag(target)}_t")
            return pen, gone, [
                summon(mob, (x0 + 0.5, 1.0, z0 + 0.5), attacker_nbt),
                with_marker(target, (far + 0.5, 1.0, z0 + pen.w - 0.5), target_nbt),
            ]
        b.make(f"mob_{mob}", mob, 1500, build)

    kill("iron_golem", "zombie")
    kill("zoglin", "cow")
    kill("vindicator", "villager", 'equipment:{mainhand:{id:"minecraft:iron_axe"}}', target_nbt="NoAI:1b")
    kill("pillager", "villager", 'equipment:{mainhand:{id:"minecraft:crossbow"}}', target_nbt="NoAI:1b")
    kill("ravager", "villager", target_nbt="NoAI:1b")
    kill("guardian", "squid", water=True)
    kill("frog", "slime", target_nbt="Size:0")
    # tamed wolves and cats never bred in a test (no owner online), so test hunting
    kill("wolf", "sheep")
    kill("cat", "rabbit")

    # ---------------- fish and squid die out of water ----------------
    for mob in ["cod", "salmon", "tropical_fish", "pufferfish", "squid", "glow_squid"]:
        def build(t, mob=mob):
            pen = pen_for(t, mob, walls=2, roof=True)
            gone = lambda rel: pen.gone(rel, f"type=minecraft:{mob}")
            return pen, gone, [with_marker(mob, pen.center)]
        b.make(f"mob_{mob}", mob, 900, build)

    # ---------------- custom ----------------
    def evoker(t):
        pen = Pen(t, 6, 4, walls=4, roof=True)
        return pen, (lambda rel: pen.sel(rel, "type=minecraft:vex")), [
            summon("evoker", (pen.x0 + 0.5, 1.0, pen.z0 + 0.5)),
            summon("villager", (pen.x0 + 5.5, 1.0, pen.z0 + 5.5), "NoAI:1b"),
        ]
    b.make("mob_evoker", "evoker", 400, evoker)

    def split(mob):
        def build(t):
            pen = pen_for(t, mob, walls=3, roof=True)
            # children copy the tags, so look for the small size instead
            return pen, (lambda rel: pen.sel(rel, f"type=minecraft:{mob},nbt={{Size:0}}")), [
                summon(mob, pen.center, "Size:1"),
                lambda rel: f"kill @e[type=minecraft:{mob},tag={tag(mob)},distance=..12]",
            ]
        b.make(f"mob_{mob}", mob, 80, build)

    split("slime")
    split("magma_cube")

    def enderman(t):
        pen = pen_for(t, "enderman", walls=4)
        pen.fill("minecraft:water", 1, 1)
        # water hurts it and it teleports away: alive somewhere, but not in the pool
        return pen, (lambda rel: f"{pen.at(rel)} unless entity {pen.box('type=minecraft:enderman')}"
                     f" if entity @e[type=minecraft:enderman,tag={tag('enderman')},distance=..64] {pen.back(rel)}"), [
            summon("enderman", pen.center)]
    b.make("mob_enderman", "enderman", 200, enderman)

    def copper_golem(t):
        pen = Pen(t, 3, 3, walls=2)
        x, z = pen.x0 + 1, pen.z0 + 1
        t.set((x, 1, z), "minecraft:copper_block")
        t.set((x, 3, z), "minecraft:dispenser", {"facing": "down", "triggered": "false"},
              {"id": "minecraft:dispenser", "Items": [{"Slot": __import__("nbtlib").tag.Byte(0),
               "id": "minecraft:carved_pumpkin", "count": __import__("nbtlib").tag.Int(1)}]})
        return pen, (lambda rel: pen.sel(rel, "type=minecraft:copper_golem", dy=4)), [
            lambda rel: f"setblock {rel((x, 4, z))} minecraft:redstone_block"]
    b.make("mob_copper_golem", "copper_golem", 60, copper_golem)
