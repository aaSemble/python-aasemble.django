import logging
import os
import os.path
import subprocess

from django.template.loader import render_to_string

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

    for k in override_env or []:
        if override_env[k] is None and k in environ:
            del environ[k]
        else:
            environ[k] = override_env[k]

    if discard_stderr:
        stderr_arg = subprocess.PIPE
    else:
        stderr_arg = subprocess.STDOUT

    if stdout is not None:
        stdout_arg = stdout
    else:
        stdout_arg = subprocess.PIPE

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=stdout_arg,
                            stderr=stderr_arg, cwd=cwd, env=environ)
    stdout, stderr = proc.communicate(input)

    logger.info("%r returned with returncode %d." % (cmd, proc.returncode))
    logger.info("%r gave stdout: %s." % (cmd, stdout))
    logger.info("%r gave stderr: %s." % (cmd, stderr))

    if proc.returncode != 0:
        raise CommandFailed('%r returned %d. Output: %s (stderr: %s)' %
                            (cmd, proc.returncode, stdout, stderr),
                            cmd, proc.returncode, stdout, stderr)

    return stdout


def ensure_dir(d):
    if not os.path.isdir(d):
        os.makedirs(d)
    return d
