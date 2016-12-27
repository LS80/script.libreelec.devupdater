import os
import subprocess
from contextlib import contextmanager


OS_RELEASE = dict(line.strip().replace('"', '').split('=')
                  for line in open('/etc/os-release'))

UPDATE_DIR = os.path.join(os.path.expanduser('~'), '.update')
UPDATE_IMAGES = ('SYSTEM', 'KERNEL')


def release():
    dist = OS_RELEASE['NAME']
    return "{name}-{version}".format(name=dist,
                                     version=OS_RELEASE['VERSION_ID'])


def mount_readwrite():
    subprocess.check_call(['mount', '-o', 'rw,remount', '/flash'])


def mount_readonly():
    subprocess.call(['mount', '-o', 'ro,remount', '/flash'])


@contextmanager
def write_context():
    try:
        mount_readwrite()
    except subprocess.CalledProcessError:
        pass
    else:
        try:
            yield
        finally:
            mount_readonly()


def update_extlinux():
    subprocess.call(['/usr/bin/extlinux', '--update', '/flash'])


def system_device():
    for mount in open('/proc/mounts'):
        device, path = mount.split()[:2]
        if path == '/flash':
            return os.path.split(device)[-1]


def debug_system_partition():
    DEBUG_BYTES_REQUIRED = 384*1024*1024
    device = system_device()
    if device is None:
        return False
    system_size_bytes = int(open(os.path.join('/sys/class/block', device, 'size')).read()) * 512
    return system_size_bytes >= DEBUG_BYTES_REQUIRED
