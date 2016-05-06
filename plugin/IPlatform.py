from abc import ABCMeta, abstractmethod

class IPlatform(metaclass=ABCMeta):
    @abstractmethod
    def getApplicationName(self):
        pass

    @abstractmethod
    def getDefaultName(self):
        pass

    @abstractmethod
    def getDefaultPort(self):
        pass

    @abstractmethod
    def runServer(self, port):
        pass
