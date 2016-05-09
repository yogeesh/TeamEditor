import json
from threading import Thread
import time
import socket
import struct

from vimPlatform import *
from vimUI import *


class CursorManager:
    """
    The cursor manager
    """
    __slots__ = 'nextCursorId', 'nextCursorColor', 'cursors', 'editorModel'

    def __init__(self, editorModel):
        """
        Initializer
        :param editorModel: the editor model
        """
        self.nextCursorId = 1
        self.reset()
        self.editorModel = editorModel

    def reset(self):
        """
        Resets the cursor manager
        :return: None
        """
        self.nextCursorColor = 1
        self.cursors = {}

    def addCursor(self, name, x, y):
        """
        Adds cursor of the given user name
        :param name: name of the user
        :param x: column number of cursor
        :param y: row number of cursor
        :return: None
        """
        if name == self.editorModel.name:
            self.cursors[name] = ('CursorUser', 99999)
        else:
            self.cursors[name] = ('Cursor' + str(self.nextCursorColor), self.nextCursorId)
            self.nextCursorId += 1
            self.nextCursorColor = (self.nextCursorId) % self.editorModel.ui.getNumberOfCursorColors()
            self.editorModel.ui.addCursor(self.cursors[name][1], self.cursors[name][0], x, y)

    def removeCursor(self, name):
        """
        Removes cursor of the given user name
        :param name: the user name of the cursor to be removed
        :return: None
        """
        self.editorModel.ui.removeCursor(self.cursors[name][1])
        del (self.cursors[name])

    def updateCursor(self, name, x, y):
        """
        Updates cursor of the given user name
        :param name: name of the user
        :param x: column number of cursor
        :param y: row number of cursor
        :return: None
        """
        self.editorModel.ui.updateCursor(self.cursors[name][1], self.cursors[name][0], x, y)


