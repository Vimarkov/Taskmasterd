import threading
import os
import time
import sys

from taskmasterd import report_log, find_program, get_env, get_umask
from parse_command import parse_command
from stop_program import confirm_stop

def init_program(name, pid, state, time, msg):
    status2 = {}
    status2['state'] = state
    status2['pid'] = pid
    status2['time'] = time
    status2['msg'] = msg
    status2['padding'] = 0
    status2['exit'] = 0
    status2['signal'] = 0
    status2['exit_status'] = 0
    status2['type'] = 0
    status2['startretries'] = 0
    status2['date'] = 0
    return status2 

def run_program(program, name, padding, status):
    fd0 = os.pipe()
    fd1 = os.pipe()
    fd2 = os.pipe()
    fd3 =  os.pipe()
    fderr = os.pipe()
    msg = 0

    try:
        pid = os.fork()
    except OSError:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
    if pid == 0:
        if find_program(program, 'directory') == 1:
            os.chdir(program['directory'])
        if find_program(program, 'umask') == 1:
            get_umask(program)
        pi = str(os.getpid())
        os.close(fd3[0])
        os.write(fd3[1], pi.encode())
        report_log("Spawned: \'{}\' with pid {}".format(name, pi))
        os.close(fd0[1])
        os.dup2(fd0[0], sys.stdin.fileno())
        os.close(fd0[0])
        if find_program(program, 'stdout_logfile') == 1:
            stdout_fd = open(program['stdout_logfile'], 'a')
            os.dup2(stdout_fd.fileno(), sys.stdout.fileno())
        else:
            os.close(fd1[0])
            os.dup2(fd1[1], sys.stdout.fileno())
            os.close(fd1[1])
        if find_program(program, 'stderr_logfile') == 1:
            stderr_fd = open(program['stderr_logfile'], 'a') 
            os.dup2(stderr_fd.fileno(), sys.stderr.fileno())
        else:
            os.close(fd2[0])
            os.dup2(fd2[1], sys.stderr.fileno())
            os.close(fd2[1])
        msg = get_env(program, name)
        cmd, args = parse_command(program['command'])  
        if msg:
            msg = msg.encode()
            os.write(2, msg)
            os.close(fderr[0])
            os.write(fderr[1], msg)
            sys.exit(1)
        if cmd == 0:
            msg = 'can\'t find command {}\n'.format(program['command'])
            msg = msg.encode()
            os.write(2, msg)
            os.close(fderr[0])
            os.write(fderr[1], msg)
            sys.exit(1)
        try:
            os.execv(cmd, args)
        except FileNotFoundError:
            msg = 'File not found'
            msg = msg.encode()
            os.write(2, msg)
            sys.exit(1)
        except OSError:
            msg = 'command at {} is not executable\n'.format(program['command'])
            msg = msg.encode()
            os.write(2, msg)
            os.close(fderr[0])
            os.write(fderr[1], msg)
            sys.exit(1)
    os.close(fd3[1])
    pi = os.read(fd3[0], 20)
    os.close(fd3[0])
    os.close(fderr[1])
    msg = os.read(fderr[0], 100) 
    os.close(fderr[0])
    if msg:
        msg = msg[0:len(msg)-1].decode()
    t = time.time()
    t = str(t)
    t = t[0:10]
    status[name] = init_program(name, pi.decode(), 'STARTING', t, msg)
    sts = os.waitpid(int(pi.decode()), 0)
    try:
        if os.WIFSIGNALED(sts[1]):
            exit_value = os.WTERMSIG(sts[1])
            status[name]['exit_status'] = exit_value
        if os.WIFEXITED(sts[1]):
            signal = os.WEXITSTATUS(sts[1])
            status[name]['signal'] = signal
        status[name]['exit'] = 1
    except KeyError:
        pass


def start_program(valid, status, config, padding):
    valid_arg = []
    msg = ''

    for arg in valid:
        valid_arg.append('program:' + arg)
    for name in valid_arg:
        if status[name]['state'] == 'STARTING' or status[name]['state'] == 'RUNNING' or status[name]['state'] == 'BACKOFF':
            msg = msg + '{}: ERROR (already started)\n'.format(name[8:])
        if status[name]['state'] == 'FATAL':
            msg = msg + '{}: ERROR (spawn error)\n'.format(name[8:])
        if status[name]['state'] == 'STOPPED' or status[name]['state'] == 'EXITED':
            thread = threading.Thread(target=run_program, args=(config[name], name, padding, status))
            thread.start()
            msg = msg + name + ': started\n'
    return(msg)

def restart_program(valid, status, config, padding):
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
        if status[name]['state'] == 'STARTING' or status[name]['state'] == 'RUNNING' or status[name]['state'] == 'BACKOFF':
            msg = msg + '{}: ERROR (already started)\n'.format(name[8:])
        if status[name]['state'] == 'FATAL':
            msg = msg + '{}: ERROR (spawn error)\n'.format(name[8:])
        if status[name]['state'] == 'STOPPED' or status[name]['state'] == 'EXITED':
            thread = threading.Thread(target=run_program, args=(config[name], name, padding, status))
            thread.start()
            msg = msg + name[8:] + ': started\n'
        time.sleep(0.1) 
    return msg
        