" --------------------------------
" Add our plugin to the path
" --------------------------------
"python import sys
"python import vim
"python sys.path.append(vim.eval('expand("<sfile>:h")'))

com! -nargs=* VimCo py vimCo.start(<f-args>)

" --------------------------------
"  Function(s)
" --------------------------------

function! SetCursorColors ()
    hi CursorUser gui=bold term=bold cterm=bold
    hi Cursor1 ctermbg=DarkRed ctermfg=White guibg=DarkRed guifg=White gui=bold term=bold cterm=bold
    hi Cursor2 ctermbg=DarkBlue ctermfg=White guibg=DarkBlue guifg=White gui=bold term=bold cterm=bold
    hi Cursor3 ctermbg=DarkGreen ctermfg=White guibg=DarkGreen guifg=White gui=bold term=bold cterm=bold
    hi Cursor4 ctermbg=DarkCyan ctermfg=White guibg=DarkCyan guifg=White gui=bold term=bold cterm=bold
    hi Cursor5 ctermbg=DarkMagenta ctermfg=White guibg=DarkMagenta guifg=White gui=bold term=bold cterm=bold
    hi Cursor6 ctermbg=Brown ctermfg=White guibg=Brown guifg=White gui=bold term=bold cterm=bold
    hi Cursor7 ctermbg=LightRed ctermfg=Black guibg=LightRed guifg=Black gui=bold term=bold cterm=bold
    hi Cursor8 ctermbg=LightBlue ctermfg=Black guibg=LightBlue guifg=Black gui=bold term=bold cterm=bold
    hi Cursor9 ctermbg=LightGreen ctermfg=Black guibg=LightGreen guifg=Black gui=bold term=bold cterm=bold
    hi Cursor10 ctermbg=LightCyan ctermfg=Black guibg=LightCyan guifg=Black gui=bold term=bold cterm=bold
    hi Cursor0 ctermbg=LightYellow ctermfg=Black guibg=LightYellow guifg=Black gui=bold term=bold cterm=bold
endfunction



if !exists("VimCo_default_name")
    let VimCo_default_name = 0
endif
if !exists("VimCo_default_port")
    let VimCo_default_port = 0
endif


python << endOfPython

###
# Python starts from here.
# Supported: python 2.7
###
from vimCoClient import *
    vimCo = VimCoClient()

endOfPython
