#!/usr/bin/env python3
"""Generates the minehouse-parity datapack: block_based GameTests that run on
both vanilla 26.3 (net.minecraft.gametest.Main) and Pumpkin (pumpkin-tester).

Each test is a small structure. Most tests use a "checker": a repeating command
block that runs `execute if <condition> run setblock ~ ~1 ~ redstone_block`,
which powers the accept test block above it. A test passes once the condition
holds and fails when max_ticks runs out.

Run: python3 tools/minehouse-parity/gen_tests.py  (needs `pip install nbtlib`)
"""
from pathlib import Path

import nbtlib
from nbtlib.tag import Byte, Compound, Int, List, String

DATA_VERSION = 5023  # 26.3
NS = "minehouse"
ROOT = Path(__file__).resolve().parents[2] / "assets/tests/datapacks/minehouse-parity"


def item(slot, id_, count=1):
    return {"Slot": Byte(slot), "id": String(id_), "count": Int(count)}


class Test:
    def __init__(self, name, size, max_ticks=100, floor="minecraft:stone"):
        self.name, self.size, self.max_ticks = name, size, max_ticks
        self.blocks = {}
        sx, _, sz = size
        for x in range(sx):
            for z in range(sz):
                self.set((x, 0, z), floor)

    def set(self, pos, block, props=None, nbt=None):
        self.blocks[tuple(pos)] = (block, props or {}, nbt)

    def start(self, pos):
        self.set(pos, "minecraft:test_block", {"mode": "start"},
                 {"id": "minecraft:test_block", "mode": "start", "message": "", "powered": Byte(0)})

    def accept(self, pos):
        self.set(pos, "minecraft:test_block", {"mode": "accept"},
                 {"id": "minecraft:test_block", "mode": "accept", "message": "", "powered": Byte(0)})

    def command(self, pos, cmd, kind="command_block", auto=False, facing="up"):
        self.set(pos, f"minecraft:{kind}", {"conditional": "false", "facing": facing},
                 {"id": "minecraft:command_block", "Command": cmd, "auto": Byte(int(auto)),
                  "powered": Byte(0), "conditionMet": Byte(0), "TrackOutput": Byte(0),
                  "UpdateLastExecution": Byte(1), "SuccessCount": Int(0)})

    def checker(self, pos, condition):
        """Start block at `pos` with a checker column stacked on top of it.

        A repeating command block only runs while it is powered (an `auto`
        block loaded from a structure never gets its first tick), so the start
        pulse fires an impulse block that places a redstone block under the
        repeating block. The repeating block then checks `condition` every
        tick and, once it holds, places a redstone block that powers the
        accept block. The four horizontal neighbours of `pos` stay free, so the
        start pulse can also trigger the mechanism under test.

        `condition` is a callable that turns a structure position into the
        `~x ~y ~z` form relative to the repeating block.
        """
        x, y, z = pos
        self.start(pos)
        self.command((x, y + 1, z), "setblock ~ ~1 ~ minecraft:redstone_block")
        rx, ry, rz = x, y + 3, z
        def rel(p):
            if all(isinstance(c, int) for c in p):
                return f"~{p[0]-rx} ~{p[1]-ry} ~{p[2]-rz}"
            # a float point: command blocks execute at their block centre
            return " ".join(f"~{round(c - (o + 0.5), 3):g}" for c, o in zip(p, (rx, ry, rz)))

        clause = condition(rel)
        if not clause.startswith(("if ", "unless ", "positioned ")):
            clause = f"if {clause}"
        self.command((rx, ry, rz), f"execute {clause} run setblock ~ ~1 ~ minecraft:redstone_block",
                     kind="repeating_command_block")
        self.accept((x, y + 5, z))

    def write(self):
        palette, index, blocks = [], {}, []
        for pos, (block, props, nbt) in sorted(self.blocks.items()):
            key = (block, tuple(sorted(props.items())))
            if key not in index:
                index[key] = len(palette)
                entry = {"id": String(block)}
                if props:
                    entry["properties"] = Compound({k: String(v) for k, v in props.items()})
                palette.append(Compound(entry))
            b = {"pos": List[Int]([Int(c) for c in pos]), "state": Int(index[key])}
            if nbt is not None:
                b["nbt"] = nbtlib.parse_nbt(nbtlib.serialize_tag(Compound(_tagify(nbt))))
            blocks.append(Compound(b))
        root = Compound({
            "DataVersion": Int(DATA_VERSION),
            "size": List[Int]([Int(c) for c in self.size]),
            "palette": List[Compound](palette),
            "blocks": List[Compound](blocks),
            "entities": List[Compound]([]),
        })
        sdir = ROOT / "data" / NS / "structure"
        tdir = ROOT / "data" / NS / "test_instance"
        sdir.mkdir(parents=True, exist_ok=True)
        tdir.mkdir(parents=True, exist_ok=True)
        nbtlib.File(root).save(sdir / f"{self.name}.nbt", gzipped=True)
        (tdir / f"{self.name}.json").write_text(
            '{\n  "type": "minecraft:block_based",\n  "environment": "minecraft:default",\n'
            f'  "structure": "{NS}:{self.name}",\n  "max_ticks": {self.max_ticks},\n'
            '  "manual_only": false\n}\n')


