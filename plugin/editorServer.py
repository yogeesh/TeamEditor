import socket
import sys
import select
import json
import struct

class EditorServer:
    """
    The server of the collaborative text editor
    """
    __slots__ = 'socketList', 'buffer', 'clientManager'
    
    def __init__(self, port):
        """
        Initializer
        :param port: the port on which the server listens for incoming connection requests
        """
        # Server side copy of the document
        self.buffer = []

        # Manages the clients
        self.clientManager = ClientManager(self)

        # Bind to server port and listen
        listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenSocket.bind(("localhost", port))
        listenSocket.listen(10)

        # List of sockets whose states have to be checked
        self.socketList = [listenSocket]

        # Start accepting clients
        self.acceptClients(listenSocket)

    def acceptClients(self, listenSocket):
        """
        Accepts clients and handles their messages
        :param listenSocket the socket on server to listen for connection requests
        :return: None
        """
        messageLen = None
        while True:
            try:
                readSockets, writeSockets, errorSockets = select.select(self.socketList, [], [], 300)

                # for sockets that are in read state
                for socket in readSockets:
                    # new connection request from a client on the listen socket
                    if socket == listenSocket:
                        clientSocket, addr = listenSocket.accept()
                        self.socketList.append(clientSocket)

                        # receive client's name
                        if messageLen is None:
                            data = self.recvall(clientSocket, 4)
                            if data is not None and len(data) == 4:
                                messageLen = struct.unpack('>I', data)[0]
                        if messageLen is not None:
                            data = self.recvall(clientSocket, messageLen)
                            if data is not None and len(data) == messageLen:
                                name = str(data)

                                #TODO: validate name

                                client = Client(name, clientSocket, self)
                                self.clientManager.addClient(client)
                                print('Client ' + client.name + ' joined!')

                                # give the current buffer and other client info to this new client
                                d = {
                                    'type': 'message',
                                    'data': {
                                        'message_type': 'connect_success',
                                        'name': client.name,
                                        'users': self.clientManager.allClientsToDict()
                                    }
                                }
                                if self.clientManager.isMulti():
                                    d['data']['buffer'] = self.buffer

                                self.send(client.sock, json.dumps(d))

                                # broadcast to other clients about this new client
                                d = {
                                    'type': 'message',
                                    'data': {
                                        'message_type': 'user_connected',
                                        'user': client.toDict()
                                    }
                                }

                                self.broadcastData(client.name, json.dumps(d))

                                messageLen = None
                        
                    # incoming data from clients
                    else:
                        # get incoming data
                        if messageLen is None:
                            data = self.recvall(socket, 4)
                            if data is None:
                                # EOF received. Broadcast to other clients about this client having disconnected
                                client = self.clientManager.getClientBySock(socket)
                                d = {
                                    'type': 'message',
                                    'data': {
                                        'message_type': 'user_disconnected',
                                        'name': client.name
                                    }
                                }
                                self.broadcastData(client.name, json.dumps(d))
                                print('Client ' + client.name + ' left')

                                # remove the client from client manager and socket list
                                self.clientManager.removeClient(client)
                                if socket in self.socketList: self.socketList.remove(socket)

                                # exit if all clients have disconnected
                                if len(self.socketList) == 1: return
                            elif len(data) == 4:
                                messageLen = struct.unpack('>I', data)[0]
                        if messageLen is not None:
                            data = self.recvall(socket, messageLen)
                            if data is None:
                                # EOF received. Broadcast to other clients about this client having disconnected
                                client = self.clientManager.getClientBySock(socket)
                                d = {
                                    'type': 'message',
                                    'data': {
                                        'message_type': 'user_disconnected',
                                        'name': client.name
                                    }
                                }
                                self.broadcastData(client.name, json.dumps(d))
                                print('Client ' + client.name + ' left')

                                # remove the client from client manager and socket list
                                self.clientManager.removeClient(client)
                                if socket in self.socketList: self.socketList.remove(socket)

                                # exit if all clients have disconnected
                                if len(self.socketList) == 1: return
                            elif len(data) == messageLen:
                                # process the data
                                self.processData(data)
                                messageLen = None
                    
            except select.error:
                #TODO
                print('Socket error')

    def broadcastData(self, clientX, data, sendToClientX=False):
        """
        Broadcast data to all clients on behalf of clientX
        :param clientX: the client whose data is being sent to other clients
        :param data: the data to be sent
        :param sendToSelf: whether to send to clientX or not
        :return: None
        """
        for name, client in self.clientManager.clientsByName.iteritems():
            if client.name != clientX or sendToClientX:
                self.send(client.sock, data)

    def send(self, sock, data):
        """
        Send data through a socket
        :param sock: the socket through which data is to be sent
        :param data: the data to be sent
        :return: None
        """
        # pack length of data along with it
        data = struct.pack('>I', len(data)) + data
        try:
            sock.sendall(data)
        except socket.error:
            print('Socket error occurred when sending')

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

        data = packet['data']
        updateSelf = False

        if 'cursor' in data.keys():
            # cursor update from the client
            client = self.clientManager.getClientByName(data['name'])
            client.updateCursor(data['cursor']['x'], data['cursor']['y'])
            packet['data']['updated_cursors'] = [client.toDict()]
            del packet['data']['cursor']

        if 'buffer' in data.keys():
            # buffer update from the client
            b_data = data['buffer']
            self.buffer = self.buffer[:b_data['start']] \
                                    + b_data['buffer'] \
                                    + self.buffer[b_data['end'] - b_data['change_y'] + 1:]
            # update all clients' cursors based on the new buffer
            packet['data']['updated_cursors'] += self.clientManager.updateCursors(b_data, client)
            updateSelf = True
        self.broadcastData(client.name, json.dumps(packet), updateSelf)


