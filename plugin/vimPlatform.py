import vim
from IPlatform import *

# Find the server path
VimCoServerPath = vim.eval('expand("<sfile>:h")') + '/vimCoServer.py'

class VimPlatform(IPlatform):
    def getApplicationName(self):
        return "VimCo"

    def getDefaultName(self):
        return vim.eval('VimCo_default_name')

    def getDefaultPort(self):
        return vim.eval('VimCo_default_port')

    def runServer(self, port):
        print('running server')
        print(VimCoServerPath)
        vim.command(':silent execute "!' + VimCoServerPath + ' ' + port + ' &>/dev/null &"')