def _tagify(v):
    if isinstance(v, dict):
        return Compound({k: _tagify(x) for k, x in v.items()})
    if isinstance(v, list):
        return List[Compound]([_tagify(x) for x in v])
    if isinstance(v, str):
        return String(v)
    return v


TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


@test
def redstone_wire_15():
    t = Test("redstone_wire_15", (17, 2, 1), max_ticks=20)
    t.start((0, 1, 0))
    for x in range(1, 16):
        t.set((x, 1, 0), "minecraft:redstone_wire",
              {"east": "side", "west": "side", "north": "none", "south": "none", "power": "0"})
    t.accept((16, 1, 0))
    return t


@test
def comparator_reads_chest():
    # a hopper fills the chest; the comparator reacts to the content change
    t = Test("comparator_reads_chest", (5, 3, 1), max_ticks=40)
    t.start((4, 1, 0))
    t.set((0, 1, 0), "minecraft:chest", {"facing": "north", "type": "single", "waterlogged": "false"},
          {"id": "minecraft:chest", "Items": []})
    t.set((0, 2, 0), "minecraft:hopper", {"facing": "down", "enabled": "true"},
          {"id": "minecraft:hopper", "Items": [item(0, "minecraft:cobblestone", 64)], "TransferCooldown": Int(0)})
    t.set((1, 1, 0), "minecraft:comparator", {"facing": "west", "mode": "compare", "powered": "false"})
    t.accept((2, 1, 0))
    return t


@test
def command_execute_if_items():
    # `execute if items` itself (container checks elsewhere use `if data`)
    t = Test("command_execute_if_items", (3, 7, 1), max_ticks=20)
    t.set((0, 1, 0), "minecraft:chest", {"facing": "north", "type": "single", "waterlogged": "false"},
          {"id": "minecraft:chest", "Items": [item(0, "minecraft:diamond")]})
    t.checker((2, 1, 0), lambda r: f"items block {r((0, 1, 0))} container.* minecraft:diamond")
    return t


@test
def piston_pushes_block():
    t = Test("piston_pushes_block", (4, 7, 3), max_ticks=40)
    t.checker((0, 1, 1), lambda r: f"block {r((3, 1, 1))} minecraft:gold_block")
    t.set((1, 1, 1), "minecraft:piston", {"facing": "east", "extended": "false"})
    t.set((2, 1, 1), "minecraft:gold_block")
    return t


@test
def hopper_fills_chest():
    t = Test("hopper_fills_chest", (3, 7, 1), max_ticks=40)
    t.set((0, 1, 0), "minecraft:chest", {"facing": "north", "type": "single", "waterlogged": "false"},
          {"id": "minecraft:chest", "Items": []})
    t.set((0, 2, 0), "minecraft:hopper", {"facing": "down", "enabled": "true"},
          {"id": "minecraft:hopper", "Items": [item(0, "minecraft:diamond")], "TransferCooldown": Int(0)})
    t.checker((2, 1, 0), lambda r: f'data block {r((0, 1, 0))} Items[{{id:"minecraft:diamond"}}]')
    return t


@test
def hopper_picks_up_item():
    t = Test("hopper_picks_up_item", (3, 7, 1), max_ticks=60)
    t.set((0, 1, 0), "minecraft:chest", {"facing": "north", "type": "single", "waterlogged": "false"},
          {"id": "minecraft:chest", "Items": []})
    t.set((0, 2, 0), "minecraft:hopper", {"facing": "down", "enabled": "true"},
          {"id": "minecraft:hopper", "Items": [], "TransferCooldown": Int(0)})
    t.checker((2, 1, 0), lambda r: f'data block {r((0, 1, 0))} Items[{{id:"minecraft:emerald"}}]')
    t.command((1, 1, 0), 'summon item ~-1 ~2.2 ~ {Item:{id:"minecraft:emerald",count:1}}')
    return t


@test
def furnace_smelts_iron():
    t = Test("furnace_smelts_iron", (3, 7, 1), max_ticks=320)
    t.set((0, 1, 0), "minecraft:furnace", {"facing": "north", "lit": "false"},
          {"id": "minecraft:furnace",
           "Items": [item(0, "minecraft:raw_iron"), item(1, "minecraft:coal")]})
    t.checker((2, 1, 0), lambda r: f'data block {r((0, 1, 0))} Items[{{Slot:2b,id:"minecraft:iron_ingot"}}]')
    return t


