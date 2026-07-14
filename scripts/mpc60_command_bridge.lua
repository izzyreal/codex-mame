local actions = dofile("/Users/izmar/git/codex-mame/scripts/lib/mpc_actions.lua")

local bridge_dir = os.getenv("MPC_BRIDGE_DIR")
if bridge_dir == nil or bridge_dir == "" then
    error("MPC_BRIDGE_DIR is required")
end

local command_path = bridge_dir .. "/command.txt"
local response_path = bridge_dir .. "/response.txt"
local ready_path = bridge_dir .. "/ready.txt"
local analog_dial_value = 0

local function find_field(field_name)
    for _, port in pairs(manager.machine.ioport.ports) do
        local field = port.fields[field_name]
        if field then
            return field
        end
    end
    return nil
end

local function turn_mpc60_dial(delta)
    local field = find_field("Dial")
    if field == nil then
        error("field not found: Dial")
    end
    local step = delta < 0 and -1 or 1
    for _ = 1, math.abs(delta) do
        analog_dial_value = (analog_dial_value + step) % 256
        field:set_value(analog_dial_value)
        actions.wait_frames(4)
    end
end

local function write_file(path, text)
    local file, err = io.open(path, "w")
    if not file then
        error("could not open " .. path .. ": " .. tostring(err))
    end
    file:write(text)
    file:close()
end

local function read_file(path)
    local file = io.open(path, "r")
    if not file then
        return nil
    end
    local text = file:read("*a")
    file:close()
    return text
end

local function split_command(line)
    local first = string.find(line, "|", 1, true)
    if first == nil then
        return line, "", ""
    end
    local second = string.find(line, "|", first + 1, true)
    if second == nil then
        return string.sub(line, 1, first - 1), string.sub(line, first + 1), ""
    end
    return string.sub(line, 1, first - 1),
        string.sub(line, first + 1, second - 1),
        string.sub(line, second + 1)
end

local function execute(command, arg)
    if command == "tap" then
        actions.tap(arg, 6, 6)
    elseif command == "dial" then
        local delta = tonumber(arg)
        local ok, err = pcall(actions.turn_dial, delta, 4)
        if not ok then
            turn_mpc60_dial(delta)
        end
    elseif command == "snap" then
        actions.snapshot(arg)
    elseif command == "wait_stable" then
        actions.wait_for_stable(2, tonumber(arg) or 20, 40)
    elseif command == "exit" then
        -- The caller needs an acknowledgement before MAME starts shutting
        -- down; otherwise the bridge client can time out while MAME exits.
    else
        error("unknown command: " .. tostring(command))
    end
end

write_file(ready_path, "ready\n")

local last_id = ""
while true do
    actions.wait_frames(2)
    local line = read_file(command_path)
    if line ~= nil then
        line = string.gsub(line, "[\r\n]+$", "")
        local id, command, arg = split_command(line)
        if id ~= nil and id ~= "" and id ~= last_id then
            last_id = id
            local ok, err = pcall(execute, command, arg)
            if ok then
                write_file(response_path, id .. "|ok\n")
            else
                write_file(response_path, id .. "|error|" .. tostring(err) .. "\n")
            end
            if command == "exit" then
                manager.machine:exit()
                break
            end
        end
    end
end
