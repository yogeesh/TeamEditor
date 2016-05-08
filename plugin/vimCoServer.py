import socket
import sys
import select
import json
import struct
import argparse

parser = argparse.ArgumentParser(description='Start a VimCo server')
parser.add_argument('port', type=int, nargs='?', default=8555,
                    help='Port number to run on')

class vimServer:

    __slots__ = "clientList"
    
    def __init__(self, port):
        #Bind to server port and listen
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.bind(("localhost", port))
        serverSocket.listen(10)#supporting max 10 users
        
        self.clientList = [serverSocket]
        self.acceptClients(serverSocket)

    def acceptClients(self, serverSocket):
        """
        Handleling multiple clients
        """
        
        while True:
            try:
                readSocket, writeSocket, errorSocket = \
                    select.select(self.clientList, [], [], 300)

                for socket in readSocket:
                    #new socket connection
                    if socket == serverSocket:
                        tempSocket, addr = serverSocket.accept()
                        self.clientList.append(tempSocket)
                        print "Client joined!"
                        name = self.recvData(tempSocket)
                        print "%s joined\n"%name
                        
                        #populating data for broadcast
                        data = dict()
                        data["message_type"] = "user_connected"
                        data["user"] = {"name" : name}
                        sendData = self.createPacket('message', data)
                        self.boardcastData(data=sendData, \
                                           socketX=tempSocket)
                        
                    #existing socket recieving data
                    else:
                        data = recvData(socket)
                        self.processRcvdMessage(socket, data)

                    #Checks if all connections are closed
                    if(self.checkOpenSocketConnections()):
                        continue
                    else:
                        return
                    
            except select.error:
                #TODO
                pass
                
    def processRcvdMessage(self, socketX, data):
        """
        Message was received from SocketX.
        Message contents: data
        """
        print data
        pass


    def boardcastData(self, data, socketX):
        """
        Broadcast data to all clients except clientX
        """
        #Ignoring 1st socket, as it is dedicated to serverSocket
        for socI in range(1, len(self.clientList)):
            if self.clientList[socI] != socketX:
                self.clientList[socI].sendall(data)
                print "broadcasted!"


    def recvData(self, socket):
        msgLen = socket.recv(4)
        msgLen = struct.unpack('>I', msgLen)[0]
        return socket.recv(msgLen)
        
    def checkOpenSocketConnections(self):
        return True


    def createPacket(self, type, data):
        packet = dict()
        packet['type'] = type
        packet['data'] = data
        jSend = json.dumps(packet)
        data = struct.pack('>I', len(jSend)) + jSend
        print data
        return data

        
if __name__ == "__main__":
    args = parser.parse_args()
    server = vimServer(args.port)
