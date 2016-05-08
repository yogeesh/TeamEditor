import socket
import sys
import select
import json
import struct

class vimServer:

    __slots__ = 'clientList', 'buffer', 'clientManager'
    
    def __init__(self, port):
        self.buffer = []
        self.clientManager = ClientManager(self)

        #Bind to server port and listen
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.bind(("localhost", port))
        serverSocket.listen(10)#supporting max 10 users
        
        self.clientList = [serverSocket]
        self.acceptClients(serverSocket)


    def acceptClients(self, serverSocket):
        """
        Handling multiple clients
        """
        messageLen = None

        while True:
            try:
                readSocket, writeSocket, errorSocket = \
                    select.select(self.clientList, [], [], 300)

                for socket in readSocket:
                    #new socket connection
                    if socket == serverSocket:
                        tempSocket, addr = serverSocket.accept()
                        client = Client(str(tempSocket), self)
                        self.clientManager.addClient(client)
                        print('Client ' + tempSocket + ' joined!')

                        d = {
                            'type': 'message',
                            'data': {
                                'message_type': 'connect_success',
                                'name': str(client.id),
                                'users': self.clientManager.allClientsToJson()
                            }
                        }
                        if self.clientManager.isMulti():
                            d['data']['buffer'] = self.buffer

                        self.send(int(client.id), json.dumps(d))

                        d = {
                            'type': 'message',
                            'data': {
                                'message_type': 'user_connected',
                                'user': self.user.toJson()
                            }
                        }

                        self.broadcastData(int(client.id), d)
                        
                    #existing socket recieving data
                    else:
                        data = self.recvall(socket, 4)
                        if messageLen is None:
                            if len(data) == 4:
                                messageLen = struct.unpack('>I', data)[0]
                                data = ''

                        if messageLen is not None:
                            data = self.recvall(socket, messageLen)
                            if len(data) == messageLen:
                                self.processData(data)
                                data = ''
                                messageLen = None

                    #Checks if all connections are closed
                    if(self.checkOpenSocketConnections()):
                        continue
                    else:
                        return
                    
            except select.error:
                #TODO
                pass


    def broadcastData(self, socketX, data, sendToSelf=False):
        """
        Broadcast data to all clients except clientX
        """
        obj_json = json.dumps(data)
        for id, client in self.clientManager.clients.iteritems():
            sock = int(client.id)
            if sock != socketX or sendToSelf:
                self.send(sock, obj_json)

        """
        #Ignoring 1st socket, as it is dedicated to serverSocket
        for socI in range(1, len(self.clientList)):
            if self.clientList[socI] != socketX:
                self.clientList[socI].sendall(data)
                print "broadcasted!"
        """

    def checkOpenSocketConnections(self):
        return True


    """
    def processRcvdMessage(self, socketX, data):
        print data
        pass

    def recvData(self, socket):
        msgLen = socket.recv(4)
        msgLen = struct.unpack('>I', msgLen)[0]
        return socket.recv(msgLen)

    def createPacket(self, type, data):
        packet = dict()
        packet['type'] = type
        packet['data'] = data
        jSend = json.dumps(packet)
        data = struct.pack('>I', len(jSend)) + jSend
        print data
        return data
    """

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
                packet = sock.recv(n - len(self.data))
            except socket.timeout:
                print('Timeout error occurred when receiving')
            except socket.error:
                print('Socket error occurred when receiving')
                break
            if not packet:
                return None
            data += packet
        print data
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

    def __cleanData(data):
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
            packet['data']['updated_cursors'] = [client.toJson()]
            del packet['data']['cursor']

        if 'buffer' in data.keys():
            b_data = data['buffer']
            self.factory.buffer = self.factory.buffer[:b_data['start']] \
                                    + b_data['buffer'] \
                                    + self.factory.buffer[b_data['end'] - b_data['change_y'] + 1:]
            packet['data']['updated_cursors'] += self.clientManager.updateCursors(b_data, client)
            updateSelf = True
        self.broadcastData(client.id, packet, updateSelf)


class Cursor:
    __slots__ = 'x', 'y'

    def __init__(self):
        self.x = 1
        self.y = 1

    def toJson(self):
        return {
            'x': self.x,
            'y': self.y
        }

class Client:
    __slots__ = 'id', 'server', 'cursor'

    def __init__(self, id, server):
        self.id = id
        self.server = server
        self.cursor = Cursor()

    def toJson(self):
        return {
            'name': self.id,
            'cursor': self.cursor.toJson()
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

    def hasClient(self, id):
        return self.clients.get(id)

    def addClient(self, client):
        self.clients[client.id] = client

    def getClient(self, id):
        try:
            return self.clients[id]
        except KeyError:
            raise Exception('Client ' + id + ' does not exist')

    def removeClient(self, client):
        if self.clients.get(client.id):
            d = {
                'type': 'message',
                'data': {
                    'message_type': 'user_disconnected',
                    'name': client.id
                }
            }
            self.server.broadcastPacket(client.id, d)
            print 'Client "{user_name}" Disconnected'.format(user_name=client.id)
            del self.clients[client.id]

    def allClientsToJson(self):
        return [client.toJson() for client in self.server.clientManager.clients.values()]

    def updateCursors(self, data, c):
        result = []
        y_target = c.cursor.y
        x_target = c.cursor.x

        for client in self.server.clientManager.clients.values():
            updated = False
            if client != c:
                if client.cursor.y > y_target:
                    client.cursor.y += data['change_y']
                    updated = True
                if client.cursor.y == y_target and client.cursor.x > x_target:
                    client.cursor.x = max(1, client.cursor.x + data['change_x'])
                    updated = True
                if client.cursor.y == y_target - 1 and client.cursor.x > x_target \
                    and data['change_y'] == 1:
                    client.cursor.y += 1
                    client.cursor.x = max(1, client.cursor.x + data['change_x'])
                    updated = True
                if updated:
                    result.append(client.toJson())
        return result

        
if __name__ == "__main__":
    vimServer(int(sys.argv[1]))