class EditorModel:
    """
    The collaborative text editor client model
    """
    __slots__ = 'addr', 'port', 'name', 'prevBuffer', 'isConnected', 'connection', 'cursorManager', 'controller', 'ui'

    def __init__(self, controller, ui):
        """
        Initializer
        :param controller: the editor controller
        :param ui: the user interface
        """
        self.isConnected = False
        self.connection = None
        self.addr = None
        self.port = None
        self.name = None
        self.prevBuffer = None
        self.cursorManager = None
        self.controller = controller
        self.ui = ui

    def createServer(self, port, name):
        """
        Create and run the server
        :param port: the server's listening port
        :param name: name of the host user
        :return: None
        """
        self.controller.platform.runServer(port)
        time.sleep(1)
        self.connect('localhost', port, name)

    def connect(self, addr, port, name):
        """
        Connect to the server with given user name
        :param addr: IP address of the server
        :param port: listening port of the server
        :param name: user name
        :return: None
        """
        if self.isConnected is True:
            self.ui.printError('Already connected to a server. Please disconnect first')
            return
        if not port and self.port:
            port = self.port
        if not addr and self.addr:
            addr = self.addr
        if not addr or not port or not name:
            self.ui.printError('Wrong syntax. Usage: ' + self.platform.getApplicationName() + \
                               ' connect <server address> <port> <name>')
            return

        port = int(port)
        addr = str(addr)
        if self.connection is None:
            self.addr = addr
            self.port = port
            self.name = name
            self.prevBuffer = []
            self.cursorManager = CursorManager(self)
            self.ui.printMessage('Connecting...')
            self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.connection.connect((addr, port))
            except socket.error:
                self.ui.printError('Unable to connect to server')
                return
            self.isConnected = True
            self.send(self.connection, self.name)

            self.controller.startDaemonThread()
        elif (port != self.port) or (addr != self.addr):
            self.ui.printError('Different address,port already used. You need to restart to try new ones')

    def disconnect(self):
        """
        Disconnect from the server
        :return: None
        """
        if self.connection is not None:
            for name in self.cursorManager.cursors.keys():
                if name != self.name:
                    self.ui.removeCursor(self.cursorManager.cursors[name][1])
            self.controller.stopDaemonThread()
            self.connection.close()
            self.connection = None
            self.isConnected = False
            self.cursorManager.reset()
            self.ui.printMessage('Successfully disconnected from the server!')
        else:
            self.ui.printError(self.platform.getApplicationName() + ' must be running to use this command')

    def __addUsers(self, users):
        """
        Add a list of users
        :param users: the list of user data to be added
        :return: None
        """
        map(self.__addUser, users)

    def __addUser(self, userData):
        """
        Add a user
        :param userData: the user data to be added
        :return: None
        """
        self.cursorManager.addCursor(userData['name'], userData['cursor']['x'], userData['cursor']['y'])

    def __removeUser(self, name):
        """
        Remove a user
        :param name: the name of the user to be removed
        :return: None
        """
        self.cursorManager.removeCursor(name)

    def update(self):
        """
        Update the server about the user's current state
        :return:
        """
        d = {
            "type": "update",
            "data": {
                "cursor": {
                    "x": max(1, self.ui.getCursorX()),
                    "y": self.ui.getCursorY()
                },
                "name": self.name
            }
        }
        d = self.__createUpdatePacket(d)
        data = json.dumps(d)
        self.send(self.connection, data)

    def __createUpdatePacket(self, d):
        """
        Creates update packet with the changes in the text
        :param d: the packet data to which we need to append the text changes
        :return: the updated packet data
        """
        currentBuffer = self.ui.getCurrentBuffer()
        if currentBuffer != self.prevBuffer:
            cursor_y = self.ui.getCursorY() - 1
            change_y = len(currentBuffer) - len(self.prevBuffer)
            change_x = 0
            if cursor_y - change_y < len(self.prevBuffer) and cursor_y - change_y >= 0 \
                    and cursor_y >= 0 and cursor_y < len(currentBuffer):
                change_x = len(currentBuffer[cursor_y]) - len(self.prevBuffer[cursor_y - change_y])
            limits = {
                'from': max(0, cursor_y - abs(change_y)),
                'to': min(len(currentBuffer) - 1, cursor_y + abs(change_y))
            }
            d_buffer = {
                'start': limits['from'],
                'end': limits['to'],
                'change_y': change_y,
                'change_x': change_x,
                'buffer': currentBuffer[limits['from']:limits['to'] + 1],
                'buffer_size': len(currentBuffer)
            }
            d['data']['buffer'] = d_buffer
            self.prevBuffer = currentBuffer
        return d

    def __toUtf8(self, data):
        """
        Encode received data to UTF-8
        :param data: the data to be encoded
        :return: the UTF-8 encoded data
        """
        if isinstance(data, dict):
            d2 = {}
            for key, value in data.iteritems():
                d2[self.__toUtf8(key)] = self.__toUtf8(value)
            return d2
        elif isinstance(data, list):
            return map(self.__toUtf8, data)
        elif isinstance(data, unicode):
            return data.encode('utf-8')
        else:
            return data

    def __cleanData(self, data):
        """
        Preprocess received data to remove unnecessary characters
        :param data: the data to be cleaned
        :return: the cleaned data
        """
        dirtyData = data.find("}{")
        if dirtyData > -1:
            data = data[:dirtyData + 1]
        return data

    def processData(self, data_string):
        """
        Process the received data and take actions
        :param data_string: the raw unprocessed data received
        :return: None
        """
        data_string = self.__cleanData(data_string)
        packet = self.__toUtf8(json.loads(data_string))

        if 'type' in packet.keys():
            data = packet['data']
            if packet['type'] == 'message':
                """
                if data['message_type'] == 'error_newname_taken':
                    self.disconnect()
                    self.ui.printError('Name already in use. Please try a different name')
                elif data['message_type'] == 'error_newname_invalid':
                    self.disconnect()
                    self.ui.printError(
                        'Name contains illegal characters. Only numbers, letters, underscores, and dashes allowed. ' + \
                        'Please try a different name')
                el
                """
                if data['message_type'] == 'connect_success':
                    self.ui.setCursorColors()
                    if 'buffer' in data.keys():
                        self.prevBuffer = data['buffer']
                        self.ui.setCurrentBuffer(self.prevBuffer)
                    self.ui.printMessage('Success! You\'re now connected [Port ' + str(self.port) + ']')
                    self.__addUsers(data['users'])
                elif data['message_type'] == 'user_connected':
                    self.ui.printMessage(data['user']['name'] + ' connected to this document')
                    self.__addUsers([data['user']])
                elif data['message_type'] == 'user_disconnected':
                    self.__removeUser(data['name'])
                    self.ui.printMessage(data['name'] + ' disconnected from this document')
                else:
                    self.ui.printError('Received unknown message_type: ' + str(data['message_type']))
            elif packet['type'] == 'update':
                if 'buffer' in data.keys() and data['name'] != self.name:
                    b_data = data['buffer']
                    currentBuffer = self.ui.getCurrentBuffer()
                    self.prevBuffer = currentBuffer[:b_data['start']] \
                                      + b_data['buffer'] \
                                      + currentBuffer[b_data['end'] - b_data['change_y'] + 1:]
                    self.ui.setCurrentBuffer(self.prevBuffer)
                if 'updated_cursors' in data.keys():
                    # set our own cursor first
                    for updated_user in data['updated_cursors']:
                        if self.name == updated_user['name'] and data['name'] != self.name:
                            oldX, oldY = self.ui.getCursor()
                            if oldX != updated_user['cursor']['x'] or oldY != updated_user['cursor']['y']:
                                self.ui.setCursor(updated_user['cursor']['x'], updated_user['cursor']['y'])

                    # then set others' cursors
                    for updated_user in data['updated_cursors']:
                        if self.name != updated_user['name']:
                            self.cursorManager.updateCursor(updated_user['name'],
                                                            updated_user['cursor']['x'], updated_user['cursor']['y'])
            else:
                self.ui.printError('Received unknown packet type: ' + str(packet['type']))
            self.ui.redraw()

    def send(self, sock, data):
        """
        Send data through a socket
        :param sock: the socket through which data is to be sent
        :param data: the data to be sent
        :return: None
        """
        data = struct.pack('>I', len(data)) + data
        try:
            sock.sendall(data)
        except socket.error:
            self.ui.printError('Socket error occurred when sending')

    def recvall(self, sock, n):
        """
        Helper function to recv n bytes or return None if EOF is hit
        :param sock: the socket through which data is to be received
        :param n: the number of bytes of data to be received
        :return: the received data of length n
        """
        data = ''
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
            except socket.timeout:
                #print('Timeout error occurred when receiving')
                break
            except socket.error:
                print('Socket error occurred when receiving')
                break
            if not packet:
                return None
            data += packet
        return data

