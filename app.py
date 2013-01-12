import tornado.web
import tornado.httpserver
import tornado.ioloop
import subprocess
import tempfile
import os
import sys

TESSERACT_PATH = "/usr/local/bin/tesseract"


class MainHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def prepare(self):
        self.paths = {}

    def post(self):
        f = self.request.files['file'][0]
        self.paths = {
            'input': tempfile.mktemp(suffix=f['filename']),
            'output': tempfile.mktemp(suffix='.txt')
        }

        tesseract_out = os.path.splitext(self.paths['output'])[0]
        options = self.get_argument('options', default='').split(' ')

        with open(self.paths['input'], 'wb') as i:
            i.write(f['body'])

        self.subprocess([TESSERACT_PATH, self.paths['input'],
            tesseract_out] + options, self.on_stdout)

    def on_finish(self):
        for key, val in enumerate(self.paths):
            try:
                os.remove(val)
            except OSError:
                pass

    def on_stdout(self, data):
        if data is None:
            with open(self.paths['output'], 'r') as o:
                text = o.read()
            self.finish(text)

    def subprocess(self, cmd, callback):
        ioloop = tornado.ioloop.IOLoop.instance()
        PIPE = subprocess.PIPE
        cmd = " ".join(cmd)
        pipe = subprocess.Popen(cmd, shell=True, stdin=PIPE,
            stdout=PIPE, stderr=subprocess.STDOUT, close_fds=True)
        fd = pipe.stdout.fileno()

        def read(*args):
            data = pipe.stdout.readline()
            if data:
                callback(data)
            elif pipe.poll() is not None:
                ioloop.remove_handler(fd)
                callback(None)

        # read handler
        ioloop.add_handler(fd, self.async_callback(read), ioloop.READ)


application = tornado.web.Application([
    (r"/", MainHandler),
])


def main():
    application.listen(8010, address='127.0.0.1')
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        import daemon
        log = open('tesseract-web-service.log', 'a+')
        pwd = os.path.dirname(os.path.realpath(__file__))
        with daemon.DaemonContext(stdout=log, stderr=log,
            working_directory=pwd):
            main()
    else:
        main()
