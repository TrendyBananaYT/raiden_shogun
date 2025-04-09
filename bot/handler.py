import datetime
import sys

class LogColors:
    RESET = '\033[0m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'

def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _format(level, color, message, tag=None):
    tag_str = f"[{tag}] " if tag else ""
    return f"{LogColors.BOLD}{color}[{timestamp()}] [{level}]{LogColors.RESET} {tag_str}{message}{LogColors.RESET}"

def debug(message, tag=None):
    print(_format("DEBUG", LogColors.CYAN, message, tag))

def info(message, tag=None):
    print(_format("INFO", LogColors.WHITE, message, tag))

def success(message, tag=None):
    print(_format("SUCCESS", LogColors.GREEN, message, tag))

def warning(message, tag=None):
    print(_format("WARNING", LogColors.YELLOW, message, tag))

def error(message, tag=None):
    print(_format("ERROR", LogColors.RED, message, tag))

def fatal(message, tag=None):
    print(_format("FATAL", LogColors.MAGENTA, message, tag))
    sys.exit(1)  # immediately stop the program

# Example: use this for common minor data issues
def missing_data(detail, tag="DATA"):
    warning(f"Missing or invalid data: {detail}", tag)

def latency_check(latency_ms: float, tag=None):
    """Logs latency with color based on severity."""
    msg = f"Latency: {latency_ms:,.2f} ms"

    if latency_ms < 100:
        success(msg, tag)
    elif latency_ms < 300:
        warning(msg, tag)
    else:
        error(msg, tag)
