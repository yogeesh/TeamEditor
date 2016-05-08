import socket
import sys
import select
import json
import struct

class EditorServer:

    __slots__ = 'socketList', 'buffer', 'clientManager'
    
    def __init__(self, port):
        self.buffer = []
        self.clientManager = ClientManager(self)

        #Bind to server port and listen
        listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listenSocket.bind(("localhost", port))
        listenSocket.listen(10)#supporting max 10 users
        
        self.socketList = [listenSocket]
        self.acceptClients(listenSocket)


    def acceptClients(self, listenSocket):
        """
        Handling multiple clients
        """
        messageLen = None

        while True:
            try:
                readSocket, writeSocket, errorSocket = \
                    select.select(self.socketList, [], [], 300)

                for socket in readSocket:
                    #new socket connection
                    if socket == listenSocket:
                        clientSocket, addr = listenSocket.accept()
                        self.socketList.append(clientSocket)

                        if messageLen is None:
                            data = self.recvall(clientSocket, 4)
                            if len(data) == 4:
                                messageLen = struct.unpack('>I', data)[0]

                        if messageLen is not None:
                            data = self.recvall(clientSocket, messageLen)
                            if len(data) == messageLen:
                                name = str(data)

                                #TODO: validate name

                                client = Client(name, clientSocket, self)
                                self.clientManager.addClient(client)
                                print('Client ' + client.name + ' joined!')

                                d = {
                                    'type': 'message',
                                    'data': {
                                        'message_type': 'connect_success',
                                        'name': client.name,
                                        'users': self.clientManager.allClientsToJson()
                                    }
                                }
                                if self.clientManager.isMulti():
                                    d['data']['buffer'] = self.buffer

                                self.send(client.sock, json.dumps(d))

                                d = {
                                    'type': 'message',
                                    'data': {
                                        'message_type': 'user_connected',
                                        'user': client.to_json()
                                    }
                                }

                                self.broadcastData(client.name, d)

                                messageLen = None
                        
                    #existing socket recieving data
                    else:
                        if messageLen is None:
                            data = self.recvall(socket, 4)
                            if len(data) == 4:
                                messageLen = struct.unpack('>I', data)[0]

                        if messageLen is not None:
                            data = self.recvall(socket, messageLen)
                            if len(data) == messageLen:
                                self.processData(data)
                                messageLen = None

                    #Checks if all connections are closed
                    if(self.checkOpenSocketConnections()):
                        continue
                    else:
                        return
                    
            except select.error:
                #TODO
                pass


    def broadcastData(self, clientX, data, sendToSelf=False):
        """
        Broadcast data to all clients except clientX
        """
        obj_json = json.dumps(data)
        for name, client in self.clientManager.clients.iteritems():
            if client.name != clientX or sendToSelf:
                self.send(client.sock, obj_json)

    def checkOpenSocketConnections(self):
        return True

    def send(self, sock, data):
        # pack length of data along with it
        data = struct.pack('>I', len(data)) + data
        try:
            sock.sendall(data)
        except socket.error:
            print('Socket error occurred when sending')

    def recvall(self, sock, n):
        # Helper function to recv n bytes or return None if EOF is hit
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
        badData = data.find("}{")
        if badData > -1:
            data = data[:badData + 1]
        return data

    def processData(self, data_string):
        data_string = self.__cleanData(data_string)
        packet = self.__toUtf8(json.loads(data_string))

        data = packet['data']
        updateSelf = False

        if 'cursor' in data.keys():
            client = self.clientManager.getClient(data['name'])
            client.updateCursor(data['cursor']['x'], data['cursor']['y'])
            packet['data']['updated_cursors'] = [client.to_json()]
            del packet['data']['cursor']

        if 'buffer' in data.keys():
            b_data = data['buffer']
            self.buffer = self.buffer[:b_data['start']] \
                                    + b_data['buffer'] \
                                    + self.buffer[b_data['end'] - b_data['change_y'] + 1:]
            packet['data']['updated_cursors'] += self.clientManager.updateCursors(b_data, client)
            updateSelf = True
        self.broadcastData(client.name, packet, updateSelf)


class Cursor:
    __slots__ = 'x', 'y'

    def __init__(self):
        self.x = 1
        self.y = 1

    def to_json(self):
        return {
            'x': self.x,
            'y': self.y
        }

class Client:
    __slots__ = 'name', 'sock', 'cursor'

    def __init__(self, name, sock, server):
        self.name = name
        self.sock = sock
        self.cursor = Cursor()

    def to_json(self):
        return {
            'name': self.name,
            'cursor': self.cursor.to_json()
        }

    def updateCursor(self, x, y):
        self.cursor.x = x
        self.cursor.y = y


class ClientManager:
    __slots__ = 'clients', 'server'

    def __init__(self, server):
        self.clients = {}
        self.server = server

    def isEmpty(self):
        return not self.clients

    def isMulti(self):
        return len(self.clients) > 1

    def hasClient(self, name):
        return self.clients.get(name)

    def getClient(self, name):
        try:
            return self.clients[name]
        except KeyError:
            raise Exception('Client ' + name + ' does not exist')

    def addClient(self, client):
        self.clients[client.name] = client

    def removeClient(self, client):
        if self.clients.get(client.name):
            d = {
                'type': 'message',
                'data': {
                    'message_type': 'user_disconnected',
                    'name': client.name
                }
            }
            self.server.broadcastPacket(client.name, d)
            print('Client ' + client.name + ' disconnected')
            del self.clients[client.name]

    def allClientsToJson(self):
        return [client.to_json() for client in self.clients.values()]

    def updateCursors(self, data, c):
        result = []
        y_target = c.cursor.y
        x_target = c.cursor.x

        for client in self.clients.values():
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
                    result.append(client.to_json())
        return result

        
if __name__ == "__main__":
    EditorServer(int(sys.argv[1]))
