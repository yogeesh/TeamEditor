from abc import ABCMeta, abstractmethod

class IEditorView(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def getCursorX(self):
        pass

    @abstractmethod
    def getCursorY(self):
        pass

    @abstractmethod
    def getCursor(self):
        pass

    @abstractmethod
    def setCursor(self, x, y):
        pass

    @abstractmethod
    def setCursorColors(self):
        pass

    @abstractmethod
    def getCurrentBuffer(self):
        pass

    @abstractmethod
    def setCurrentBuffer(self, buffer):
        pass

    @abstractmethod
    def printError(self, error):
        pass

    @abstractmethod
    def printMessage(self, msg):
        pass

    @abstractmethod
    def redraw(self):
        pass

    @abstractmethod
    def quit(self):
        pass

    @abstractmethod
    def getNumberOfCursorColors(self):
        pass

    @abstractmethod
    def addCursor(self, cursorId, cursorColor, x, y):
        pass

    @abstractmethod
    def removeCursor(self, cursorId):
        pass

    @abstractmethod
    def updateCursor(self, cursorId, cursorColor, x, y):
        pass