class EditorController:
    """
    The collaborative text editor controller
    """
    __slots__ = 'daemonThread', 'runFlag', 'editorModel', 'platform', 'ui'

    def __init__(self):
        """
        Initializer
        """
        self.daemonThread = None
        self.platform = VimPlatform()
        self.ui = VimUI()
        self.editorModel = EditorModel(self, self.ui)
        self.runFlag = False

    def execute(self, arg1=False, arg2=False, arg3=False, arg4=False):
        """
        Execute the collaborative text editor command with the given command line arguments
        :param arg1, arg2, arg3, arg4: command line arguments
        :return: None
        """
        default_name = self.platform.getDefaultName()
        default_name_string = " - default: '" + default_name + "'" if default_name != '0' else ""
        default_port = self.platform.getDefaultPort()
        default_port_string = " - default: " + default_port if default_port != '0' else ""
        if arg1 == 'host':
            # act as a server
            if arg2 and arg3:
                self.editorModel.createServer(arg2, arg3)
            elif arg2 and default_name != '0':
                self.editorModel.createServer(arg2, default_name)
            elif default_port != '0' and default_name != '0':
                self.editorModel.createServer(default_port, default_name)
            else:
                self.ui.printMessage("usage :" + self.platform.getApplicationName() + \
                                     " host [port" + default_port_string + \
                                     "] [name" + default_name_string + "]")
        elif arg1 == 'connect':
            # connect to a server
            if arg2 and arg3 and arg4:
                self.editorModel.connect(arg2, arg3, arg4)
            elif arg2 and arg3 and default_name != '0':
                self.editorModel.connect(arg2, arg3, default_name)
            elif arg2 and default_port != '0' and default_name != '0':
                self.editorModel.connect(arg2, default_port, default_name)
            else:
                self.ui.printMessage("usage :" + self.platform.getApplicationName() + \
                                     " connect [host address / 'localhost'] [port" + \
                                     default_port_string + "] [name" + default_name_string + "]")
        elif arg1 == 'disconnect':
            # disconnect from the server
            self.editorModel.disconnect()
        elif arg1 == 'quit':
            # disconnect from the server and quit
            self.editorModel.disconnect()
            self.ui.quit()
        else:
            self.ui.printMessage("usage: " + self.platform.getApplicationName() + " [share] [connect] [disconnect] [quit]")

    def startDaemonThread(self):
        """
        Start running the daemon thread to send and receive periodic updates
        :return: None
        """
        self.runFlag = True
        self.daemonThread = Thread(target=self.__run)
        self.daemonThread.start()

    def stopDaemonThread(self):
        """
        Stop the daemon thread
        :return: None
        """
        self.runFlag = False
        self.daemonThread.join()

    def __run(self):
        """
        Receives updates from the server and sends periodic updates to the server
        :return: None
        """
        begin = time.time()
        messageLen = None
        data = ''
        while self.runFlag is True:
            # set timeout so as not to block on receiving updates
            self.editorModel.connection.settimeout(0.01)    #10 ms

            # receive updates
            if messageLen is None:
                data = self.editorModel.recvall(self.editorModel.connection, 4)
                if data is None:
                    return
                elif len(data) == 4:
                    messageLen = struct.unpack('>I', data)[0]
            if messageLen is not None:
                data = self.editorModel.recvall(self.editorModel.connection, messageLen)
                if data is None:
                    return
                elif len(data) == messageLen:
                    self.editorModel.processData(data)
                    messageLen = None

            # reset to blocking
            self.editorModel.connection.settimeout(None)

            # send periodic updates
            if time.time() - begin > 0.1:   #100 ms
                self.editorModel.update()
                begin = time.time()

