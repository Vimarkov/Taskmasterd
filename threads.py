import threading
import sys
import configparser
import socket
import multiprocessing
import signal
import time
import timeit
import datetime

from parse_command import *
from parse_data import *
from daemonize import *
from get_config import *
from start_program import *
from stop_program import *

def decoupe(seconde):

    heure = seconde /3600
    heure = int(heure)
    seconde %= 3600
    minute = seconde/60
    minute =int(minute)
    seconde%=60
    heure = str(heure)
    minute = str(minute)
    seconde = str(seconde)

    return heure + ':' + minute + ':' + seconde

def find_program(program, name):
    for data in program:
        if data == name:
            return 1
    return 0

def init_program(name, pid, state, time, msg):
    status2 = {}
    status2['state'] = state
    status2['pid'] = pid
    status2['time'] = time
    status2['msg'] = msg
    status2['padding'] = 0
    status2['exit'] = 0
    status[name] = status2 

def confirm_stop(program, data, status):
    try:
        os.kill(int(status[data]['pid']), 0)
        if status[data]['state'] == 'STOPPED':
            print('pass')
            time.sleep(int(program['stopwaitsecs']))
    except ProcessLookupError:
        print('ok')
        pass

def check_pid(padding, data, status, program):
    dur = 0
    space = padding - len(data)
    try:
        os.kill(int(status[data]['pid']), 0)
        if status[data]['time'] != 0:
            start = time.time()
            start = str(start)
            start = start[0:10]
            start = int(start) - int(status[data]['time'])
            dur = start
            start = decoupe(start)
        else:
            status[data]['time'] = time.time()
            start = status[data]['time']            
            start = str(start)
            start = start[0:10]
            start = int(start) - int(status[data]['time'])
        
        if status[data]['state'] == 'STOPPED':
            status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' pid {}, uptime {}'.format(status[data]['pid'], start)
            return status[data]['string']
        if dur < int(program['startsecs']):
            status[data]['state'] = 'STARTING'
        else:
            status[data]['state'] = 'RUNNING'
        status[data]['padding'] = " " * 30 + " " * space
        status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' pid {}, uptime {}'.format(status[data]['pid'], start) 
        return status[data]['string']
    except ProcessLookupError:
        stop = time.time()
        stop = str(stop)
        stop = stop[0:10]
        stop = int(stop) - int(status[data]['time']) 
        if status[data]['state'] == 'STOPPED' or status[data]['state'] == 'EXITED':
            if status[data]['date']: 
                status[data]['padding'] = " " * 30 + " " * space
                status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + status[data]['date'] 
                return status[data]['string']
        status[data]['time'] = 0
        if status[data]['exit'] == 1:
            if status[data]['state'] != 'FATAL' and status[data]['state'] != 'EXITED' and status[data]['state'] != 'STOPPED':
                status[data]['state'] = 'BACKOFF'
            if not status[data]['msg'] and status[data]['state'] != 'EXITED':                
                status[data]['msg'] = 'Exited too quickly (process log may have details)'
        status[data]['padding'] = " " * 30 + " " * space
        status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' {}'.format(status[data]['msg']) 
        return status[data]['string']
    except ValueError:
        if status[data]['exit'] == 2:
            status[data]['state'] = 'STOPPED'
            if not status[data]['msg']:
                status[data]['msg'] = 'Not started'
        status[data]['padding'] = " " * 30 + " " * space
        status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' {}'.format(status[data]['msg']) 
        return status[data]['string']

def run_program(program, name, padding):
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
        pi = str(os.getpid())
        os.close(fd3[0])
        os.write(fd3[1], pi.encode())
        report_log("Spawned {}".format(program['command']))
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

        cmd, args = parse_command(program['command'])        
        if cmd == 0:
            msg = 'can\'t find command {}\n'.format(program['command'])
            msg = msg.encode()
            os.write(2, msg)
            os.close(fderr[0])
            os.write(fderr[1], msg)
            sys.exit(1)
        try:
            os.execl(cmd, cmd, args)
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
    init_program(name, pi.decode(), 'STARTING', 0, msg)
    sts = os.waitpid(int(pi.decode()), 0)
    if os.WIFSIGNALED(sts[1]):
        exit_value = os.WTERMSIG(sts[1])
        status[name]['exit_status'] = exit_value
    if os.WIFEXITED(sts[1]):
        signal = os.WEXITSTATUS(sts[1])
        status[name]['signal'] = signal
    status[name]['exit'] = 1

