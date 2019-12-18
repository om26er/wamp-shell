import getpass
import socket
import sys
import threading
import tty
import termios

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession


class _GetchUnix:
    def __call__(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


getter = _GetchUnix()


class STDOutSession(ApplicationSession):
    def __init__(self, config=None):
        super().__init__(config)
        self.name = "{}@{}".format(getpass.getuser(), socket.gethostname())
        self.run = True

    def on_stdout(self, stdout):
        if stdout.strip() == 'exit':
            self.run = False
        print(stdout)

    def on_key(self, key):
        sys.stdout.buffer.write(key.encode())

    def read_stdin(self, name):
        def actually_read():
            while self.is_connected():
                key = getter()
                self.call("io.crossbar.command.send_key", key)
        threading.Thread(target=actually_read).start()

    async def onJoin(self, details):
        await self.subscribe(self.on_stdout, "io.crossbar.command.stdout")
        await self.subscribe(self.on_key, "io.crossbar.command.on_key")
        name = await self.call("io.crossbar.command.id")
        self.read_stdin("{} ".format(name))


if __name__ == '__main__':
    runner = ApplicationRunner("ws://localhost:8080/ws", "realm1")
    runner.run(STDOutSession)
