import os
from taskmasterd import find_program
from daemonize import report_log
#from threads import confirm_stop
import time

def confirm_stop(program, data, status):
    report_log('Waiting for {} to stop'.format(data))
    try:
        os.kill(int(status[data]['pid']), 0)
        if status[data]['state'] == 'STOPPED':
            print('pass')
            time.sleep(int(program['stopwaitsecs']))
    except ProcessLookupError:
        report_log('Stopped: {} (terminated by SIG{})'.format(data, program['stopsignal']))
        pass
    except ValueError:
        pass

def stop_program(valid, status, config, padding):
    valid_arg = []
    msg = ''
    sign = 0
    for arg in valid:
        valid_arg.append('program:' + arg)
    for name in valid_arg:
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
        if status[name]['state'] == 'STOPPED' or status[name]['state'] == 'FATAL' or status[name]['state'] == 'EXITED':
            msg = msg + '{}: ERROR (not running)\n'.format(name[8:])
        if status[name]['state'] == 'RUNNING' or status[name]['state'] == 'STARTING':
            os.kill(int(status[name]['pid']), sign)
            status[name]['state'] = 'STOPPED'
            msg = msg + name[8:] + ': stopped\n'
        if status[name]['state'] == 'BACKOFF' or status[name]['state'] == 'STARTING':
            status[name]['state'] = 'STOPPED'
            msg = msg + name[8:] + ': stopped\n'
        time.sleep(0.1)
        confirm_stop(config[name], name, status)
    return(msg)
