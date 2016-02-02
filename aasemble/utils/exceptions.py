class CommandFailed(Exception):
    def __init__(self, msg, cmd, returncode, stdout):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        super(CommandFailed, self).__init__(msg)
