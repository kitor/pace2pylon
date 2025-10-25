import sys
import os
from datetime import datetime
from threading import Semaphore

# Temporary stuff for split screen logging. Replace with a proper logger later.

_THREADS_BASE = 3
_THREAD_LINES = 9

logs = []

print_semaphore = Semaphore()

def printxy(text, x=0, y=0):
    # Prints text on console at given coordinates
    sys.stdout.write("\033[{};{}H".format(y, x))
    sys.stdout.write("\033[K")
    sys.stdout.write(text)
    sys.stdout.flush()


def ts_print(line):
    ts  = datetime.now().strftime("%m-%d %H:%M:%S%z")
    print(f"{ts} {line}")


def tprint(thread_id, buf):
    if (thread_id > 12) and (thread_id < (len(logs) - 2)):
	# skip webui and batteries logs
        ts_print(buf)

    return

    print_semaphore.acquire()
    try:
        lines = buf.splitlines()
        for line in lines:
            ts  = datetime.now().strftime("%m-%d %H:%M:%S%z")
            logs[thread_id].append(f"{ts} {line}")

        base = _THREADS_BASE + _THREAD_LINES * thread_id
        off = 0

        for line in logs[thread_id][-_THREAD_LINES+2:]:
            printxy(line, 0, base+off)
            off+=1
    except:
        pass
    print_semaphore.release()


def clear_screen():
    os.system('clear')
