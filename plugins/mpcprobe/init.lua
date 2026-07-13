local exports = {
    name = "mpcprobe",
    version = "0.0.1",
    description = "Probe Akai MPC inputs and screen state",
    license = "BSD-3-Clause",
    author = { name = "Codex" }
}

local mpcprobe = exports
local reset_subscription
local frame_subscription
local queued_actions = {}
local active_action = nil
local action_state = nil
local DEFAULT_POLL_FRAMES = 40
local DEFAULT_CHANGE_POLL_FRAMES = 4
local SEQUENCER_READY_SIG = "66ace03b"
local analog_field_state = {}

local function current_screen_signature()
    local screen = manager.machine.screens[":screen"]
    if not screen then
        return nil
    end
    local pixels = screen:pixels()
    local hash = 2166136261
    for i = 1, #pixels do
        hash = (hash ~ pixels:byte(i)) & 0xffffffff
        hash = (hash * 16777619) & 0xffffffff
    end
    return string.format("%08x", hash)
end

local function bool_to_int(value)
    if value then
        return 1
    end
    return 0
end

local function field_press_value(field)
    local mask = tonumber(field.mask)
    if mask and mask ~= 0 then
        return mask
    end
    local def_value = tonumber(field.defvalue)
    if def_value and def_value ~= 0 then
        return def_value
    end
    return 1
end

local function release_field(field)
    if field.is_analog then
        field:clear_value()
        return
    end
    field:set_value(0)
end

local function find_field_by_name(field_name)
    for port_tag, port in pairs(manager.machine.ioport.ports) do
        local field = port.fields[field_name]
        if field then
            return port_tag, field
        end
    end
    return nil, nil
end

local function clamp(value, min_value, max_value)
    if value < min_value then
        return min_value
    end
    if value > max_value then
        return max_value
    end
    return value
end

local function next_analog_value(field_name, field, delta)
    local min_value = tonumber(field.minvalue) or 0
    local max_value = tonumber(field.maxvalue) or 255
    local def_value = tonumber(field.defvalue) or min_value
    local current = analog_field_state[field_name]
    if current == nil then
        current = def_value
    end

    local span = (max_value - min_value) + 1
    if span <= 0 then
        local next_value = clamp(current + delta, min_value, max_value)
        analog_field_state[field_name] = next_value
        return next_value
    end

    local offset = (current - min_value + delta) % span
    local next_value = min_value + offset
    analog_field_state[field_name] = next_value
    return next_value
end

local function dump_ports()
    emu.print_info("mpcprobe: dumping I/O ports")
    for port_tag, port in pairs(manager.machine.ioport.ports) do
        emu.print_info(string.format("port %s active=0x%08x", port_tag, port.active))
        for field_name, field in pairs(port.fields) do
            emu.print_info(string.format(
                "  field name=%s mask=0x%08x player=%d enabled=%d analog=%d type_class=%s",
                field_name,
                field.mask,
                field.player,
                bool_to_int(field.enabled),
                bool_to_int(field.is_analog),
                field.type_class
            ))
        end
    end
end

local function reset_queue()
    queued_actions = {}
    active_action = nil
    action_state = nil
end

local function write_port_dump(path)
    local file, err = io.open(path, "w")
    if not file then
        emu.print_error("mpcprobe: could not open " .. path .. ": " .. tostring(err))
        return
    end
    for port_tag, port in pairs(manager.machine.ioport.ports) do
        file:write(string.format("port %s active=0x%08x\n", port_tag, port.active))
        for field_name, field in pairs(port.fields) do
            file:write(string.format(
                "  field name=%s mask=0x%08x player=%d enabled=%d analog=%d type_class=%s\n",
                field_name,
                field.mask,
                field.player,
                bool_to_int(field.enabled),
                bool_to_int(field.is_analog),
                field.type_class
            ))
        end
    end
    file:close()
    emu.print_info("mpcprobe: wrote port dump to " .. path)
end

