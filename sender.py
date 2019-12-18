import asyncio
import collections
import getpass
import subprocess
import shlex
import socket
import threading

from autobahn.asyncio.wamp import ApplicationRunner, ApplicationSession


class STDOutSession(ApplicationSession):
    def __init__(self, config=None):
        super().__init__(config)
        self.name = "{}@{}".format(getpass.getuser(), socket.gethostname())
        self.stdout = collections.deque()
        self.buffer = ''

    def get_prompt(self):
        return "{}:$".format(self.name)

    def process_key(self, key):
        if key == '\r':
            cmd = str(self.buffer)
            self.buffer = ''
            if cmd != '':
                threading.Thread(target=self.actually_run_command, args=(cmd,)).start()
            else:
                self.publish("io.crossbar.command.stdout", key)
        else:
            self.buffer += key
            self.publish("io.crossbar.command.on_key", key)

    def actually_run_command(self, cmd):
        process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
        self.stdout.append("{}:$ {}".format(self.name, cmd))
        for line in process.stdout:
            self.stdout.append(line.decode().strip())

    async def start_publishing(self):
        while len(self.stdout) > 0:
            self.publish("io.crossbar.command.stdout", self.stdout.popleft())
        while len(self.stdout) == 0:
            await asyncio.sleep(0.2)
        await self.start_publishing()

    async def onJoin(self, details):
        await self.register(self.get_prompt, "io.crossbar.command.id")
        await self.register(self.process_key, "io.crossbar.command.send_key")
        await self.start_publishing()


if __name__ == '__main__':
    runner = ApplicationRunner("ws://localhost:8080/ws", "realm1")
    runner.run(STDOutSession)
