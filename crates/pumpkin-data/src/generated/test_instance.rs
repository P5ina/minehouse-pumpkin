/* This file is generated. Do not edit manually. */
#[allow(clippy::too_many_lines)]
#[allow(clippy::match_same_arms)]
#[allow(clippy::missing_const_for_fn)]
#[allow(clippy::match_single_binding)]
#[must_use]
pub fn get_test_instance_json(path: &str) -> Option<&'static str> {
    match path {
        "minecraft:always_pass" | "always_pass" => Some(include_str!(
            "../../../../assets/datapack/data/minecraft/test_instance/always_pass.json"
        )),
        "minehouse:command_execute_if_items" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/command_execute_if_items.json"
        )),
        "minehouse:comparator_reads_chest" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/comparator_reads_chest.json"
        )),
        "minehouse:dispenser_water_flows_7" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/dispenser_water_flows_7.json"
        )),
        "minehouse:furnace_smelts_iron" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/furnace_smelts_iron.json"
        )),
        "minehouse:hopper_fills_chest" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/hopper_fills_chest.json"
        )),
        "minehouse:hopper_picks_up_item" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/hopper_picks_up_item.json"
        )),
        "minehouse:iron_golem_from_blocks" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/iron_golem_from_blocks.json"
        )),
        "minehouse:nether_portal_lights" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/nether_portal_lights.json"
        )),
        "minehouse:piston_pushes_block" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/piston_pushes_block.json"
        )),
        "minehouse:redstone_wire_15" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/redstone_wire_15.json"
        )),
        "minehouse:snow_golem_from_blocks" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/snow_golem_from_blocks.json"
        )),
        "minehouse:tnt_breaks_stone" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/tnt_breaks_stone.json"
        )),
        "minehouse:water_meets_lava_obsidian" => Some(include_str!(
            "../../../../assets/tests/datapacks/minehouse-parity/data/minehouse/test_instance/water_meets_lava_obsidian.json"
        )),
        "pumpkin:creeper_should_run_from_cat" => Some(include_str!(
            "../../../../assets/tests/datapacks/pumpkin-unit-test/data/pumpkin/test_instance/creeper_should_run_from_cat.json"
        )),
        "pumpkin:summon_command_regression" => Some(include_str!(
            "../../../../assets/tests/datapacks/pumpkin-unit-test/data/pumpkin/test_instance/summon_command_regression.json"
        )),
        _ => None,
    }
}
#[must_use]
#[allow(clippy::too_many_lines, clippy::large_stack_arrays)]
pub const fn all_test_instance_names() -> &'static [&'static str] {
    &[
        "minecraft:always_pass",
        "minehouse:command_execute_if_items",
        "minehouse:comparator_reads_chest",
        "minehouse:dispenser_water_flows_7",
        "minehouse:furnace_smelts_iron",
        "minehouse:hopper_fills_chest",
        "minehouse:hopper_picks_up_item",
        "minehouse:iron_golem_from_blocks",
        "minehouse:nether_portal_lights",
        "minehouse:piston_pushes_block",
        "minehouse:redstone_wire_15",
        "minehouse:snow_golem_from_blocks",
        "minehouse:tnt_breaks_stone",
        "minehouse:water_meets_lava_obsidian",
        "pumpkin:creeper_should_run_from_cat",
        "pumpkin:summon_command_regression",
    ]
}
