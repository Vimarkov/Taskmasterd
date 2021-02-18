from threads import find_program
from start_program import run_program, init_program
from stop_program import confirm_stop
from daemonize import report_log
import threading
import time
import os

old_conf = {}
config = {}
client = {}
def shutdown(pid, status):  
    if status:
        for name in status:
            try:
                os.kill(int(status[name]['pid']), 9)
            except ProcessLookupError:
                pass
    os.kill(pid, 9) 
    sys.exit(1)

def parse_conf2(config, pid, status):
    signalcode = ['TERM', 'HUP', 'INT', 'QUIT', 'KILL', 'USR1', 'USR2']
    check = 0
    for name in config:
        if find_program(config[name], 'stopsignal') == 1:
            if len(config[name]['stopsignal']) > 4:
                return('Error: value {} is not a valid signal name in section {}'.format(config[name]['stopsignal'], name))
            if signalcode.count(config[name]['stopsignal']) == 0:
                return('Error: value {} is not a valid signal name in section {}'.format(config[name]['stopsignal'], name))
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
                return('Error: Unexpected end of key/value pairs in value ' + config[name]['environment'] + ' in section ' + name)
            check = 0
            env = config[name]['environment'].split(",")
            for data in env:
                for letter in data:
                    if letter == '=':
                        check = 1
                if check == 0:
                    return('Error: Unexpected end of key/value pairs in value ' + config[name]['environment'] + ' in section ' + name)
                check = 0
                odd = 0
                for letter in data:
                    if letter == '\"':
                        check = check + 1
                    if check != 0 and check % 2 == 0:
                        odd = 1
                if odd != 1:
                    return('Error: Unexpected end of key/value pairs in value ' + config[name]['environment'] + ' in section ' + name)
        if find_program(config[name], 'startsecs') == 1:
            try:
                int(config[name]['startsecs'])
            except ValueError:
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['startsecs'], name))
        if find_program(config[name], 'numprocs') == 1:
            try:
                int(config[name]['numprocs'])
            except ValueError:
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['numprocs'], name))
        if find_program(config[name], 'stopwaitsecs') == 1:
            try:
                int(config[name]['stopwaitsecs'])
            except ValueError:
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['stopwaitsecs'], name))
        if find_program(config[name], 'umask') == 1:
            try:
                int(config[name]['umask'])
            except ValueError:
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['umask'], name))
        if find_program(config[name], 'autostart') == 1:
            test = config[name]['autostart'] 
            if test != 'true' and test != 'false':
                return('Error: not a valid boolean value: '' in section {}'. format(name))
        if find_program(config[name], 'startretries') == 1:
            try:
                int(config[name]['startretries'])
            except ValueError:
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['startretrties'], name))
        if find_program(config[name], 'exitcodes') == 1:
            try:
                int(config[name]['exitcodes'])
            except ValueError:
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['exitcodes'], name))
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
                return('invalid literal for int() with base 10: \'{}\' in {}'.format(config[name]['stopsignal'], name))
    return '\n'

def get_config(config_data):
    for i in config_data:
        headers = {}
        for y in config_data[i]:
            headers[y] = config_data[i][y]
        config[i] = headers

def get_tmp_config(config_data):
    config = {}
    for i in config_data:
        headers = {}
        for y in config_data[i]:
            headers[y] = config_data[i][y]
        config[i] = headers
    return config

def get_command(data, command):
    command['state'] = data.decode()
    return(command)

def confirm_stop(program, data, status):
    try:
        os.kill(int(status[data]['pid']), 0)
        if status[data]['state'] == 'STOPPED':
            print('pass')
            time.sleep(int(program['stopwaitsecs']))
    except ProcessLookupError:
        pass
    except ValueError:
        pass
    except KeyError:
        pass

def stop_config(status, config, name):
    msg = ''
    sign = 0
    if find_program(config[name], 'stopsignal') == 0:
            sign = 15
    else:
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
    try:
        if status[name]['state'] == 'STOPPED' or status[name]['state'] == 'FATAL' or status[name]['state'] == 'EXITED':
            msg = msg + '{}: ERROR (not running)\n'.format(name[8:])
        if status[name]['state'] == 'RUNNING' or status[name]['state'] == 'STARTING':
            try:
                os.kill(int(status[name]['pid']), sign)
                status[name]['state'] = 'STOPPED'
                msg = msg + name[8:] + ': stopped\n'
            except ProcessLookupError:
                pass
        if status[name]['state'] == 'BACKOFF' or status[name]['state'] == 'STARTING':
            status[name]['state'] = 'STOPPED'
            msg = msg + name[8:] + ': stopped\n'
    except KeyError:
        pass
    time.sleep(0.1)
    confirm_stop(config[name], name, status)
    return(msg)