local function list_fields(pattern)
    pattern = pattern and string.lower(pattern) or nil
    for port_tag, port in pairs(manager.machine.ioport.ports) do
        for field_name, field in pairs(port.fields) do
            local haystack = string.lower(field_name)
            if (not pattern) or string.find(haystack, pattern, 1, true) then
                emu.print_info(string.format(
                    "%s | %s | mask=0x%08x analog=%d min=%s max=%s def=%s",
                    port_tag,
                    field_name,
                    field.mask,
                    bool_to_int(field.is_analog),
                    tostring(field.minvalue),
                    tostring(field.maxvalue),
                    tostring(field.defvalue)
                ))
            end
        end
    end
end

local function set_field_value(field_name, value)
    local port_tag, field = find_field_by_name(field_name)
    if not field then
        emu.print_error("mpcprobe: field not found: " .. field_name)
        return
    end
    field:set_value(value)
    emu.print_info(string.format("mpcprobe: set %s on %s to %s", field_name, port_tag, tostring(value)))
end

local function clear_field_value(field_name)
    local port_tag, field = find_field_by_name(field_name)
    if not field then
        emu.print_error("mpcprobe: field not found: " .. field_name)
        return
    end
    release_field(field)
    emu.print_info(string.format("mpcprobe: cleared %s on %s", field_name, port_tag))
end

local function snapshot_to_path(path)
    local screen = manager.machine.screens[":screen"]
    if not screen then
        emu.print_error("mpcprobe: no :screen device")
        return false
    end
    local pixels, width, height = screen:pixels()
    local err = screen:snapshot(path)
    if err then
        emu.print_error("mpcprobe: snapshot failed: " .. tostring(err))
        return false
    end
    emu.print_info(string.format(
        "mpcprobe: snapshot=%s width=%d height=%d bytes=%d",
        path,
        width,
        height,
        #pixels
    ))
    return true
end

local function press_field(field_name, frames)
    local port_tag, field = find_field_by_name(field_name)
    if not field then
        emu.print_error("mpcprobe: field not found: " .. field_name)
        return
    end
    frames = frames or 1
    field:set_value(field_press_value(field))
    local remaining = frames
    local subscription
    subscription = emu.add_machine_frame_notifier(function()
        remaining = remaining - 1
        if remaining <= 0 then
            release_field(field)
            if subscription then
                subscription:unsubscribe()
            end
        end
    end)
    emu.print_info(string.format("mpcprobe: pressed %s on %s for %d frame(s)", field_name, port_tag, frames))
end

local function dump_screen(prefix)
    local path = prefix or "mpcprobe_screen.png"
    snapshot_to_path(path)
end

local function run_script(path)
    if not path or path == "" then
        emu.print_error("mpcprobe: run_script requires a path")
        return false
    end
    local chunk, err = loadfile(path)
    if not chunk then
        emu.print_error("mpcprobe: could not load script " .. path .. ": " .. tostring(err))
        return false
    end
    emu.print_info("mpcprobe: running script " .. path)
    local ok, run_err = pcall(chunk)
    if not ok then
        emu.print_error("mpcprobe: script failed: " .. tostring(run_err))
        return false
    end
    return true
end