def check_program(program, name, cmd, padding, valid):
    nb = 0
    if cmd == 0:
        if find_program(program, 'autostart') == 1:
            if program['autostart'] == 'true':
                if find_program(program, 'command') == 1:
                    run_program(program, name, padding)
                else:
                    print('[-] Error: program section program {} does not specify a command'.format(name))
                    sys.exit(1)
            if program['autostart'] == 'false':
                init_program(name, '', 'STOPPED', 0, '')
                status[name]['exit'] = 2
        else:
            if find_program(program, 'command') == 1:
                run_program(program, name, padding)
            else:
                print('[-] Error: program section program {} does not specify a command'.format(name))
                sys.exit(1)
    if cmd != 0 and cmd != 1:
        start_program(cmd, status, name, valid)


def run_conf(config, cmd, status, av, pid):
    i = 0
    conf = {}
    old_name = []
    old = []
    msg = ''
    names = 0
    padding = 0
    for header in config:
        if header[0:8] == 'program:':
            if len(header) > padding:
                padding = len(header)
    msg, valid_actions = parse_actions(cmd, config, status)
    if cmd == 0:
        for name in status:
            msg = msg + check_pid(padding, name, status, config[name]) + '\n'
    if cmd == 'help':
        msg = msg + 'default commands:\n'
        msg = msg + '================\n'
        msg = msg + '[status], [start], [stop], [restart]\n'
        msg = msg + '[update], [reread], [shutdown]\n'
    if cmd == 'status':
        for name in status:
            msg = msg + check_pid(padding, name, status, config[name]) + '\n'
    if cmd != 0: 
        if cmd[0:5] == 'stop ':
            if valid_actions:
                msg = msg + stop_program(valid_actions, status, config, padding)
        if cmd[0:6] == 'start ':
            if valid_actions:
                msg = msg + start_program(valid_actions, status, config, padding)
        if cmd[0:8] == 'restart ':
            if valid_actions:
                msg = msg + restart_program(valid_actions, status, config, padding)
        if cmd[0:8] == 'reread':
            err = []
            cmd = 0
            autostart = 0
            check = 0
            config_data = configparser.ConfigParser()
            try:
                config_data.read(av)
            except configparser.DuplicateSectionError:
                print ('program exist already')
                sys.exit(1) 
            new_conf = get_tmp_config(config_data)
            for name in config:
                if name[0:8] == 'program:':
                    for name2 in new_conf:
                        if name2[0:8] == 'program:':
                            if name[8:8+len(name2[8:len(name2)])] == name2[8:len(name)]:
                                if find_program(config[name], 'autostart') == 1:
                                    autostart = config[name]['autostart'] 
                                cmd = config[name]['command']
                                config[name] = new_conf[name2]
                                config[name]['command'] = cmd 
                                config[name]['autostart'] = autostart
            parse_conf(config, pid, status)
            msg = msg + 'configuration file reread\n'
        if cmd[0:8] == 'update':
            config_data = configparser.ConfigParser()
            try:
                config_data.read(av)
            except configparser.DuplicateSectionError:
                print ('program exist already')
                sys.exit(1)
            new_conf = get_tmp_config(config_data)
            msg = msg + parse_conf2(new_conf, pid, status)
            if  msg == '\n':
                for name in new_conf:
                    if name[0:8] == 'program:':
                        names = name
                        if find_program(new_conf[name], 'numprocs') == 0:
                            new_conf[name]['numprocs'] = 1
                        while i < int(new_conf[name]['numprocs']):
                            if int(new_conf[name]['numprocs']) > 1:
                                names = name + ':' + name[8:] + str(i)
                                conf[names] = new_conf[name]
                            else:
                                conf[name] = new_conf[name]
                            i = i + 1
                        if int(new_conf[name]['numprocs']) > 1:
                            old.append(name)
                        i = 0
                    else:
                        if name[0:8] == 'program:':
                            if int(new_conf[name]['numprocs']) != 0:
                                conf[name] = new_conf[name]
                msg = msg + check_config(config, conf, status, config_data, padding, old, pid) 
    return msg

def multi_process(config, connection, client, status, av, pid):
    cmd = 0
    state = 0
    bis = 0
    with connection:
        #print('[+] Client({}): {} connected on port {}'.format(client['login'], config['client1']['host'], config['client1']['port']))
        report_log('[+] Client({}): {} connected on port {}'.format(client['login'], config['client1']['host'], config['client1']['port']))
        while True:
            msg = run_conf(config, cmd, status, av, pid)
            if not msg:
                msg = 'No program loaded\n' 
            connection.sendall(msg.encode())
            try:
                data = connection.recv(1024)
            except ConnectionResetError:
                print('[-] Client({}): {} leaves on port {}.'.format(client['login'], config['client1']['host'], config['client1']['port']))
                break 
            report_log('Client sended: {}'.format(data.decode()))
            if data:
                if data == b'shutdown':
                    client['command'] = data.decode()
                    connection.sendall(data)
                    break
                cmd = data.decode() 
            else:
                client['command'] = 'exit'
                print('[-] Client({}): {} leaves on port {}.'.format(client['login'], config['client1']['host'], config['client1']['port']))
                break
