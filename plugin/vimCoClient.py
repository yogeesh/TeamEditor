import vim
import json
from threading import Thread
import time
import socket
import struct

# Find the server path
VimCoServerPath = vim.eval('expand("<sfile>:h")') + '/vimCoServer.py'

class VimCoProtocol:
    __slots__ = 'vimCo', 'runFlag'

    def __init__(self, vimCo):
        self.vimCo = vimCo
        self.runFlag = True

    def send(self, data):
        # pack length of data along with it
        data = struct.pack('>I', len(data)) + data
        try:
            self.vimCo.connection.sendall(data)
        except socket.error:
            print 'Socket error occurred when sending'

    def recvall(self, data, n):
        # Helper function to recv n bytes or return None if EOF is hit
        while len(data) < n:
            try:
                packet = self.vimCo.recv(n - len(self.data))
            except socket.timeout:
                break
            except socket.error:
                print 'Socket error occurred when receiving'
                break
            if not packet:
                return None
            data += packet
        return data

    def stop(self):
        self.runFlag = False

    def run(self):
        begin = time.time()
        messageLen = None
        data = ''
        while self.runFlag is True:
            self.vimCo.connection.settimeout(0.001)

            if messageLen is None:
                data = self.recvall(data, 4)
                if len(data) == 4:
                    messageLen = struct.unpack('>I', data)[0]
                    data = ''

            if messageLen is not None:
                data = socket.recvall(data, messageLen)
                if len(data) == messageLen:
                    self.processData(data)
                    data = ''
                    messageLen = None

            self.vimCo.connection.settimeout(None)

            if time.time() - begin > 0.01:
                self.vimCo.update()
                begin = time.time()


    def __to_utf8(self, d):
        if isinstance(d, dict):
            d2 = {}
            for key, value in d.iteritems():
                d2[self.__to_utf8(key)] = self.__to_utf8(value)
            return d2
        elif isinstance(d, list):
            return map(self.to_utf8, d)
        elif isinstance(d, unicode):
            return d.encode('utf-8')
        else:
            return d

    def __clean_data(d):
        bad_data = d.find("}{")
        if bad_data > -1:
            d = d[:bad_data + 1]
        return d

    def processData(self, data_string):
        data_string = self.__clean_data(data_string)
        packet = self.__to_utf8(json.loads(data_string))

        if 'packet_type' in packet.keys():
            data = packet['data']
            if packet['packet_type'] == 'message':
                if data['message_type'] == 'error_newname_taken':
                    self.vimCo.disconnect()
                    print 'ERROR: Name already in use. Please try a different name'
                if data['message_type'] == 'error_newname_invalid':
                    self.vimCo.disconnect()
                    print 'ERROR: Name contains illegal characters. Only numbers, letters, underscores, and dashes allowed. Please try a different name'
                if data['message_type'] == 'connect_success':
                    self.vimCo.setup()
                    if 'buffer' in data.keys():
                        self.vimCo.vim_buffer = data['buffer']
                        vim.current.buffer[:] = self.vimCo.vim_buffer
                    print 'Success! You\'re now connected [Port ' + str(self.vimCo.port) + ']'
                if data['message_type'] == 'user_connected':
                    print data['user']['name'] + ' connected to this document'
                if data['message_type'] == 'user_disconnected':
                    print data['name'] + ' disconnected from this document'
            if packet['packet_type'] == 'update':
                if 'buffer' in data.keys() and data['name'] != self.vimCo.name:
                    b_data = data['buffer']
                    self.vimCo.vim_buffer = vim.current.buffer[:b_data['start']] \
                                            + b_data['buffer'] \
                                            + vim.current.buffer[b_data['end'] - b_data['change_y'] + 1:]
                    vim.current.buffer[:] = self.vimCo.vim_buffer
                if 'updated_cursors' in data.keys():
                    for updated_user in data['updated_cursors']:
                        if self.vimCo.name == updated_user['name'] and data['name'] != self.vimCo.name:
                            vim.current.window.cursor = (updated_user['cursor']['y'], updated_user['cursor']['x'])
            vim.command(':redraw')

