"Helper function for colored terminal outputs"
import shutil


MIN_LINE_LENGTH = 20
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)

CROSS = u'\u2717'
TICK = u'\u2713'


def colorify(message, color=BLUE):
    """Change color of the standard output.

    Parameters
    ----------
    message : str
        The message to color.

    Returns
    -------
    color_message : str
        The colored message to be displayed in terminal.
    """
    return f"\033[1;{color}m" + message + "\033[0m"


def print_normalize(msg, endline=True):
    """Format the output to have the length of the terminal."""
    line_length = max(
        MIN_LINE_LENGTH, shutil.get_terminal_size((100, 24)).columns
    )
    n_colors = msg.count('\033') // 2
    msg = msg.ljust(line_length + n_colors * 11)

    if endline:
        print(msg)
    else:
        print(msg + '\r', end='', flush=True)
