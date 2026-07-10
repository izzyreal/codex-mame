local actions = dofile("/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua")
local out_dir = "/tmp/uk8-pad-sweep"

os.execute("mkdir -p " .. out_dir)

actions.wait_for_sequencer_ready(240, 40)

actions.set("Shift", 1)
actions.tap_and_wait_for_change("3 / Load", 2, 12, 20, 40)
actions.clear("Shift")
actions.snapshot(out_dir .. "/01-load-screen.png")

actions.tap_and_wait_for_change("Soft Key 6", 2, 12, 20, 40)
actions.snapshot(out_dir .. "/02-load-a-set.png")

actions.tap_and_wait_for_change("Soft Key 3", 2, 12, 20, 40)
actions.snapshot(out_dir .. "/03-initial.png")

for i = 1, 10 do
    actions.turn_dial(1)
    actions.snapshot(string.format("%s/%02d-plus-%02d.png", out_dir, i + 3, i))
end

actions.turn_dial(8)
actions.snapshot(out_dir .. "/14-plus-18-total.png")

manager.machine:exit()
