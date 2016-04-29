" --------------------------------
" Add our plugin to the path
" --------------------------------
python import sys
python import vim
python sys.path.append(vim.eval('expand("<sfile>:h")'))

" --------------------------------
"  Function(s)
" --------------------------------
function! Execute()
python << endOfPython

###
# Python starts from here.
# Supported: python 2.7
###
from vimCo import *

def main():
    editor = User()
    

if __name__ == "__main__":
   main()
   

endOfPython
endfunction

" --------------------------------
"  Expose our commands to the user
" --------------------------------
command! VimCo call Execute()
