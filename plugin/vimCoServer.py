import socket
import sys
import select

class vimServer:

    __slots__ = "clientList"
    
    def __init__(self, port):
        #Bind to server port and listen
        serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.bind(("0.0.0.0", port))
        serverSocket.listen(10)#supporting max 10 users
        
        self.clientList = [serverSocket]
        acceptClients()

    def acceptClients():
        """
        Handleling multiple clients
        """
        
        while True:
            try:
                readSocket, writeSocket, errorSocket = \
                    select.select(clientList, [], [], 300)

                for socket in readSocket:
                    #new socket connection
                    if socket == serverSocket:
                        tempSocket, addr = serverSocket.accept()
                        clientList.append(tempSocket)

                    #existing socket recieving data
                    else:
                        data = socket.recv(1024)
                        for clientNum in range(1, len(clientList)+1):
                            if soc == sockeot:
                                processRcvdMessage(clientNum, data)

                    #Checks if all connections are closed
                    if(checkOpenSocketConnections()):
                        continue
                    else:
                        return
                    
            except select.error:
                #TODO
                pass
                
    def processRcvdMessage(clientX, data):
        """
        process the data and brodcast to all clients except clientX
        """
        pass


    def sendData(data, clientX):
        """
        Broadcast data to all clients except clientX
        """
        pass

        
if __name__ == "__main__":
    vimServer(sys.argv[1])