def start_config(status, config, name, padding):
    msg = ''
    if config[name]['autostart'] == 'true':
        thread = threading.Thread(target=run_program, args=(config[name], name, padding, status))
        thread.start()
        msg = msg + name + ': started\n'
    if config[name]['autostart'] == 'false':
        status[name] = init_program(name, '', 'STOPPED', 0, 'Not started')
    return(msg)

def check_data(data, process_group):
    for name in process_group:
        if name == data:
            return 1
    return 0


def check_config(config, new_conf, status, config_data, padding, rem, pid):
    i = 0
    stop_process = []
    process_group = []
    conf = {}
    old = {}
    check = 0
    gap = 0
    msg = '\n'

    for data in new_conf:
        if data[0:8] == 'program:':
            if find_program(new_conf[data], 'autostart') == 0:
                new_conf[data]['autostart'] = 'true'
            if find_program(new_conf[data], 'autorestart') == 0:
                new_conf[data]['autorestart'] = 'unexpected'
            if find_program(new_conf[data], 'startretries') == 0:
                new_conf[data]['startretries'] = '3'
            if find_program(new_conf[data], 'exitcodes') == 0:
                new_conf[data]['exitcodes'] = 0
            if find_program(new_conf[data], 'stopwaitsecs') == 0:
                new_conf[data]['stopwaitsecs'] = 10
            if find_program(new_conf[data], 'startsecs') == 0:
                new_conf[data]['startsecs'] = 1
    msg = parse_conf2(new_conf, pid, status)
    if msg and msg != '\n':
        return(msg)
    else:
        msg = 'Nothing to update\n'
    for data in new_conf:
        if data[0:8] == 'program:':
            try:
                if status[data]: 
                    pass                                      
            except KeyError:
                if check_data(data, process_group) == 0:
                    process_group.append(data)         
    for name in config:
        if name[0:8] == 'program:':
            try:    
                if new_conf[name]:
                    pass
            except KeyError:
                stop_process.append(name)         
    for data in new_conf:
        if data[0:8] == 'program:':
            
            for data2 in new_conf[data]:
                try:
                    if config[data][data2]:
                        pass
                except KeyError:
                    for name in process_group:
                        if data == name:
                            check = 1
                    if check == 0:
                        if check_data(data, process_group) == 0:
                            process_group.append(data)
                        stop_process.append(data)
    check = 0
    for data in config:
        if data[0:8] == 'program:':
            for data2 in config[data]:
                try:
                    if new_conf[data][data2]:
                        pass
                except KeyError:
                    for name in stop_process:
                        if data == name:
                            check = 1
                    if check == 0:
                        if check_data(data, process_group) == 0:
                            process_group.append(data)
                        stop_process.append(data)
    check = 0
    for data in new_conf:
        if data[0:8] == 'program:':
            try: 
                if new_conf[data] == config[data]:
                    pass
                else:
                    for name in stop_process:
                        if data == name:
                            check = 1
                    if check == 0:
                        if check_data(data, process_group) == 0:
                            process_group.append(data)
                        stop_process.append(data)
            except KeyError:
                pass
    if stop_process:
        for name in stop_process:
            msg = msg + stop_config(status, config, name)
            confirm_stop(config[name], name, status)
            msg = msg + name + ' removed to process group\n'
            old[name] = 0
            try:
                del old_conf[name]
            except KeyError:
                pass 
            try:
                del status[name]
                del config[name]
            except KeyError:
                pass
    for name in new_conf:
        config[name] = new_conf[name]
    if process_group:
        for name in process_group:
            if find_program(config[name], 'autostart') == 0:
                config[name]['autostart'] = 'true'
            if find_program(config[name], 'autorestart') == 0:
                config[name]['autorestart'] = 'unexpected'
            if find_program(config[name], 'startretries') == 0:
                config[name]['startretries'] = '3'
            if find_program(config[name], 'exitcodes') == 0:
                config[name]['exitcodes'] = 0
            if find_program(config[name], 'stopwaitsecs') == 0:
                config[name]['stopwaitsecs'] = 10
            if find_program(config[name], 'startsecs') == 0:
                config[name]['startsecs'] = 1
            msg = msg + start_config(status, config, name, padding) 
            time.sleep(0.1)
            msg = msg + name + ' added to process group\n'
    report_log('Configuration file reloaded')
    return msg
