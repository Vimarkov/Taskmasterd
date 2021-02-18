import sys
import os

def find_program(program, name):
    for data in program:
        if data == name:
            return 1
    return 0

def shutdown(pid, status):  
    if status:
        for name in status:
            try:
                os.kill(int(status[name]['pid']), 9)
            except ProcessLookupError:
                pass
    os.kill(pid, 9) 
    sys.exit(1)

def parse_data(data, config):
    action = []

    if data == 'start':
        print('[-] Error: start requires a process name\nstart <name>		Start a process')
        print('start <gname>:*		Start all processes in a group')
        print('start <name> <name>	Start multiple processes or groups\nstart all		Start all processes') 
        return 1 
    if data[0:6] == 'start ':
        return data
    if data == 'stop':
        print('[-] Error: stop requires a process name\nstop <name>		Stop a process')
        print('stop <gname>:*		Stop all processes in a group')
        print('stop <name> <name>	Stop multiple processes or groups\nstop all		Stop all processes') 
        return 1 
    if data[0:5] == 'stop ':
        return data
    if data == 'restart':
        print('Error: restart requires a process name\nrestart <name>		Restart a process')
        print('restart <gname>:*	Restart all processes in a group')
        print('restart <name> <name>	Restart multiple processes or groups\nrestart all		Restart all processes')
        return 1
    if data[0:8] == 'restart ': 
        return(data)
    if data == 'update': 
        return(data)
    if data == 'reread':
        return(data)
    if data == 'status':
        return data 
    if data == 'reload':
        return data 
    if data == 'shutdown':
        return data
    if data == 'help':
        return data    
    return 0

