import os

import psutil


def get_usage():
    pid = os.getpid()
    process = psutil.Process(pid)

    with process.oneshot():
        mem = process.memory_info()
        cpu = process.cpu_times()
        cpu_percent = process.cpu_percent()

    return {
        'memory': {
            'resident': mem.rss,
            'virtual': mem.vms,
        },
        'cpu': {
            'user': cpu.user,
            'system': cpu.system,
            'percent': cpu_percent,
        }
    }
