local out = "/tmp/mpc2000xl-ports.txt"

if not mpcprobe then
    emu.print_error("autoboot: mpcprobe global is not available")
    manager.machine:exit()
    return
end

mpcprobe.write_port_dump(out)
manager.machine:exit()
