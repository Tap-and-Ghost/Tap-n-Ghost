from __future__ import print_function
import threading
import time
import nfc

CONNECT_INTERVAL_SECS = 0.1
CONNECT_ITERATIONS = 2
CONNECT_TIMEOUT_SECS = 0.5
SHORTEST_SENSE_SECS = 1


def sense(clf):
    started = time.time()

    res = []
    res.append(time.strftime("%H:%M:%S", time.localtime(started)))
    for target in ['106A', '106B', '212F']:
        state = State()
        clf.connect(rdwr={'targets': (target,), 'on-discover': state.on_discover,
                          'interval': CONNECT_INTERVAL_SECS, 'iterations': CONNECT_ITERATIONS},
                    terminate=state.should_terminate)
        res.append(state.target)

    secs = SHORTEST_SENSE_SECS - (time.time() - started)
    if(secs > 0):
        time.sleep(secs)

    return res


class State(object):
    def __init__(self):
        self.target = None
        self.started = time.time()

    def should_terminate(self):
        return self.target or time.time() - self.started > CONNECT_TIMEOUT_SECS

    def on_discover(self, target):
        self.target = target


class SenseThread(threading.Thread):
    def __init__(self, name, path, log_writer, surpress=False):
        super(SenseThread, self).__init__()
        self.name = name
        self.path = path
        self.log_writer = log_writer
        self.surpress = surpress
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def run(self):
        with nfc.ContactlessFrontend(self.path) as clf:
            while not self.stop_event.is_set():
                res = sense(clf)
                self.log_writer.writerow(res)
                if not self.surpress or any(res[1:]):
                    print(", ".join(map(str, [res[0]] + [self.name] + res[1:])))
        print('[-] Thread Exits: ' + self.name)
