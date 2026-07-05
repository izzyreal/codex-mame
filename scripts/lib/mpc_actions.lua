local actions = {}
local DEFAULT_POLL_FRAMES = 40
local DEFAULT_CHANGE_POLL_FRAMES = 4
local SEQUENCER_READY_SIG = "66ace03b"
local DEFAULT_DIAL_SETTLE_FRAMES = 2

local function resolve_field(field_name)
    if not mpcprobe then
        error("mpcprobe is not available")
    end
    local port_tag, field = nil, nil
    for candidate_port_tag, port in pairs(manager.machine.ioport.ports) do
        local candidate = port.fields[field_name]
        if candidate then
            port_tag = candidate_port_tag
            field = candidate
            break
        end
    end
    if not field then
        error("field not found: " .. field_name)
    end
    return port_tag, field
end

function actions.wait_frames(frame_count)
    for _ = 1, frame_count do
        emu.wait_next_frame()
    end
end

function actions.tap(field_name, hold_frames, settle_frames)
    hold_frames = hold_frames or 2
    settle_frames = settle_frames or 2
    local _, field = resolve_field(field_name)
    field:set_value(1)
    actions.wait_frames(hold_frames)
    field:clear_value()
    actions.wait_frames(settle_frames)
end

function actions.tap_and_wait_for_change(field_name, hold_frames, settle_frames, max_polls, poll_frames)
    local baseline = actions.screen_signature()
    actions.tap(field_name, hold_frames, settle_frames)
    return actions.wait_for_change(max_polls, poll_frames, baseline)
end

function actions.set(field_name, value)
    local _, field = resolve_field(field_name)
    field:set_value(value)
end

function actions.clear(field_name)
    local _, field = resolve_field(field_name)
    field:clear_value()
end

function actions.snapshot(path)
    local screen = manager.machine.screens[":screen"]
    if not screen then
        error("no :screen device")
    end
    local err = screen:snapshot(path)
    if err then
        error("snapshot failed: " .. tostring(err))
    end
end

function actions.screen_signature()
    local screen = manager.machine.screens[":screen"]
    if not screen then
        error("no :screen device")
    end
    local pixels = screen:pixels()
    local hash = 2166136261
    for i = 1, #pixels do
        hash = (hash ~ pixels:byte(i)) & 0xffffffff
        hash = (hash * 16777619) & 0xffffffff
    end
    return string.format("%08x", hash)
end

function actions.wait_for_change(max_polls, poll_frames, baseline)
    max_polls = max_polls or 20
    poll_frames = poll_frames or DEFAULT_CHANGE_POLL_FRAMES
    baseline = baseline or actions.screen_signature()
    for _ = 1, max_polls do
        actions.wait_frames(poll_frames)
        local current = actions.screen_signature()
        if current ~= baseline then
            return current
        end
    end
    error("wait_for_change timed out")
end

function actions.wait_for_stable(stable_polls, max_polls, poll_frames)
    stable_polls = stable_polls or 2
    max_polls = max_polls or 20
    poll_frames = poll_frames or DEFAULT_POLL_FRAMES
    local last = actions.screen_signature()
    local stable_count = 1
    for _ = 1, max_polls do
        actions.wait_frames(poll_frames)
        local current = actions.screen_signature()
        if current == last then
            stable_count = stable_count + 1
            if stable_count >= stable_polls then
                return current
            end
        else
            last = current
            stable_count = 1
        end
    end
    error("wait_for_stable timed out")
end

function actions.wait_for_screen(signature, quiet_frames, max_polls, poll_frames)
    quiet_frames = quiet_frames or DEFAULT_POLL_FRAMES
    max_polls = max_polls or 120
    poll_frames = poll_frames or DEFAULT_POLL_FRAMES
    for _ = 1, max_polls do
        actions.wait_frames(poll_frames)
        local current = actions.screen_signature()
        if current == signature then
            local changed = false
            for _ = 1, quiet_frames do
                actions.wait_frames(1)
                if actions.screen_signature() ~= signature then
                    changed = true
                    break
                end
            end
            if not changed then
                return current
            end
        end
    end
    error("wait_for_screen timed out for signature " .. tostring(signature))
end

function actions.wait_for_sequencer_ready(max_polls, poll_frames)
    return actions.wait_for_screen(
        SEQUENCER_READY_SIG,
        DEFAULT_POLL_FRAMES,
        max_polls or 120,
        poll_frames or DEFAULT_POLL_FRAMES
    )
end

function actions.turn_dial(delta, settle_frames)
    settle_frames = settle_frames or 2
    local field_name = delta < 0 and "Data Wheel -1" or "Data Wheel +1"
    local _, field = resolve_field(field_name)
    for _ = 1, math.abs(delta) do
        field:set_value(1)
        actions.wait_frames(1)
        field:clear_value()
        actions.wait_frames(settle_frames)
    end
end

function actions.set_sq(current_sq_number, target_sq_number, settle_frames)
    if current_sq_number == nil or target_sq_number == nil then
        error("current_sq_number and target_sq_number are required")
    end
    return actions.turn_dial(target_sq_number - current_sq_number, settle_frames or DEFAULT_DIAL_SETTLE_FRAMES)
end

function actions.nudge_dial_positive(steps, settle_frames)
    steps = steps or 1
    return actions.turn_dial(steps, settle_frames or DEFAULT_DIAL_SETTLE_FRAMES)
end

function actions.nudge_dial_negative(steps, settle_frames)
    steps = steps or 1
    return actions.turn_dial(-steps, settle_frames or DEFAULT_DIAL_SETTLE_FRAMES)
end

return actions
