import os
import select
import sys
import termios, fcntl, sys, os

def report_history(history):
    pidfile = '/tmp/.history'
    with open(pidfile, 'a') as f:
        f.write(history + '\n')

def read_input():
    i = 0
    er = 0
    mx = 0
    histl = ''
    up = 0
    down = 0
    check = 0
    history = 0
    flag = []
    pidfile = '/tmp/.history'
    fd = sys.stdin.fileno()
    flags_save = fcntl.fcntl(fd, fcntl.F_GETFL)
    attrs_save = termios.tcgetattr(fd)
    attrs = list(attrs_save) # copy the stored version to update
    attrs[0] &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK
                  | termios.ISTRIP | termios.INLCR | termios.IGNCR
                  | termios.ICRNL | termios.IXON )
    attrs[1] &= ~termios.OPOST
    attrs[2] &= ~(termios.CSIZE | termios.PARENB)
    attrs[2] |= termios.CS8
    attrs[3] &= ~(termios.ECHONL | termios.ECHO | termios.ICANON
                  | termios.ISIG | termios.IEXTEN)
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags_save & ~os.O_NONBLOCK)
    ret = ''
    fd1 = open(pidfile, 'a')
    try:
        while True:
            inp, out, err = select.select([sys.stdin], [], [])
            c = sys.stdin.read(1) # returns a single character
            if ord(c) >= 28 and ord(c) <= 126:
                ret = ret + c
                os.write(1, c.encode())
                er = er + 1
            if ord(c) == 27:
                if len(c) == 1:
                    if c != '\r':
                        c = sys.stdin.read(2)
                        if c == '[A':
                            history = open('/tmp/.history', 'r')
                            lines = history.readlines()
                            lines.reverse()
                            while i < er:
                                os.write(1, chr(8).encode())
                                os.write(1, b' ')
                                os.write(1, chr(8).encode())
                                i = i + 1
                            ret = ''
                            i = 0
                            er = 0
                            if up > 0:
                                #if mx == 0:
                                while i < len(lines[up -1]) - 1:
                                    os.write(1, chr(8).encode())
                                    os.write(1, b' ')
                                    os.write(1, chr(8).encode())
                                    i = i + 1
                                i = 0
                            try:
                                os.write(1, lines[up][0:len(lines[up]) - 1].encode())
                                ret = lines[up][0:len(lines[up]) - 1]
                                up = up + 1
                                mx = 0
                            except IndexError:
                                try:
                                    os.write(1, lines[up -1][0:len(lines[up -1]) - 1].encode())
                                    ret = lines[up -1][0:len(lines[up -1]) - 1]
                                except IndexError:
                                    pass
                        if c == '[B':
                            history = open('/tmp/.history', 'r')
                            lines = history.readlines()
                            lines.reverse()
                            if up > 0:
                                mx = 0
                                up = up - 1
                                while i < er:
                                    os.write(1, chr(8).encode())
                                    os.write(1, b' ')
                                    os.write(1, chr(8).encode())
                                    i = i + 1
                                ret = ''
                                i = 0
                                er = 0

                                while i < len(lines[up]) - 1:
                                    os.write(1, chr(8).encode())
                                    os.write(1, b' ')
                                    os.write(1, chr(8).encode())
                                    i = i + 1
                                i = 0
                                if up - 1 >= 0:
                                    try:
                                        os.write(1, lines[up - 1][0:len(lines[up - 1]) - 1].encode())
                                        ret = lines[up - 1][0:len(lines[up - 1]) - 1] 
                                        down = down + 1
                                    except IndexError:
                                        pass
            if len(c) == 1:
                if ord(c) == 127:
                    if len(ret) > 0:
                        ret = ret[0:len(ret) - 1]
                        er = er - 1
                        os.write(1, chr(8).encode())
                        os.write(1, b' ')
                        os.write(1, chr(8).encode())
                if ord(c) == 3:
                    return(0)
            if c == '\r':
                break
        if ret:
            report_history(ret)
    except KeyboardInterrupt:
        ret.append('\x03')
    finally:
        # restore old state
        termios.tcsetattr(fd, termios.TCSAFLUSH, attrs_save)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags_save)
    return(ret)

if __name__ == "__main__":
    ret = read_single_keypress()