local function enqueue_action(action)
    queued_actions[#queued_actions + 1] = action
    emu.print_info(string.format("mpcprobe: queued %s", action.kind))
end

local function queue_tap(field_name, hold_frames, settle_frames)
    enqueue_action({
        kind = "tap",
        field_name = field_name,
        hold_frames = hold_frames or 2,
        settle_frames = settle_frames or 2
    })
end

local function queue_wait(frame_count)
    enqueue_action({
        kind = "wait",
        frame_count = frame_count or 1
    })
end

local function queue_snapshot(path)
    enqueue_action({
        kind = "snapshot",
        path = path or "mpcprobe_screen.png"
    })
end

local function queue_wait_change(max_polls, poll_frames)
    enqueue_action({
        kind = "wait_change",
        baseline = current_screen_signature(),
        max_polls = max_polls or 20,
        poll_frames = poll_frames or DEFAULT_CHANGE_POLL_FRAMES
    })
end

local function queue_wait_stable(stable_polls, max_polls, poll_frames)
    enqueue_action({
        kind = "wait_stable",
        stable_polls = stable_polls or 2,
        max_polls = max_polls or 20,
        poll_frames = poll_frames or DEFAULT_POLL_FRAMES
    })
end

local function queue_wait_screen(signature, quiet_frames, max_polls, poll_frames)
    enqueue_action({
        kind = "wait_screen",
        signature = signature,
        quiet_frames = quiet_frames or DEFAULT_POLL_FRAMES,
        max_polls = max_polls or 120,
        poll_frames = poll_frames or DEFAULT_POLL_FRAMES
    })
end

local function queue_wait_sequencer_ready(max_polls, poll_frames)
    queue_wait_screen(
        SEQUENCER_READY_SIG,
        DEFAULT_POLL_FRAMES,
        max_polls or 120,
        poll_frames or DEFAULT_POLL_FRAMES
    )
end

local function queue_tap_wait_change(field_name, hold_frames, settle_frames, max_polls, poll_frames)
    local baseline = current_screen_signature()
    queue_tap(field_name, hold_frames, settle_frames)
    enqueue_action({
        kind = "wait_change",
        baseline = baseline,
        max_polls = max_polls or 20,
        poll_frames = poll_frames or DEFAULT_CHANGE_POLL_FRAMES
    })
end

local function queue_set(field_name, value)
    enqueue_action({
        kind = "set",
        field_name = field_name,
        value = value
    })
end

local function queue_clear_field(field_name)
    enqueue_action({
        kind = "clear",
        field_name = field_name
    })
end

local function queue_dial(delta, settle_frames)
    enqueue_action({
        kind = "dial",
        delta = delta or 0,
        settle_frames = settle_frames or 2
    })
end

local function queue_combo(modifier_field_name, field_name, hold_frames, settle_frames)
    local _, modifier_field = find_field_by_name(modifier_field_name)
    if not modifier_field then
        emu.print_error("mpcprobe: field not found: " .. modifier_field_name)
        return
    end
    queue_set(modifier_field_name, field_press_value(modifier_field))
    queue_tap(field_name, hold_frames, settle_frames)
    queue_clear_field(modifier_field_name)
end

local function queue_clear()
    reset_queue()
    emu.print_info("mpcprobe: cleared queued actions")
end

local function queue_status()
    emu.print_info(string.format(
        "mpcprobe: queue=%d active=%s",
        #queued_actions,
        active_action and active_action.kind or "none"
    ))
end

local function process_tap(action)
    if not action_state then
        local _, field = find_field_by_name(action.field_name)
        if not field then
            emu.print_error("mpcprobe: field not found: " .. action.field_name)
            return true
        end
        field:set_value(field_press_value(field))
        action_state = {
            phase = "hold",
            remaining = action.hold_frames,
            field = field,
            just_started = true
        }
        return false
    end

    if action_state.just_started then
        action_state.just_started = false
        return false
    end

    action_state.remaining = action_state.remaining - 1
    if action_state.remaining > 0 then
        return false
    end

    if action_state.phase == "hold" then
        release_field(action_state.field)
        action_state.phase = "settle"
        action_state.remaining = action.settle_frames
        return action_state.remaining <= 0
    end

    return true
end

local function process_wait(action)
    if not action_state then
        action_state = {
            remaining = action.frame_count,
            just_started = true
        }
        return false
    end

    if action_state.just_started then
        action_state.just_started = false
        return false
    end

    action_state.remaining = action_state.remaining - 1
    return action_state.remaining <= 0
end

local function process_snapshot(action)
    snapshot_to_path(action.path)
    return true
end

local function process_wait_change(action)
    if not action_state then
        action_state = {
            baseline = action.baseline,
            poll_frames = action.poll_frames,
            frames_until_poll = action.poll_frames,
            polls_left = action.max_polls
        }
        return false
    end

    action_state.frames_until_poll = action_state.frames_until_poll - 1
    if action_state.frames_until_poll > 0 then
        return false
    end

    local current = current_screen_signature()
    if current ~= action_state.baseline then
        emu.print_info(string.format(
            "mpcprobe: lcd changed %s -> %s",
            tostring(action_state.baseline),
            tostring(current)
        ))
        return true
    end

    action_state.polls_left = action_state.polls_left - 1
    if action_state.polls_left <= 0 then
        emu.print_error("mpcprobe: wait_change timed out")
        return true
    end

    action_state.frames_until_poll = action.poll_frames
    return false
end

local function process_wait_stable(action)
    if not action_state then
        local current = current_screen_signature()
        action_state = {
            last = current,
            stable_count = 1,
            poll_frames = action.poll_frames,
            frames_until_poll = action.poll_frames,
            polls_left = action.max_polls
        }
        return false
    end

    action_state.frames_until_poll = action_state.frames_until_poll - 1
    if action_state.frames_until_poll > 0 then
        return false
    end

    local current = current_screen_signature()
    if current == action_state.last then
        action_state.stable_count = action_state.stable_count + 1
        if action_state.stable_count >= action.stable_polls then
            emu.print_info(string.format(
                "mpcprobe: lcd stable at %s for %d poll(s)",
                tostring(current),
                action_state.stable_count
            ))
            return true
        end
    else
        action_state.last = current
        action_state.stable_count = 1
    end

    action_state.polls_left = action_state.polls_left - 1
    if action_state.polls_left <= 0 then
        emu.print_error("mpcprobe: wait_stable timed out")
        return true
    end

    action_state.frames_until_poll = action.poll_frames
    return false
end

local function process_wait_screen(action)
    if not action_state then
        action_state = {
            phase = "scan",
            poll_frames = action.poll_frames,
            frames_until_poll = action.poll_frames,
            polls_left = action.max_polls,
            quiet_left = 0
        }
        return false
    end

    if action_state.phase == "scan" then
        action_state.frames_until_poll = action_state.frames_until_poll - 1
        if action_state.frames_until_poll > 0 then
            return false
        end

        local current = current_screen_signature()
        if current == action.signature then
            action_state.phase = "verify"
            action_state.quiet_left = action.quiet_frames
            return false
        end

        action_state.polls_left = action_state.polls_left - 1
        if action_state.polls_left <= 0 then
            emu.print_error("mpcprobe: wait_screen timed out for signature " .. tostring(action.signature))
            return true
        end

        action_state.frames_until_poll = action.poll_frames
        return false
    end

    local current = current_screen_signature()
    if current ~= action.signature then
        action_state.phase = "scan"
        action_state.frames_until_poll = action.poll_frames
        return false
    end

    action_state.quiet_left = action_state.quiet_left - 1
    if action_state.quiet_left <= 0 then
        emu.print_info(string.format(
            "mpcprobe: lcd reached %s and stayed unchanged for %d frame(s)",
            tostring(current),
            action.quiet_frames
        ))
        return true
    end

    return false
end

local function process_set(action)
    set_field_value(action.field_name, action.value)
    return true
end

local function process_clear(action)
    clear_field_value(action.field_name)
    return true
end

local function process_dial(action)
    if not action_state then
        local remaining_steps = math.abs(action.delta)
        if remaining_steps == 0 then
            return true
        end

        local digital_field_name = action.delta < 0 and "Data Wheel -1" or "Data Wheel +1"
        local _, digital_field = find_field_by_name(digital_field_name)
        if digital_field then
            action_state = {
                mode = "digital",
                phase = "pulse",
                remaining = 1,
                remaining_steps = remaining_steps,
                settle_frames = action.settle_frames,
                field = digital_field,
                just_started = true
            }
            digital_field:set_value(field_press_value(digital_field))
            return false
        end

        local analog_field_name, analog_field = find_field_by_name("Dial")
        if not analog_field or not analog_field.is_analog then
            emu.print_error("mpcprobe: no supported dial input found")
            return true
        end

        local analog_settle_frames = math.max(action.settle_frames, 4)
        local analog_step = action.delta < 0 and -1 or 1
        local next_value = next_analog_value("Dial", analog_field, analog_step)

        action_state = {
            mode = "analog",
            remaining = analog_settle_frames,
            remaining_steps = remaining_steps,
            settle_frames = analog_settle_frames,
            field = analog_field,
            field_name = analog_field_name,
            step = analog_step,
            just_started = true
        }
        analog_field:set_value(next_value)
        emu.print_info(string.format(
            "mpcprobe: set %s to %d for dial step",
            analog_field_name,
            next_value
        ))
    end

    if action_state.just_started then
        action_state.just_started = false
        return false
    end

    if action_state.mode == "analog" then
        action_state.remaining = action_state.remaining - 1
        if action_state.remaining > 0 then
            return false
        end

        action_state.remaining_steps = action_state.remaining_steps - 1
        if action_state.remaining_steps <= 0 then
            return true
        end

        local next_value = next_analog_value("Dial", action_state.field, action_state.step)
        action_state.remaining = action_state.settle_frames
        action_state.just_started = true
        action_state.field:set_value(next_value)
        emu.print_info(string.format(
            "mpcprobe: set %s to %d for dial step",
            action_state.field_name,
            next_value
        ))
        return false
    end

    action_state.remaining = action_state.remaining - 1
        if action_state.remaining > 0 then
            return false
        end

        if action_state.phase == "pulse" then
            release_field(action_state.field)
            action_state.phase = "settle"
            action_state.remaining = action_state.settle_frames
            return false
        end

    action_state.remaining_steps = action_state.remaining_steps - 1
    if action_state.remaining_steps <= 0 then
        return true
    end

    action_state.phase = "pulse"
    action_state.remaining = 1
    action_state.just_started = true
    action_state.field:set_value(1)
    return false
end

local function process_queue()
    if not active_action then
        if #queued_actions == 0 then
            return
        end
        active_action = table.remove(queued_actions, 1)
        action_state = nil
        emu.print_info(string.format("mpcprobe: running %s", active_action.kind))
    end

    local finished = false
    if active_action.kind == "tap" then
        finished = process_tap(active_action)
    elseif active_action.kind == "wait" then
        finished = process_wait(active_action)
    elseif active_action.kind == "snapshot" then
        finished = process_snapshot(active_action)
    elseif active_action.kind == "wait_change" then
        finished = process_wait_change(active_action)
    elseif active_action.kind == "wait_stable" then
        finished = process_wait_stable(active_action)
    elseif active_action.kind == "wait_screen" then
        finished = process_wait_screen(active_action)
    elseif active_action.kind == "set" then
        finished = process_set(active_action)
    elseif active_action.kind == "clear" then
        finished = process_clear(active_action)
    elseif active_action.kind == "dial" then
        finished = process_dial(active_action)
    else
        emu.print_error("mpcprobe: unknown action kind: " .. tostring(active_action.kind))
        finished = true
    end

    if finished then
        active_action = nil
        action_state = nil
    end
end

function mpcprobe.startplugin()
    frame_subscription = emu.add_machine_frame_notifier(process_queue)
    reset_subscription = emu.add_machine_reset_notifier(function()
        reset_queue()
        _G.mpcprobe = {
            dump_ports = dump_ports,
            write_port_dump = write_port_dump,
            list_fields = list_fields,
            screen_sig = current_screen_signature,
            set = set_field_value,
            clear = clear_field_value,
            press = press_field,
            dump_screen = dump_screen,
            tap = queue_tap,
            tap_wait_change = queue_tap_wait_change,
            combo = queue_combo,
            wait = queue_wait,
            wait_change = queue_wait_change,
            wait_stable = queue_wait_stable,
            wait_screen = queue_wait_screen,
            wait_sequencer_ready = queue_wait_sequencer_ready,
            snap = queue_snapshot,
            queue_set = queue_set,
            queue_clear_field = queue_clear_field,
            dial = queue_dial,
            queue_clear = queue_clear,
            queue_status = queue_status,
            run_script = run_script
        }
        emu.print_info("mpcprobe: ready")
        emu.print_info("mpcprobe: use mpcprobe.dump_ports(), mpcprobe.combo(\"Shift\", \"3 / Load\"), mpcprobe.tap(\"Window\"), mpcprobe.wait_change(), mpcprobe.wait_stable(), mpcprobe.wait_sequencer_ready(), mpcprobe.dial(3), mpcprobe.snap(\"lcd.png\"), mpcprobe.queue_status(), mpcprobe.run_script(\"/path/to/script.lua\")")
    end)
end

return exports