def parse_conf(config, pid, status):
    signalcode = ['TERM', 'HUP', 'INT', 'QUIT', 'KILL', 'USR1', 'USR2']
    check = 0
    for name in config:
        if find_program(config[name], 'stopsignal') == 1:
            if len(config[name]['stopsignal']) > 4:
                print('Error: value {} is not a valid signal name in section {}'.format(config[name]['stopsignal'], name))
                shutdown(pid, status)
            if signalcode.count(config[name]['stopsignal']) == 0:
                print('Error: value {} is not a valid signal name in section {}'.format(config[name]['stopsignal'], name))
                shutdown(pid, status)
        if find_program(config[name], 'environment') == 1:
            value = []
            variable = []
            nb = 1
            var = ''
            check = 0
            for letter in config[name]['environment']:
                if letter == ',':
                    check = 1
            if check == 0:
                print('Error: Unexpected end of key/value pairs in value ' + config[name]['environment'] + ' in section ' + name)
                sys.exit(1)
            check = 0
            env = config[name]['environment'].split(",")
            for data in env:
                for letter in data:
                    if letter == '=':
                        check = 1
                if check == 0:
                    print('Error: Unexpected end of key/value pairs in value ' + config[name]['environment'] + ' in section ' + name)
                    sys.exit(1)
                check = 0
                odd = 0
                for letter in data:
                    if letter == '\"':
                        check = check + 1
                    if check != 0 and check % 2 == 0:
                        odd = 1
                if odd != 1:
                    print('Error: Unexpected end of key/value pairs in value ' + config[name]['environment'] + ' in section ' + name)
                    sys.exit(1)
        if find_program(config[name], 'startsecs') == 1:
            try:
                int(config[name]['startsecs'])
            except ValueError:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['startsecs'], name))
                shutdown(pid, status)
        if find_program(config[name], 'numprocs') == 1:
            try:
                int(config[name]['numprocs'])
            except ValueError:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['numprocs'], name))
                shutdown(pid, status)
        if find_program(config[name], 'stopwaitsecs') == 1:
            try:
                int(config[name]['stopwaitsecs'])
            except ValueError:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['stopwaitsecs'], name))
                shutdown(pid, status)
        if find_program(config[name], 'umask') == 1:
            try:
                int(config[name]['umask'])
            except ValueError:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['umask'], name))
                shutdown(pid, status)
        if find_program(config[name], 'autostart') == 1:
            test = config[name]['autostart'] 
            if test != 'true' and test != 'false':
                print('Error: not a valid boolean value: '' in section {}'. format(name))
                shutdown(pid, status)
        if find_program(config[name], 'startretries') == 1:
            try:
                int(config[name]['startretries'])
            except ValueError:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['startretrties'], name))
                shutdown(pid, status)
        if find_program(config[name], 'exitcodes') == 1:
            try:
                int(config[name]['exitcodes'])
            except ValueError:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['exitcodes'], name))
                shutdown(pid, status)
        if find_program(config[name], 'stopsignal') == 1:
            sign = 0
            if config[name]['stopsignal'] == 'TERM':
                sign = 15
            if config[name]['stopsignal'] == 'HUP':
                sign = 1
            if config[name]['stopsignal'] == 'INT':
                sign = 2
            if config[name]['stopsignal'] == 'QUIT':
                sign = 3
            if config[name]['stopsignal'] == 'KILL':
                sign = 9
            if config[name]['stopsignal'] == 'USR1':
                sign = 10
            if config[name]['stopsignal'] == 'USR2':
                sign = 12
            if sign == 0:
                print('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['stopsignal'], name))
                shutdown(pid, status)

def parse_actions(cmd, config, status):
    action = []
    valid = []
    msg = ''
    check = 0
    
    if cmd != 0 and cmd != 1:
        if cmd[0:6] == 'start ':
            for l in cmd[6:len(cmd)]:
                if l != ' ':
                    check = 1
            if check == 0:
                msg = '[-] Error: start requires a process name\nstart <name>		Start a process\n'
                msg = msg + 'start <gname>:*		Start all processes in a group\n' 
                msg = msg + 'start <name> <name>	Start multiple processes or groups\nstart all		Start all processes\n'
                return msg, valid
            check = 0
            action = cmd[6:len(cmd)].split()
            for arg in action:
                for name in config:
                    if name[0:8] == 'program:':
                        if arg == name[8:len(name)]:
                            valid.append(arg)
                            check = 1
                if check == 0:
                    msg = msg + '{}: ERROR (no such process)\n'.format(arg)
                check = 0
        check = 0 
        if cmd[0:5] == 'stop ':
            for l in cmd[5:len(cmd)]:
                if l != ' ':
                    check = 1
            if check == 0:
                msg = '[-] Error: stop requires a process name\nstop <name>           Stop a process\n'
                msg = msg + 'stop <gname>:*        Stop all processes in a group\n'
                msg = msg + 'stop <name> <name>    Stop multiple processes or groups\nstop all              Stop all processes\n' 
                return msg, valid
            check = 0
            action = cmd[5:len(cmd)].split()
            for arg in action:
                for name in config:
                    if name[0:8] == 'program:':
                        if arg == name[8:len(name)]:
                            valid.append(arg)
                            check = 1
                if check == 0:
                    msg = msg + '{}: ERROR (no such process)\n'.format(arg)
                check = 0
        check = 0
        if cmd[0:8] == 'restart ':
            for l in cmd[8:len(cmd)]:
                if l != ' ':
                    check = 1
            if check == 0:
                msg = '[-] Error: restart requires a process name\nrestart <name>           Restart a process\n'
                msg = msg + 'restart <gname>:*        Restart all processes in a group\n'
                msg = msg + 'restart <name> <name>    Restart multiple processes or groups\nrestart all              Restart all processes\n' 
                return msg, valid
            check = 0
            action = cmd[8:len(cmd)].split()
            for arg in action:
                for name in config:
                    if name[0:8] == 'program:':
                        if arg == name[8:len(name)]:
                            valid.append(arg)
                            check = 1
                if check == 0:
                    msg = msg + '{}: ERROR (no such process)\n'.format(arg)
                check = 0 
    return msg, valid
