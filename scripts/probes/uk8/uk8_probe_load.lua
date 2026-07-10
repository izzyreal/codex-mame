local actions = dofile("/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua")
local out_dir = "/tmp/uk8-probe"

os.execute("mkdir -p " .. out_dir)

actions.wait_for_sequencer_ready(240, 40)
actions.snapshot(out_dir .. "/00-ready.png")

actions.set("Shift", 1)
actions.tap_and_wait_for_change("3 / Load", 2, 12, 20, 40)
actions.clear("Shift")
actions.snapshot(out_dir .. "/01-load-screen.png")

manager.machine:exit()
