import logging
import os
import os.path
import select
import subprocess

from django.template.loader import render_to_string

from six import BytesIO

from .exceptions import CommandFailed

LOG = logging.getLogger(__name__)


def recursive_render(src, dst, context, logger=LOG):
    logger.debug('Processing %s' % (src,))
    if os.path.isdir(src):
        if not os.path.isdir(dst):
            os.mkdir(dst)
        for f in os.listdir(src):
            recursive_render(os.path.join(src, f), os.path.join(dst, f), context)
    else:
        if src.endswith('.swp'):
            return
        logger.debug('Rendering %s' % (src,))
        s = render_to_string(src, context)
        logger.debug('Result: %r' % (s,))
        with open(dst, 'w') as fp_out:
            fp_out.write(s)


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
                c, input[0] = input[0][0], input[0][1:]
                io.write(c)

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
