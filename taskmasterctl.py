import sys
import configparser
import socket
import time
from get_config import *
from parse_data import *
from term import read_input

g_state = {}

def get_pass(sock, login):
    if login != 0:
        while True:
            try:
                ask_pass = sock.recv(1024)
            except KeyboardInterrupt:
                print("\n[-] KeyboardInterrupt. Exiting...")
                sock.close()
                sys.exit(1)
            if ask_pass.decode() == 'SUCCES':
                break 
            print(ask_pass.decode())
            try:
                pswd = input()
            except KeyboardInterrupt:
                sock.sendall(b'exit')
                print("\n[-] KeyboardInterrupt. Exiting...") 
                sock.close()
                sys.exit(1)
            if not pswd:
                pswd = '0'
            sock.sendall(pswd.encode())
        return pswd
    return 0

def get_login(sock, login):
    if login == 0:
        while True:
            try:
                ask_login = sock.recv(1024)
            except KeyboardInterrupt:
                print("\n[-] KeyboardInterrupt. Exiting...")
                sock.close()
                sys.exit(1)
            print(ask_login.decode())
            try:
                login = input()
            except KeyboardInterrupt:
                sock.sendall(b'exit')
                print("\n[-] KeyboardInterrupt. Exiting...") 
                sock.close()
                sys.exit(1)
            if not login:
                login = '0'
            sock.sendall(login.encode())
            if len(login) > 2:
                break
        
        return(login)
    return(0)

if __name__ == "__main__":
    if len(sys.argv) > 3 or len(sys.argv) < 1:           #Need to parse args
        print("[-] Usage: ./Tasmaster <File.conf>")
        sys.exit(1)
    config_data = configparser.ConfigParser()
    config_data.read(sys.argv[1])
    get_config(config_data)
    server = 1
    shutdown = 0
    data = b''
    i = 0
    login = 0
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            while True:
                try:
                    sock.connect((config['client1']['host'], int(config['client1']['port'])))
                    if shutdown != 1:
                        print('[+] Connected to', config['client1']['host'], config['client1']['port'])
                    server = 1
                    if shutdown == 1:
                        sock.close()
                        break
                except ConnectionRefusedError:
                    print('[-] Connection error')
                    shutdown = 0
                    sock.close()
                    server = 0
                    login = 0
                    os.write(1, b'Taskmaster> ')
                    try:
                        out = read_input()
                        if out == 0:
                            sys.exit(1)
                        os.write(1, b'\n')
                    except KeyboardInterrupt:
                        print("\n[-] KeyboardInterrupt. Exiting...") 
                        sock.close()
                        sys.exit(1) 
                    break
                except OSError: 
                    sock.close()
                    break
                if server == 1:
                    #login = get_login(sock, login)
                    #pswd = get_pass(sock, login)

                    msg = sock.recv(1024)
                    print(msg.decode(), end='')
                    while True:
                        while True:
                            os.write(1, b'Taskmaster> ')
                            try:
                                command = read_input()
                                os.write(1, b'\n')
                                if command == 0:
                                    sys.exit(1)
                            except KeyboardInterrupt:
                                print("\n[-] KeyboardInterrupt. Exiting...") 
                                sock.close()
                                sys.exit(1)
                            command = parse_data(command, config)
                            if command != 0 and command != 1:
                                break 
                            else:
                                if command == 0:
                                    print('[-] Command not found.')
                        if len(command) > 0:
                            try:
                                sock.sendall(command.encode())
                            except BrokenPipeError:
                                sock.close()
                                break
                            if command != 'shutdown':
                                try:
                                    data = sock.recv(1024)
                                except KeyboardInterrupt:
                                    print("\n[-] KeyboardInterrupt. Exiting...")
                                    sock.close()
                                    sys.exit(1) 
                                except ConnectionResetError:
                                    sock.close()
                                    break
                            if command:
                                if command == 'shutdown':
                                    shutdown = 1
                                    sock.close()
                                    break
                                print(data.decode(), end='')