@test
def dispenser_water_flows_7():
    t = Test("dispenser_water_flows_7", (10, 8, 3), max_ticks=100)
    # glass walls keep the stream one block wide
    for x in range(0, 10):
        t.set((x, 1, 0), "minecraft:glass")
        t.set((x, 1, 2), "minecraft:glass")
    t.set((0, 1, 1), "minecraft:glass")
    t.set((1, 2, 1), "minecraft:dispenser", {"facing": "down", "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": [item(0, "minecraft:water_bucket")]})
    t.checker((2, 2, 1), lambda r: f"block {r((8, 1, 1))} minecraft:water")
    return t


@test
def water_meets_lava_obsidian():
    t = Test("water_meets_lava_obsidian", (5, 8, 3), max_ticks=100)
    for x in range(0, 5):
        t.set((x, 1, 0), "minecraft:glass")
        t.set((x, 1, 2), "minecraft:glass")
    t.set((0, 1, 1), "minecraft:glass")
    t.set((4, 1, 1), "minecraft:glass")
    t.set((1, 2, 1), "minecraft:dispenser", {"facing": "down", "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": [item(0, "minecraft:lava_bucket")]})
    t.set((3, 2, 1), "minecraft:dispenser", {"facing": "down", "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": [item(0, "minecraft:water_bucket")]})
    t.checker((2, 2, 1), lambda r: f"block {r((1, 1, 1))} minecraft:obsidian")
    return t


@test
def tnt_breaks_stone():
    t = Test("tnt_breaks_stone", (9, 7, 5), max_ticks=120)
    t.set((1, 1, 1), "minecraft:tnt", {"unstable": "false"})
    for x in range(2, 8):
        t.set((x, 1, 1), "minecraft:redstone_wire",
              {"east": "side", "west": "side", "north": "none", "south": "none", "power": "0"})
    t.set((1, 1, 3), "minecraft:stone")
    t.checker((8, 1, 1), lambda r: f"block {r((1, 1, 3))} minecraft:air")
    return t


@test
def iron_golem_from_blocks():
    t = Test("iron_golem_from_blocks", (4, 10, 3), max_ticks=40)
    t.set((1, 1, 1), "minecraft:iron_block")
    t.set((1, 2, 1), "minecraft:iron_block")
    t.set((0, 2, 1), "minecraft:iron_block")
    t.set((2, 2, 1), "minecraft:iron_block")
    t.set((1, 4, 1), "minecraft:dispenser", {"facing": "down", "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": [item(0, "minecraft:carved_pumpkin")]})
    t.checker((2, 4, 1), lambda r: "entity @e[type=minecraft:iron_golem,distance=..8]")
    return t


@test
def snow_golem_from_blocks():
    t = Test("snow_golem_from_blocks", (2, 10, 1), max_ticks=40)
    t.set((0, 1, 0), "minecraft:snow_block")
    t.set((0, 2, 0), "minecraft:snow_block")
    t.set((0, 4, 0), "minecraft:dispenser", {"facing": "down", "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": [item(0, "minecraft:carved_pumpkin")]})
    t.checker((1, 4, 0), lambda r: "entity @e[type=minecraft:snow_golem,distance=..8]")
    return t


@test
def nether_portal_lights():
    t = Test("nether_portal_lights", (4, 8, 2), max_ticks=40)
    # 4x5 obsidian frame in the x/y plane at z=1, inner 2x3 at x=1..2, y=2..4
    for x in range(0, 4):
        t.set((x, 1, 1), "minecraft:obsidian")
        t.set((x, 5, 1), "minecraft:obsidian")
    for y in range(2, 5):
        t.set((0, y, 1), "minecraft:obsidian")
        t.set((3, y, 1), "minecraft:obsidian")
    t.set((1, 2, 0), "minecraft:dispenser", {"facing": "south", "triggered": "false"},
          {"id": "minecraft:dispenser", "Items": [item(0, "minecraft:flint_and_steel")]})
    t.checker((2, 2, 0), lambda r: f"block {r((1, 3, 1))} minecraft:nether_portal")
    return t


import mobs  # noqa: E402

_mob_builder = mobs.MobTestBuilder(Test)
mobs.register(_mob_builder)
TESTS.extend(_mob_builder.tests)


if __name__ == "__main__":
    import shutil
    shutil.rmtree(ROOT / "data", ignore_errors=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "pack.mcmeta").write_text(
        '{\n  "pack": {\n    "description": "MineHouse vanilla parity GameTests",\n'
        '    "min_format": [107, 1],\n    "max_format": 107\n  }\n}\n')
    for fn in TESTS:
        fn().write()
    print(f"wrote {len(TESTS)} tests to {ROOT}")
