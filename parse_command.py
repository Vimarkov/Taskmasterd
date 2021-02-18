import os

def parse_command(cmd):
    i = 0
    if cmd == '':
        return 0, 0
    args = cmd.split()

    cmd = args[0] 
    #print(cmd)
    #print(args)

    if cmd[0:8] == '/usr/bin': 
        cmd = cmd[9:len(cmd)]
    if cmd[0:4] == '/bin': 
        cmd = cmd[5:len(cmd)]
    if cmd[0:14] == '/usr/local/bin': 
        cmd = cmd[15:len(cmd)]
    if cmd[0:5] == '/sbin': 
        cmd = cmd[6:len(cmd)]
    if cmd[0:9] == '/usr/sbin': 
        cmd = cmd[10:len(cmd)]

    binary = os.listdir('/usr/bin')
    binary1 = os.listdir('/bin')
    binary2 = os.listdir('/usr/local/bin')
    binary3 = os.listdir('/sbin')
    binary4 = os.listdir('/usr/sbin')

    for file in binary:
        if cmd == file:
            return '/usr/bin/' + cmd, args
    for file in binary1:
        if cmd == file:
            return '/bin/' + cmd, args
    for file in binary2:
        if cmd == file:
            return '/usr/local/bin/' + cmd, args
    for file in binary3:
        if cmd == file:
            return '/sbin/' + cmd, args
    for file in binary4:
        if cmd == file:
            return '/usr/sbin/' + cmd, args
    return 0, 0