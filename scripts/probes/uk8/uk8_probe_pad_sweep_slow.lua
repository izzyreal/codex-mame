local actions = dofile("/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua")
local out_dir = "/tmp/uk8-pad-sweep-slow"

os.execute("mkdir -p " .. out_dir)

actions.wait_for_sequencer_ready(240, 40)

actions.set("Shift", 1)
actions.tap_and_wait_for_change("3 / Load", 2, 12, 20, 40)
actions.clear("Shift")

actions.tap_and_wait_for_change("Soft Key 6", 2, 12, 20, 40)
actions.tap_and_wait_for_change("Soft Key 3", 2, 12, 20, 40)
actions.snapshot(out_dir .. "/00-initial.png")

for i = 1, 4 do
    actions.turn_dial(1, 10)
    actions.snapshot(string.format("%s/%02d-plus-%02d.png", out_dir, i, i))
end

manager.machine:exit()
