local actions = dofile("/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua")
local out_dir = "/tmp/codex-mame-smoke"

os.execute("mkdir -p " .. out_dir)

actions.wait_for_sequencer_ready(240, 40)
actions.snapshot(out_dir .. "/00-ready.png")

actions.tap_and_wait_for_change("3 / Load", 2, 12, 20, 40)
actions.snapshot(out_dir .. "/01-load-screen.png")

actions.tap_and_wait_for_change("Main Screen", 2, 12, 20, 40)
actions.wait_for_sequencer_ready(40, 40)
actions.snapshot(out_dir .. "/02-main-screen.png")

actions.tap_and_wait_for_change("6 / Program", 2, 12, 20, 40)
actions.snapshot(out_dir .. "/03-program-screen.png")

actions.tap_and_wait_for_change("Main Screen", 2, 12, 20, 40)
actions.wait_for_sequencer_ready(40, 40)
actions.snapshot(out_dir .. "/04-main-screen-return.png")

manager.machine:exit()
