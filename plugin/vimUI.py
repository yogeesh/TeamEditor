import vim
from iEditorView import *

class VimUI(IEditorView):
    """
    The vim user interface
    """
    def getCursorX(self):
        return vim.current.window.cursor[1]

    def getCursorY(self):
        return vim.current.window.cursor[0]

    def getCursor(self):
        return vim.current.window.cursor[1], vim.current.window.cursor[0]

    def setCursor(self, x, y):
        vim.current.window.cursor = (y, x)

    def setCursorColors(self):
        vim.command('call SetCursorColors()')

    def getCurrentBuffer(self):
        return vim.current.buffer[:]

    def setCurrentBuffer(self, buffer):
        vim.current.buffer[:] = buffer

    def printError(self, error):
        print('ERROR: ' + str(error))

    def printMessage(self, msg):
        print(msg)

    def redraw(self):
        vim.command(':redraw')

    def quit(self):
        vim.command('q!')

    def getNumberOfCursorColors(self):
        return 11

    def addCursor(self, cursorId, cursorColor, x, y):
        vim.command(':call matchadd(\'' + str(cursorColor) + '\', \'\%' + str(x) + 'v.\%' + str(y) + 'l\', 10, ' + \
                    str(cursorId + 3) + ')')

    def removeCursor(self, cursorId):
        vim.command(':call matchdelete(' + str(cursorId + 3) + ')')

    def updateCursor(self, cursorId, cursorColor, x, y):
        self.removeCursor(cursorId)
        self.addCursor(cursorId, cursorColor, x, y)