#!/usr/bin/python

from threading import Event
import sys
import signal
from time import gmtime, strftime
import getopt
import getpass
from netmiko import ConnectHandler


called_interrupt = Event()


def command_arguments_prompt():
    # Should probably be using argparse here instead

    _script_name = "pyArubaPoll.py"
    print("Usage:  {script_name} (-h) <hostname|ip> (-p) <SSH port> (-u) <username> (-c) <command>")
    print()
    print("  -h | --host        hostname or IP for target device")
    print("  -p | --port        (OPTIONAL) specify the port for SSH connection, defaults to 22")
    print("  -u | --username    username to login with")
    print("  -c | --command     quoted command to run against target device")
    print("  -i | --interval    value in seconds for repeating the command")
    print("  -o | --output      (OPTIONAL) filename to be used for output, default filename is")
    print("                     '"'command-log-timestamp.txt'"'")
#    print("  -n | --iterations  number of times to run the command, defaults to infinite")
    print()
    print(f"example:  {_script_name} -h 192.168.1.1 -u admin -c '"'show version'"' -i 60 -o filename.txt")
    print()
    print("Output to file will always append if the file exists.")
    return


def process_command_arguments():
    class InvalidArguments(Exception):
        pass
    _argument_list = sys.argv[1:]
    _arg_host = None
    _arg_port = 22
    _arg_user = None
    _arg_command = None
    _arg_interval = None
    _arg_output = strftime("command-log-%Y%m%d_%H%M.txt", gmtime())

    _options = "h:p:u:c:i:o:"

    _long_options = ["host=", "port=", "username=", "command=", "interval=", "output="]

    try:
        _arguments, _values = getopt.getopt(_argument_list, _options, _long_options)
        for _currentArgument, _currentValue in _arguments:
            if _currentArgument in ("-h", "--host"):
                _arg_host = _currentValue
            elif _currentArgument in ("-p", "--port"):
                _arg_port = _currentValue
            elif _currentArgument in ("-u", "--username"):
                _arg_user = _currentValue
            elif _currentArgument in ("-c", "--command"):
                _arg_command = _currentValue
            elif _currentArgument in ("-i", "--interval"):
                _arg_interval = _currentValue
            elif _currentArgument in ("-o", "--output"):
                _arg_output = _currentValue
        if all(v is not None for v in [_arg_host, _arg_user, _arg_command, _arg_interval]):
            _arg_password = getpass.getpass("Password for %s@%s:" % (_arg_user, _arg_host))
            return _arg_host, _arg_port, _arg_user, _arg_password, _arg_command, _arg_interval, _arg_output
        else:
            raise InvalidArguments

    except getopt.error as err:
        print(str(err))

    except InvalidArguments:
        print("Not enough options specified, try again")
        print()
        command_arguments_prompt()
        exit()


def execute_ssh_command(_host, _port, _username, _password, _command):
    aos_device = {
        "device_type": "aruba_os",
        "host": _host,
        "username": _username,
        "password": _password,
        "port": _port,
    }
    try:
        with ConnectHandler(**aos_device) as net_connect:
            _command_output = net_connect.send_command(_command)

        return _command_output
    except BaseException:
        print("An error occurred")


def log_output_to_file(_logfile, _output):
    _target_file = open(_logfile, "a")
    _target_file.write(_output)
    _target_file.close()
    return


def called_quit(signo, _frame):
    print("Interrupted by %d, shutting down" % signo)
    called_interrupt.set()


def main():

    host, port, username, password, command, interval, logfile = process_command_arguments()

    while not called_interrupt.is_set():
        timestamp = strftime("%Y%m%d_%H%M", gmtime())

        output = execute_ssh_command(host, port, username, password, command)
        print(timestamp)
#        log_output_to_file(logfile, timestamp)
        print(output)
        log_output_to_file(logfile, output + "\r\n")
        called_interrupt.wait(int(interval))


if __name__ == "__main__":

    for sig in ("TERM", "HUP", "INT"):
        signal.signal(getattr(signal, "SIG"+sig), called_quit)

    main()