class Cursor:
    """
    The cursor
    """
    __slots__ = 'x', 'y'

    def __init__(self):
        """
        Initializer
        """
        self.x = 1
        self.y = 1

    def toDict(self):
        """
        Convert to a dictionary
        :return: a dictionary containing the cursor information
        """
        return {
            'x': self.x,
            'y': self.y
        }

class Client:
    """
    The client
    """
    __slots__ = 'name', 'sock', 'cursor'

    def __init__(self, name, sock):
        """
        Initializer
        :param name: the name of the client
        :param sock: the client socket
        """
        self.name = name
        self.sock = sock
        self.cursor = Cursor()

    def toDict(self):
        """
        Convert to a dictionary
        :return: a dictionary containing the client information
        """
        return {
            'name': self.name,
            'cursor': self.cursor.toDict()
        }

    def updateCursor(self, x, y):
        """
        Update the client's cursor
        :param x: column number
        :param y: row number
        :return: None
        """
        self.cursor.x = x
        self.cursor.y = y


class ClientManager:
    """
    The client manager
    """
    __slots__ = 'clientsByName', 'clientsBySock'

    def __init__(self, server):
        """
        Initializer
        """
        # Dictionary mapping clients by their sockets
        self.clientsBySock = {}
        # Dictionary mapping clients by their names
        self.clientsByName = {}

    def isEmpty(self):
        """
        Checks if there are any clients connected
        :return: True if no clients, False otherwise
        """
        return not self.clientsByName

    def isMulti(self):
        """
        Checks if there is more than one client connected
        :return: True if more than one client, False otherwise
        """
        return len(self.clientsByName) > 1

    def hasClientByName(self, name):
        """
        Checks if there is a client by the given name connected
        :param name: the name of the client to be found
        :return: True if present, False otherwise
        """
        return self.clientsByName.get(name)

    def getClientByName(self, name):
        """
        Gets the client of given name
        :param name: the name of the client to be got
        :return: the client of given name if present
        """
        try:
            return self.clientsByName[name]
        except KeyError:
            raise Exception('Client ' + name + ' does not exist')

    def hasClientBySock(self, sock):
        """
        Checks if there is a client by the given socket connected
        :param sock: the socket of the client to be found
        :return: True if present, False otherwise
        """
        return self.clientsBySock.get(sock)

    def getClientBySock(self, sock):
        """
        Gets the client of given socket
        :param sock: the socket of the client to be got
        :return: the client of given socket if present
        """
        try:
            return self.clientsBySock[sock]
        except KeyError:
            raise Exception('Client does not exist')

    def addClient(self, client):
        """
        Adds the client to the list of connected clients
        :param client: the new client
        :return: None
        """
        self.clientsByName[client.name] = client
        self.clientsBySock[client.sock] = client

    def removeClient(self, client):
        """
        Removes the client from the list of connected clients
        :param client: the new client
        :return: None
        """
        if self.clientsByName.get(client.name):
            del self.clientsByName[client.name]
            del self.clientsBySock[client.sock]

    def allClientsToDict(self):
        """
        Convert all client information to a list of dictionary data
        :return: the list of clients converted to dictionary form
        """
        return [client.toDict() for client in self.clientsByName.values()]

    def updateCursors(self, data, c):
        """
        Update all client cursors according to the received buffer information
        :param data: the received data
        :param c: the client from which the data was received
        :return: the updated list of client information
        """
        result = []
        y_target = c.cursor.y
        x_target = c.cursor.x

        for client in self.clientsByName.values():
            updated = False
            if client != c:
                if client.cursor.y > y_target:
                    client.cursor.y += data['change_y']
                    updated = True
                if client.cursor.y == y_target and client.cursor.x > x_target:
                    client.cursor.x = max(1, client.cursor.x + data['change_x'])
                    updated = True
                if client.cursor.y == y_target - 1 and client.cursor.x > x_target and data['change_y'] == 1:
                    client.cursor.y += 1
                    client.cursor.x = max(1, client.cursor.x + data['change_x'])
                    updated = True
                if updated:
                    result.append(client.toDict())
        return result


if __name__ == "__main__":
    EditorServer(int(sys.argv[1]))
