# MineHouse vanilla parity tests

GameTests that run unchanged on the vanilla 26.3 server and on Pumpkin. A test
that passes on vanilla and fails on Pumpkin is a gap we have to close before
moving the survival server.

- `gen_tests.py` builds the datapack in `assets/tests/datapacks/minehouse-parity`
  (structures + `block_based` test instances). Edit tests there, then run
  `pip install nbtlib && python3 tools/minehouse-parity/gen_tests.py` and
  `cargo run --locked -p pumpkin-codegen -- test_instance.rs` and
  `cargo run --locked -p pumpkin-codegen -- structure_template.rs`.
- `known-gaps.txt` lists tests that pass on vanilla but not yet on Pumpkin.
- `compare.py` compares both runs; the `Vanilla parity` workflow runs it on
  every push and PR.

## How a test works

Each test is a small structure with a start test block. A checker column on top
of the start block holds an impulse command block (fired by the start pulse)
that powers a repeating command block. The repeating block runs
`execute if <condition>` every tick and powers the accept block once the
condition holds. The test fails when `max_ticks` runs out. Mechanisms next to
the start block (pistons, dispensers, wire) get the same start pulse.

Use `execute if data` for container contents: it works on both servers.

## Mob tests

`mobs.py` adds one `mob_<id>` test for every mob with a spawn egg, plus the
giant and the illusioner. Each mob gets a glass pen sized from
`assets/entities.json` and a check for a behaviour vanilla is sure to show:

- falls and lands (`y=1.0`), or just exists (flying and boss mobs, `NoAI`);
- breeds (`InLove`), the baby is the one without the test tag;
- converts: lightning (pig, villager, creeper), Nether mobs in the Overworld,
  zombie/husk in water, skeleton in powder snow, tadpole growing up;
- sheared by a dispenser (sheep, mooshroom, bogged, snow golem);
- burns in daylight (a marker armor stand stays, the mob is gone);
- kills a target (golem, zoglin, raiders, guardian, frog, wolf, cat);
- fish and squid die out of water, slimes split, enderman leaves water,
  the evoker summons vexes, the copper golem is built from blocks.

The selectors use `positioned` + `dx/dy/dz` boxes inside the pen so tests on
the grid never see each other's mobs.

## Run locally

Vanilla (needs JDK 25 and the 26.3 `server.jar`):

```sh
mkdir -p /tmp/parity/packs && cp -r assets/tests/datapacks/minehouse-parity /tmp/parity/packs/
cd /tmp/parity && java -cp server.jar -DbundlerMainClass=net.minecraft.gametest.Main \
  net.minecraft.bundler.Main --packs packs --tests 'minehouse:*' --report vanilla.xml
```

Pumpkin:

```sh
cargo run -p pumpkin-tester -- --parity parity-pumpkin.json
python3 tools/minehouse-parity/compare.py /tmp/parity/vanilla.xml parity-pumpkin.json
```
