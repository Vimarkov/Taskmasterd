import sys
import configparser
import socket
import os, signal
import time

from threads import *
from get_config import *
from daemonize import *
from parse_data import parse_conf
import datetime

status = {}
g_client = []
g_state = 0

def get_umask(program):
    num = int(program['umask'], 8)
    os.umask(num)

def ask_pass(connection, client, login):
    if login != 0:
        while True:
            try:
                connection.sendall(b'Password:') 
            except BrokenPipeError:
                return(0)
            try:
                pswd = connection.recv(1024)
            except ConnectionResetError:
                return(0)
            if pswd.decode() == 'root':
                connection.sendall(b'SUCCES') 
                break
        return pswd

def ask_login(connection, client):
    if client['login'] == 0:
        while True:
            try:
                connection.sendall(b'Login:') 
            except BrokenPipeError:
                return(0)
            try:
                login = connection.recv(1024)
            except ConnectionResetError:
                return(0)
            if len(login.decode()) > 2:
                break
        return (login)

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
    status2['signal'] = 0
    status2['exit_status'] = 0
    status2['startretries'] = 0
    status2['type'] = 0
    status2['date'] = 0
    
    status[name] = status2 

def get_env(program, name):
    value = []
    variable = []
    nb = 1
    var = ''
    check = 0
    odd = 0
    string = ''

    if find_program(program, 'environment') == 1:
        for letter in program['environment']:
            if letter == ',':
                check = 1
        if check == 0:
            string = 'Error: Unexpected end of key/value pairs in value ' + program['environment'] + ' in section ' + name
            return(string)
        check = 0
        env = program['environment'].split(",")
        for data in env:
            for letter in data:
                if letter == '=':
                    check = 1
            if check == 0:
                string = 'Error: Unexpected end of key/value pairs in value ' + program['environment'] + ' in section ' + name
                return(string)
            check = 0
            odd = 0
            for letter in data:
                if letter == '\"':
                    check = check + 1
                if check != 0 and check % 2 == 0:
                    odd = 1
            if odd != 1:
                string = 'Error: Unexpected end of key/value pairs in value ' + program['environment'] + ' in section ' + name
                return(string) 
        for data in env:
            for letter in data:
                if letter != '=':
                    var = var + letter
                else:
                    break
            variable.append(var)
            var = ''
        env2 = program['environment'].split("\"") 
        for data in env2:
            if nb % 2 == 0:
                value.append(data)
            nb = nb + 1
        nb = 0 
        for data in variable:
            os.environ[data] = value[nb]
            nb = nb + 1
    return(string)

def check_pid(padding, data, program):
    space = padding - len(data)

    #try:
    #    print(data + ' ' + status[data]['state'])
    #except KeyError:
    #    pass
    try:
        os.kill(int(status[data]['pid']), 0)
        if status[data]['state'] == 'STOPPED':
            report_log('Waiting for ' + data + ' to stop')
            os.kill(int(status[data]['pid']), 9)
            report_log('Stopped ' + data + ' (terminated by SIGKILL)')
            return data
        if status[data]['time'] == 0:
            start = time.time()
            start = str(start)
            start = start[0:10]
            status[data]['time'] = start
        else:
            start = time.time()
            start = str(start)
            start = start[0:10]
            start = int(start) - int(status[data]['time'])
        if start < int(program['startsecs']):
            status[data]['state'] = 'STARTING'
        else:
            if status[data]['state'] != 'RUNNING':
                report_log('Succes: {} entered RUNNING state, process has stayed up for > than {} (startsecs)'.format(data, program['startsecs']))
            status[data]['state'] = 'RUNNING'
        status[data]['msg'] = ''
        status[data]['padding'] = " " * 30 + " " * space
        status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' pid {}, uptime {}'.format(status[data]['pid'], status[data]['time']) 
        return data
    except ProcessLookupError:
        stop = time.time()
        stop = str(stop)
        stop = stop[0:10]
        stop = int(stop) - int(status[data]['time']) 
        
        #print(data + status[data]['state'])
        if int(stop) < 2:
            report_log('Exited: \'{}\' (exit status {}; not expected)'.format(data, status[data]['exit_status']))
            status[data]['type'] = 'quick'
        else:
            if status[data]['exit_status'] != 0:
                pass
        if status[data]['state'] == 'STOPPED' or status[data]['state'] == 'EXITED':
            if status[data]['date'] == 0:
                today = datetime.datetime.now()
                date = today.strftime("%B %d %H:%M:%S")
                status[data]['date'] = ' ' + date
                status[data]['padding'] = " " * 30 + " " * space
                status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + date
                return data
        status[data]['time'] = 0
        if status[data]['exit'] == 1:
            if status[data]['state'] != 'FATAL' and status[data]['state'] != 'EXITED' and status[data]['state'] != 'STOPPED':
                status[data]['state'] = 'BACKOFF'
            if not status[data]['msg'] and status[data]['state'] != 'EXITED':
                status[data]['msg'] = 'Exited too quickly (process log may have details)'
        status[data]['padding'] = " " * 30 + " " * space
        status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' {}'.format(status[data]['msg']) 
        return data
    except ValueError:
        if status[data]['exit'] == 2:
            status[data]['state'] = 'STOPPED'
            if not status[data]['msg']:
                status[data]['msg'] = 'Not started'
        status[data]['time'] = 0
        status[data]['padding'] = " " * 30 + " " * space
        status[data]['string'] = data + status[data]['padding'] + status[data]['state'] + ' {}'.format(status[data]['msg']) 
        return data
    except KeyError:
        return data

