import os
import os.path
import shutil
import tempfile
from unittest import TestCase

import mock

from six import assertRaisesRegex

from aasemble.utils import (TemporaryDirectory,
                            ensure_dir,
                            escape_cmd_for_ssh,
                            retry_for_duration_wrapper,
                            run_cmd,
                            run_cmd_until_succesful_or_timeout,
                            ssh_get,
                            ssh_run_cmd)

from aasemble.utils.exceptions import CommandFailed

stdout_stderr_script = '''#!/bin/sh

echo stdout
echo stderr >&2
'''


class UtilsTestCase(TestCase):
    def test_escape_cmd_for_ssh(self):
        self.assertEquals(escape_cmd_for_ssh(['echo', """'%\""""]), 'echo \'\'"\'"\'%"\'')

    @mock.patch('aasemble.utils.run_cmd')
    def test_ssh_get(self, run_cmd):
        ssh_get('user@remote', 'foo/bar*', 'mydestdir')
        run_cmd.assert_called_with(['scp',
                                    '-q',
                                    '-oStrictHostKeyChecking=no',
                                    '-oUserKnownHostsFile=/dev/null',
                                    'user@remote:foo/bar*', '.'], cwd='mydestdir')

    @mock.patch('aasemble.utils.run_cmd')
    def test_ssh_run_cmd(self, run_cmd):
        ssh_run_cmd('user@remote', ['touch', '"#'])
        run_cmd.assert_called_with(['ssh',
                                    '-q',
                                    '-oStrictHostKeyChecking=no',
                                    '-oUserKnownHostsFile=/dev/null',
                                    'user@remote',
                                    'touch \'"#\''])

    @mock.patch('aasemble.utils.run_cmd')
    def test_ssh_run_cmd_with_remote_cwd(self, run_cmd):
        ssh_run_cmd('user@remote', ['touch', '"#'], remote_cwd='workspace')
        run_cmd.assert_called_with(['ssh',
                                    '-q',
                                    '-oStrictHostKeyChecking=no',
                                    '-oUserKnownHostsFile=/dev/null',
                                    'user@remote',
                                    'mkdir -p workspace ; cd workspace ; touch \'"#\''])

    def test_ensure_dir(self):
        tmpdir = tempfile.mkdtemp()
        try:
            testdir = os.path.join(tmpdir, 'testdir')
            self.assertEquals(ensure_dir(testdir), testdir)
            self.assertTrue(os.path.isdir(testdir))
            self.assertEquals(ensure_dir(testdir), testdir)
        finally:
            shutil.rmtree(tmpdir)

    def test_run_cmd_dead_simple(self):
        # Should simply return successfully
        stdout = run_cmd(['true'])
        self.assertEquals(stdout, b'')

    def test_run_cmd_with_input(self):
        stdout = run_cmd(['cat'], input=b'hello\n')
        self.assertEquals(stdout, b'hello\n')

    def test_run_cmd_no_trailing_linefeed(self):
        logger = mock.MagicMock()
        stdout = run_cmd(['bash', '-c', 'echo -n foo'], logger=logger)
        self.assertEquals(stdout, b'foo')
        logger.log.assert_called_with(20, 'foo')

    def test_run_cmd_fail_raises_exception_and_includes_stderr(self):
        assertRaisesRegex(self, CommandFailed, 'STDERR', run_cmd, ['bash', '-c', 'echo STDOUT; echo STDERR >&2; false'])

    def test_run_cmd_fail_raises_exception_and_includes_stdout(self):
        assertRaisesRegex(self, CommandFailed, 'STDOUT', run_cmd, ['bash', '-c', 'echo STDOUT; echo STDERR >&2; false'])

    def test_run_cmd_with_logger_fail_raises_exception_and_includes_stderr(self):
        logger = mock.MagicMock()
        assertRaisesRegex(self, CommandFailed, 'STDERR', run_cmd, ['bash', '-c', 'echo STDOUT; echo STDERR >&2; false'], logger=logger)

    def test_run_cmd_override_env(self):
        os.environ['TESTVAR'] = 'foo'
        stdout = run_cmd(['env'])
        self.assertIn(b'TESTVAR=foo', stdout)

        stdout = run_cmd(['env'], override_env={'TESTVAR': 'bar'})
        self.assertIn(b'TESTVAR=bar', stdout)

        stdout = run_cmd(['env'], override_env={'TESTVAR': None})
        self.assertNotIn(b'TESTVAR=', stdout)

    def test_run_cmd_other_cwd(self):
        self.assertEquals(run_cmd(['pwd'], cwd='/').strip(), b'/')

    def _prepare_stdout_stderr_script(self):
        _fd, tmpfile = tempfile.mkstemp()
        try:
            os.close(_fd)
            with open(tmpfile, 'w') as fp:
                fp.write(stdout_stderr_script)
            os.chmod(tmpfile, 0o0755)
            return tmpfile
        except:  # pragma: nocover
            os.unlink(tmpfile)
            raise

    def test_run_cmd_stdout_includes_stderr(self):
        tmpfile = self._prepare_stdout_stderr_script()
        try:
            self.assertIn(b'stderr', run_cmd([tmpfile]))
        finally:
            os.unlink(tmpfile)

    def test_run_cmd_stdout_can_discard_stderr(self):
        tmpfile = self._prepare_stdout_stderr_script()
        try:
            self.assertNotIn(b'stderr', run_cmd([tmpfile], discard_stderr=True))
        finally:
            os.unlink(tmpfile)

    def test_run_cmd_alternate_stdout(self):
        fd, tmpfile = tempfile.mkstemp()
        try:
            with os.fdopen(fd, 'wb') as fp:
                rv = run_cmd(['echo', 'foo'], stdout=fp)

            self.assertEquals(rv, None)

            with open(tmpfile, 'rb') as fp:
                self.assertEquals(fp.read(), b'foo\n')

        finally:
            os.unlink(tmpfile)

    def test_run_cmd_retries(self):
        with TemporaryDirectory() as tmpdir:
            run_cmd_until_succesful_or_timeout(5, 3, ['bash', '-c', 'test -f foo || (touch foo; exit 1)'], cwd=tmpdir)

    @mock.patch('aasemble.utils.time')
    def test_retry_for_duration_wrapper_retries(self, time):
        self._setup_mock_time(time)

        func = mock.MagicMock()
        func.side_effect = self.FakeException('oh, dear')

        self.assertRaises(self.FakeException, retry_for_duration_wrapper, 20, 10, self.FakeException, func, 1, 2, foo='bar')

        self.assertEquals(len(func.call_args_list), 4)

    @mock.patch('aasemble.utils.time')
    def test_retry_for_duration_wrapper_retries_and_eventually_returns(self, time):
        self._setup_mock_time(time)

        func = mock.MagicMock()
        func.side_effect = [self.FakeException('oh, dear'),
                            self.FakeException('oh, dear2'),
                            'oh, this time it worked']

        self.assertEquals(retry_for_duration_wrapper(20, 10, self.FakeException, func, 1, 2, foo='bar'),
                          'oh, this time it worked')

    def _setup_mock_time(self, time):
        self.fake_timestamp = 0

        def fake_sleep(t):
            self.fake_timestamp += t

        def fake_time():
            return self.fake_timestamp

        time.time.side_effect = fake_time
        time.sleep.side_effect = fake_sleep

    class FakeException(Exception):
        pass

    def test_TemporaryDirectory(self):
        with TemporaryDirectory() as tmpdir:
            self.assertTrue(tmpdir.startswith('/tmp'))
            fpath = os.path.join(tmpdir, 'foobar')
            with open(fpath, 'w') as fp:
                fp.write('foo')
        self.assertFalse(os.path.exists(tmpdir))
