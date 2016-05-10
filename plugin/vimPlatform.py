import vim
from IPlatform import *

# The server path
serverPath = vim.eval('expand("<sfile>:h")') + '/editorServer.py'

class VimPlatform(IPlatform):
    """
    The vim platform
    """
    def getApplicationName(self):
        return "TeamEditor"

    def getDefaultName(self):
        return vim.eval('TeamEditor_default_name')

    def getDefaultPort(self):
        return vim.eval('TeamEditor_default_port')

    def runServer(self, port):
        vim.command(':silent execute "!python ' + serverPath + ' ' + port + ' &>/dev/null &"')