def run_program(program, name, padding):

    fd0 = os.pipe()
    fd1 = os.pipe()
    fd2 = os.pipe()
    fd3 =  os.pipe()
    fderr = os.pipe()
    
    msg = 0
    var = ''
    value = []
    variable = []

     
    try:
        pid = os.fork()
    except OSError:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
    if pid == 0:
        if find_program(program, 'directory') == 1:
            try:
                os.chdir(program['directory'])
            except FileNotFoundError:
                pass
        if find_program(program, 'umask') == 1:
            get_umask(program)
        pi = str(os.getpid())
        
        os.close(fd3[0])
        try:
            os.write(fd3[1], pi.encode())
        except BrokenPipeError:
            print('broken pipe')
            os.kill(int(pi), 9)
            sys.exit(1)
        report_log("Spawned: \'{}\' with pid {}".format(name, pi))
            
        os.close(fd0[1])
        os.dup2(fd0[0], sys.stdin.fileno())
        os.close(fd0[0])
        if find_program(program, 'stdout_logfile') == 1:
            try:
                stdout_fd = open(program['stdout_logfile'], 'a')
                os.dup2(stdout_fd.fileno(), sys.stdout.fileno())
            except FileNotFoundError:
                pass
        else:
            os.close(fd1[0])
            os.dup2(fd1[1], sys.stdout.fileno())
            os.close(fd1[1])
        
        if find_program(program, 'stderr_logfile') == 1:
            try:
                stderr_fd = open(program['stderr_logfile'], 'a') 
                os.dup2(stderr_fd.fileno(), sys.stderr.fileno())
            except FileNotFoundError:
                pass
        else:
            os.close(fd2[0])
            os.dup2(fd2[1], sys.stderr.fileno())
            os.close(fd2[1])
        msg = get_env(program, name)
        cmd, args = parse_command(program['command'])  
        if msg == 0:
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
            os.execv(str(cmd), args)
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
    state = 'STARTING'
    #if status[name]['state'] == 'FATAL':
    #    state = 'FATAL'
    init_program(name, pi.decode(), state, t, msg)
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
    try:
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
    except KeyError:
        pass

def supervise(padding, name, program):
   
    startretries = 1
    while True:
        try:
            for name in status:
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
                startretries = startretries + status[name]['startretries']    
                name = check_pid(padding, name, config[name])
                try:
                    if status[name]['state'] == 'BACKOFF':
                        if config[name]['autorestart'] == 'false':
                            if status[name]['type'] != 'quick':
                                status[name]['state'] = 'EXITED'
                            if status[name]['type'] == 'quick':
                                startretries = startretries + 1
                                thread = threading.Thread(target=run_program, args=(config[name], name, padding))
                                thread.start()
                                time.sleep(0.2)
                            if str(startretries) == program['startretries']:
                                report_log('Gave up: {} entered FATAL state, too many start retries too quickly'.format(name))
                                status[name]['state'] = 'FATAL'
                                startretries = 1
                        else: 
                            if config[name]['autorestart'] == 'true': 
                                if status[name]['type'] == 'quick':
                                    startretries = startretries + 1
                                thread = threading.Thread(target=run_program, args=(config[name], name, padding))
                                thread.start()
                                time.sleep(0.2)
                            if config[name]['autorestart'] == 'unexpected': 
                                if status[name]['type'] == 'quick':
                                    startretries = startretries + 1
                                if status[name]['exit_status'] != 0 and status[name]['exit_status'] != int(config[name]['exitcodes']):
                                    report_log('Exited: \'{}\' (terminated by SIG{}; not expected)'.format(name, status[name]['exit_status'])) 
                                    thread = threading.Thread(target=run_program, args=(config[name], name, padding))
                                    thread.start()
                                    time.sleep(0.2)
                                if status[name]['exit_status'] != 0:
                                    if status[name]['exit_status'] == int(config[name]['exitcodes']): 
                                        status[name]['state'] = 'EXITED'
                                        report_log('Exited: {} (exit status {}; expected)'.format(name, status[name]['exit_status']))  
                            if str(startretries) == config[name]['startretries']:
                                report_log('Gave up: {} entered FATAL state, too many start retries too quickly'.format(name))
                                status[name]['state'] = 'FATAL'
                                startretries = 1
                except KeyError:
                    pass
            time.sleep(0.2)
        except RuntimeError:
            pass

