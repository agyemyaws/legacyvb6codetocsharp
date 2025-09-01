import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logging(level=logging.INFO, task_name="session"):
    """
    Setup logging configuration for the application.
    
    Args:
        level: Logging level (default: INFO)
        task_name: Task name for auto-generated log file (default: "session")
    """
   
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{task_name}_{timestamp}.log"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    return log_file


if __name__ == "__main__":
    # Simple test
    log_file = setup_logging(level=logging.DEBUG, task_name="test")
    logger = logging.getLogger(__name__)
    logger.info("Logging test completed")
    print(f"Check log file: {log_file}")