class VimCoClient:
    __slots__ = 'addr', 'port', 'name', 'vim_buffer', 'protocol', 'isConnected', 'connection', 'protocol_thread'

    def __init__(self):
        self.protocol = VimCoProtocol(self)
        self.isConnected = False
        self.connection = None
        self.addr = None
        self.port = None
        self.name = None
        self.vim_buffer = None
        self.protocol_thread = None

    def start(self, arg1=False, arg2=False, arg3=False, arg4=False):
        default_name = vim.eval('VimCo_default_name')
        default_name_string = " - default: '" + default_name + "'" if default_name != '0' else ""
        default_port = vim.eval('VimCo_default_port')
        default_port_string = " - default: " + default_port if default_port != '0' else ""
        if arg1 == 'share':
            if arg2 and arg3:
                self.createServer(arg2, arg3)
            elif arg2 and default_name != '0':
                self.createServer(arg2, default_name)
            elif default_port != '0' and default_name != '0':
                self.createServer(default_port, default_name)
            else:
                print "usage :VimCo share [port" + default_port_string + "] [name" + default_name_string + "]"
        elif arg1 == 'connect':
            if arg2 and arg3 and arg4:
                self.connect(arg2, arg3, arg4)
            elif arg2 and arg3 and default_name != '0':
                self.connect(arg2, arg3, default_name)
            elif arg2 and default_port != '0' and default_name != '0':
                self.connect(arg2, default_port, default_name)
            else:
                print "usage :VimCo connect [host address / 'localhost'] [port" + default_port_string + "] [name" + default_name_string + "]"
        elif arg1 == 'disconnect':
            self.disconnect()
        elif arg1 == 'quit':
            self.disconnect()
            vim.command('q')
        else:
            print "usage: VimCo [share] [connect] [disconnect] [quit]"

    def createServer(self, port, name):
        vim.command(':silent execute "!' + VimCoServerPath + ' ' + port + ' &>/dev/null &"')
        time.sleep(1)
        self.connect('localhost', port, name)

    def connect(self, addr, port, name):
        if self.isConnected is True:
            print 'ERROR: Already connected. Please disconnect first'
            return
        """
        if not port and self.port:
            port = self.port
        if not addr and self.addr:
            addr = self.addr
        """
        if not addr or not port or not name:
            print 'Syntax Error: Use form :VimCo connect <server address> <port> <name>'
            return
        port = int(port)
        addr = str(addr)
        if self.connection is None:
            self.addr = addr
            self.port = port
            self.name = name
            self.vim_buffer = []
            print 'Connecting...'
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.connection.connect((socket.gethostbyname(addr), port))
            except socket.error:
                print 'ERROR: Unable to connect to server'
                return
            self.isConnected = True
            self.send(self.vimCo.name)

            self.protocol_thread = Thread(target=self.protocol.run)
            self.protocol_thread.start()
        elif (port != self.port) or (addr != self.addr):
            print 'ERROR: Different address/port already used. To try another, you need to restart Vim'
        """
        else:
            print 'Reconnecting...'
            self.connection.connect((addr, port))

            self.isConnected = True
            self.send(self.vimCo.name)
        """

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()
            self.isConnected = False
            self.protocol.stop()
            print 'Successfully disconnected from server!'
        else:
            print "ERROR: VimCo must be running to use this command"

    def update(self):
        d = {
            "packet_type": "update",
            "data": {
                "cursor": {
                    "x": max(1, vim.current.window.cursor[1]),
                    "y": vim.current.window.cursor[0]
                },
                "name": self.name
            }
        }
        d = self.create_update_packet(d)
        data = json.dumps(d)
        self.protocol.send(data)

    def create_update_packet(self, d):
        current_buffer = vim.current.buffer[:]
        if current_buffer != self.vim_buffer:
            cursor_y = vim.current.window.cursor[0] - 1
            change_y = len(current_buffer) - len(self.vim_buffer)
            change_x = 0
            if cursor_y-change_y < len(self.vim_buffer) and cursor_y-change_y >= 0 \
                    and cursor_y >= 0 and cursor_y < len(current_buffer):
                change_x = len(current_buffer[cursor_y]) - len(self.vim_buffer[cursor_y-change_y])
            limits = {
                'from': max(0, cursor_y - abs(change_y)),
                'to': min(len(vim.current.buffer) - 1, cursor_y + abs(change_y))
            }
            d_buffer = {
                'start': limits['from'],
                'end': limits['to'],
                'change_y': change_y,
                'change_x': change_x,
                'buffer': vim.current.buffer[limits['from']:limits['to'] + 1],
                'buffer_size': len(current_buffer)
            }
            d['data']['buffer'] = d_buffer
            self.vim_buffer = current_buffer
        return d

    def setup(self):
        vim.command('call SetCursorColors()')
        vim.command(':autocmd!')
