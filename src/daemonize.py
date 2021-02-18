import os
import sys
import resource
import atexit
import time

def daemonize():
    stdin='/dev/null'
    stdout='/dev/null'
    stderr='/dev/null'
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

        os.chdir('/')
        os.setsid()
        os.umask(0)

        try:
            pid = os.fork()
            if pid > 0:
                        # exit from second parent
                sys.exit(0)
        except OSError:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        sys.stdout.flush()
        sys.stderr.flush()
        si = open(stdin, 'r')
        so = open(stdout, 'a+')
        se = open(stderr, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

            # write pidfile
def delpid():
    try:
        os.remove('/tmp/taskmasterd.log')
    except FileNotFoundError:
        pass

def report_log(log):
    sec = time.time()
    pidfile = '/tmp/taskmasterd.log'
    atexit.register(delpid)
    pid = str(os.getpid())
    date = time.ctime(sec)
    with open(pidfile, 'a') as f:
        f.write(date + ' ' + pid + ' ' + log + '\n')

def report_err(err):
    if err == 0:
        err = '/dev/null'
    pidfile = err
    atexit.register(delpid)
    fd = open(pidfile, 'a')
    return(fd)

def report_out(out):
    if out == 0:
        out = '/tmp/out'
    pidfile = out
    atexit.register(delpid)
    fd = open(pidfile, 'a')
    return(fd)