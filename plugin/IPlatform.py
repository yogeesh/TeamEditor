from abc import ABCMeta, abstractmethod

class IPlatform(object):
    """
    Interface for the platform
    """
    __metaclass__ = ABCMeta

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
