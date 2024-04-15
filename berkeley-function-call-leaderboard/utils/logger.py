import colorlog
import logging

def setup_logger(level=logging.INFO):
    # Create a logger
    logger_name = logging.getLogger(__name__).name
    logger = logging.getLogger(logger_name)

    # Check if logger already has handlers to prevent adding duplicate handlers
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)  # Set the logging level to DEBUG
        logger.propagate = False

        # Create a console handler
        ch = logging.StreamHandler()
        ch.setLevel(level)

        # Define log format
        log_format = (
            "%(asctime)s - %(module)s - %(levelname)s - %(message)s"
        )
        # Create a formatter with color
        formatter = colorlog.ColoredFormatter(
            "%(log_color)s" + log_format,
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )

        # Set formatter to the console handler
        ch.setFormatter(formatter)
        # Add the console handler to the logger
        logger.addHandler(ch)

        file_handler = logging.FileHandler('log.txt')
        logger.addHandler(file_handler)
    
    return logger

logger = setup_logger(logging.INFO)
# logger = setup_logger(logging.DEBUG)