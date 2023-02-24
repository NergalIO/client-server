from App import Form
from sys import argv

if len(argv) != 2:
    addr = ('localhost', 3030)
else:
    addr, port = argv[1].split(':')
    addr = (addr, int(port))

form = Form(addr)

form.start()