def run_config(config, cmd, state, pid):
    msg = ''
    old_name = []
    nb = 0
    padding = 0
    i = 0
    names = 0
    new_conf = {}
    for header in config:
        if header[0:8] == 'program:':
            if len(header) > padding:
                padding = len(header)
    
    for name in config:
        if name[0:8] == 'program:':
            names = name
            if find_program(config[name], 'numprocs') == 0:
                config[name]['numprocs'] = 1
            try:
                while i < int(config[name]['numprocs']): 
                    if int(config[name]['numprocs']) > 1:
                        names = name + ':' + name[8:] + str(i)
                        new_conf[names] = config[name]
                    else:
                        new_conf[name] = config[name]
                    nb = nb + 1
                    thread = threading.Thread(target=check_program, args=(config[name], names, cmd, padding, 0))
                    thread.start()
                    time.sleep(0.1)
                    i = i + 1
            except ValueError:
                shutdown(pid)
            if int(config[name]['numprocs']) > 1:
                old_name.append(name)
            i = 0
        else:
            new_conf[name] = config[name]
    for name in old_name:
        del config[name]
    for name in new_conf:
        config[name] = new_conf[name]
    while True:
        if len(status) == nb or nb == 0:
            for name in status:
                if status[name]['exit'] == 0:
                    try:
                        os.kill(int(status[name]['pid']), 0)
                        status[name]['exit'] = 1
                    except ProcessLookupError:
                        status[name]['exit'] = 1
            if state == 0:        
                for name2 in status:
                    if status[name2]['exit'] == 0:                                                
                        state = 0
                        break
                    if status[name2]['exit'] != 0:                                                
                        state = 1
                if state == 1:
                    thread1 = threading.Thread(target=supervise, args=(padding, name, config[name])) 
                    thread1.start()
                    break
            if not status:
                thread1 = threading.Thread(target=supervise, args=(padding, name, config[name])) 
                thread1.start()
                break

if __name__ == "__main__":
    i = 0
    if len(sys.argv) > 3 or len(sys.argv) < 1:           
        print("[-] Usage: ./Tasmaster <File.conf>")
        sys.exit(1)
    config_data = configparser.ConfigParser()
    try:
        config_data.read(sys.argv[1])
    except configparser.DuplicateSectionError:
        print ('program exist already')
        sys.exit(1)
    get_config(config_data)
    client['login'] = 0
    client['command'] = 0
    daemonize()
    report_log('daemonizing the supervisord process')
    pid = os.getpid()
    report_log('supervisord started with pid ' + str(pid))
    parse_conf(config, pid, status)
    run_config(config, 0, 0, pid)
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((config['client1']['host'], int(config['client1']['port']))) 
            except OSError:
                print('[-] OSError: [Errno 48] Address already in use')
                for name in status:
                    try:
                        os.kill(int(status[name]['pid']), 9)
                    except ProcessLookupError:
                        pass
                os.kill(pid, 9) 
                sys.exit(1)
            while True:
                sock.listen()
                report_log('-' * 40)
                report_log("[+] Listening...")
                try:
                    connection, addr = sock.accept()
                except KeyboardInterrupt:
                    report_log('\n[-] KeyboardInterrupt. Exiting...')
                    print('\n[-] KeyboardInterrupt. Exiting...')
                    sys.exit(1) 
                #login = ask_login(connection, client)
                #pswd = ask_pass(connection, client, login) 
                
                thread1 = threading.Thread(target=multi_process, args=(config, connection, client, status, sys.argv[1], pid))
                g_client.append(thread1)
                thread1.start()
                thread1.join()
                if client['command'] == 'shutdown':
                    for name in status:
                        try:
                            os.kill(int(status[name]['pid']), 9)
                        except ProcessLookupError:
                            pass
                        except ValueError:
                            pass
                    os.kill(pid, 9)
                    sock.close()
