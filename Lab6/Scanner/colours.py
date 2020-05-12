try:
    import colorama
    colorama.init()
except: pass

FORMAT_ESCAPE_SEQ_SUPPORTED = True

class Colours:
    CLS                = "\033[2J"      # CONSOLE_CLS
    CURSOR             = "\033[H"       # CONSOLE_CURSOR
    RESET              = "\033[0m"      # CONSOLE_RESET

    class Style:
        BOLD           = "\033[1m"      # CONSOLE_BOLD
        UNDERLINE      = "\033[4m"      # CONSOLE_UNDERLINE

    class FG:
        BLACK          = "\033[30m"     # CONSOLE_FG_BLACK
        BRIGHT_BLACK   = "\033[30;1m"   # CONSOLE_FG_BRIGHT_BLACK
        RED            = "\033[31m"     # CONSOLE_FG_RED
        BRIGHT_RED     = "\033[31;1m"   # CONSOLE_FG_BRIGHT_RED
        GREEN          = "\033[32m"     # CONSOLE_FG_GREEN
        BRIGHT_GREEN   = "\033[32;1m"   # CONSOLE_FG_BRIGHT_GREEN
        YELLOW         = "\033[33m"     # CONSOLE_FG_YELLOW
        BRIGHT_YELLOW  = "\033[33;1m"   # CONSOLE_FG_BRIGHT_YELLOW
        BLUE           = "\033[34m"     # CONSOLE_FG_BLUE
        BRIGHT_BLUE    = "\033[34;1m"   # CONSOLE_FG_BRIGHT_BLUE
        MAGENTA        = "\033[35m"     # CONSOLE_FG_MAGENTA
        BRIGHT_MAGENTA = "\033[35;1m"   # CONSOLE_FG_BRIGHT_MAGENTA
        CYAN           = "\033[36m"     # CONSOLE_FG_CYAN
        BRIGHT_CYAN    = "\033[36;1m"   # CONSOLE_FG_BRIGHT_CYAN
        WHITE          = "\033[37m"     # CONSOLE_FG_WHITE
        BRIGHT_WHITE   = "\033[37;1m"   # CONSOLE_FG_BRIGHT_WHITE

    class BG:
        BLACK          = "\033[40m"     # CONSOLE_BG_BLACK
        BRIGHT_BLACK   = "\033[40;1m"   # CONSOLE_BG_BRIGHT_BLACK
        RED            = "\033[41m"     # CONSOLE_BG_RED
        BRIGHT_RED     = "\033[41;1m"   # CONSOLE_BG_BRIGHT_RED
        GREEN          = "\033[42m"     # CONSOLE_BG_GREEN
        BRIGHT_GREEN   = "\033[42;1m"   # CONSOLE_BG_BRIGHT_GREEN
        YELLOW         = "\033[43m"     # CONSOLE_BG_YELLOW
        BRIGHT_YELLOW  = "\033[43;1m"   # CONSOLE_BG_BRIGHT_YELLOW
        BLUE           = "\033[44m"     # CONSOLE_BG_BLUE
        BRIGHT_BLUE    = "\033[44;1m"   # CONSOLE_BG_BRIGHT_BLUE
        MAGENTA        = "\033[45m"     # CONSOLE_BG_MAGENTA
        BRIGHT_MAGENTA = "\033[45;1m"   # CONSOLE_BG_BRIGHT_MAGENTA
        CYAN           = "\033[46m"     # CONSOLE_BG_CYAN
        BRIGHT_CYAN    = "\033[46;1m"   # CONSOLE_BG_BRIGHT_CYAN
        WHITE          = "\033[47m"     # CONSOLE_BG_WHITE
        BRIGHT_WHITE   = "\033[47;1m"   # CONSOLE_BG_BRIGHT_WHITE

def style(text, *args):
    if FORMAT_ESCAPE_SEQ_SUPPORTED:
       return "".join(args) + text + Colours.RESET
    else:
        return text

# Usage:
# print(style("Hello World!", Colours.BG.WHITE, Colours.FG.RED))
