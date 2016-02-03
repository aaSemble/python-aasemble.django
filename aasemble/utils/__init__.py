import logging
import os
import select
import subprocess

from six import BytesIO
from six.moves import shlex_quote

from .exceptions import CommandFailed

LOG = logging.getLogger(__name__)


def escape_cmd_for_ssh(cmd):
    return ' '.join([shlex_quote(arg) for arg in cmd])


def ssh_run_cmd(connect_string, cmd, remote_cwd=None, *args, **kwargs):
    if remote_cwd:
        cmd_real = 'mkdir -p {0} ; cd {0} ; '.format(shlex_quote(remote_cwd))
    else:
        cmd_real = ''

    cmd_real += escape_cmd_for_ssh(cmd)
    ssh_cmd = ['ssh', '-q', '-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null', connect_string, cmd_real]
    return run_cmd(ssh_cmd, *args, **kwargs)


def ssh_get(connect_string, remote_pattern, destdir):
    cmd = ['scp', '-q', '-oStrictHostKeyChecking=no', '-oUserKnownHostsFile=/dev/null', '{0}:{1}'.format(connect_string, remote_pattern), '.']
    run_cmd(cmd, cwd=destdir)


def run_cmd(cmd, input=None, cwd=None, override_env=None,
            discard_stderr=False, stdout=None, logger=LOG):
    logger.debug("%r, input=%r, cwd=%r, override_env=%r, discard_stderr=%r" %
                 (cmd, input, cwd, override_env, discard_stderr))

    environ = dict(os.environ)

    stdout = stdout or BytesIO()

    for k in override_env or []:
        if override_env[k] is None and k in environ:
            del environ[k]
        else:
            environ[k] = override_env[k]

    if discard_stderr:
        stderr_arg = subprocess.PIPE
    else:
        stderr_arg = subprocess.STDOUT

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=stderr_arg, cwd=cwd, env=environ)

    tmpbuf = [b'']
    input = [input]

    rfds = [proc.stdout]

    if discard_stderr:
        rfds += [proc.stderr]

    if input[0]:
        wfds = [proc.stdin]
    else:
        wfds = []
        proc.stdin.close()

    def check_io(forever=False, tmpbuf=tmpbuf, input=input):
        while rfds or wfds:
            ready_to_read, ready_to_write, _ = select.select(rfds, wfds, [], 1000)

            for io in ready_to_read:
                buf = os.read(io.fileno(), 4096)

                if not buf:
                    rfds.remove(io)

                if io == proc.stderr:
                    continue

                stdout.write(buf)

                tmpbuf[0] += buf

                while b'\n' in tmpbuf[0]:
                    line, lf, tmpbuf[0] = tmpbuf[0].partition(b'\n')
                    logger.log(logging.INFO, line.decode('utf-8', errors='replace'))

                # Make sure we get that last characters, even if there's not linefeed
                if not buf:
                    logger.log(logging.INFO, tmpbuf[0].decode('utf-8', errors='replace'))

            for io in ready_to_write:
                c, input[0] = input[0][0:1], input[0][1:]
                io.write(c)

                if not input[0]:
                    io.close()
                    wfds.remove(io)

            if not forever:
                break

    while proc.poll() is None:
        check_io()

    wfds = []

    check_io(forever=True)

    logger.info("%r returned with returncode %d." % (cmd, proc.returncode))

    final_output = getattr(stdout, 'getvalue', lambda: None)()

    if proc.returncode != 0:
        raise CommandFailed('%r returned %d. stdout=%r' % (cmd, proc.returncode, final_output),
                            cmd, proc.returncode, final_output)

    return final_output


def ensure_dir(d):
    if not os.path.isdir(d):
        os.makedirs(d)
    return d

try:
    from tempfile import TemporaryDirectory
except ImportError:
    import tempfile
    import shutil

    class TemporaryDirectory(object):
        def __init__(self, *args, **kwargs):
            self.name = tempfile.mkdtemp(*args, **kwargs)

        def cleanup(self):
            shutil.rmtree(self.name)

        def __enter__(self):
            return self.name

        def __exit__(self, exc, value, tb):
            self.cleanup()
