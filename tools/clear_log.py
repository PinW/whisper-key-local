#!/usr/bin/env python3
"""
Clear Log Tool

This tool clears the application log file to free up disk space and start
with a clean log for troubleshooting.

For beginners: This is like emptying your trash can. The app creates a log
file that records what happens, and this tool clears it when it gets too big
or you want to start fresh for debugging.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from config_manager import ConfigManager
except ImportError:
    # Fallback if config manager isn't available
    ConfigManager = None

def get_log_file_path():
    """
    Get the path to the log file from config or use default
    """
    # Try to get log file path from config
    if ConfigManager:
        try:
            config = ConfigManager()
            log_filename = config.get('logging.file.filename', 'app.log')
            # Get the directory where the tool is located (tools/)
            # Go up one level to get project root
            project_root = Path(__file__).parent.parent
            log_path = project_root / log_filename
            return str(log_path)
        except Exception:
            pass
    
    # Fallback to default
    project_root = Path(__file__).parent.parent
    return str(project_root / 'app.log')

def get_file_size(file_path):
    """
    Get file size in bytes, return 0 if file doesn't exist
    """
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError):
        return 0

def format_size(bytes_size):
    """
    Convert bytes to human readable format
    """
    if bytes_size == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def get_log_info(file_path):
    """
    Get log file information including line count and latest timestamp
    """
    if not os.path.exists(file_path):
        return {"lines": 0, "latest_timestamp": None}
    
    line_count = 0
    latest_timestamp = None
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_count += 1
                # Look for timestamp patterns in the line
                # Common log timestamp formats: 2024-01-28 14:30:25 or similar
                import re
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[\s_T]\d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    latest_timestamp = timestamp_match.group(1)
    except Exception:
        pass  # If we can't read the file, return what we have
    
    return {"lines": line_count, "latest_timestamp": latest_timestamp}

def clear_log_file():
    """
    Clear the application log file
    """
    log_path = get_log_file_path()
    
    # Check if log file exists
    if not os.path.exists(log_path):
        print("✅ No log file found - nothing to clear!")
        print(f"Expected location: {log_path}")
        return True
    
    # Get file info before clearing
    file_size = get_file_size(log_path)
    log_info = get_log_info(log_path)
    
    print(f"📊 Found log file: {os.path.basename(log_path)}")
    print(f"📏 Current size: {format_size(file_size)}")
    print(f"📄 Total lines: {log_info['lines']:,}")
    if log_info['latest_timestamp']:
        print(f"🕒 Latest entry: {log_info['latest_timestamp']}")
    print(f"📁 Location: {log_path}")
    print()
    
    # Clear the log file
    try:
        print("🗑️  Clearing log file...")
        with open(log_path, 'w') as f:
            f.write("")  # Write empty string to clear file
        
        print(f"✅ Cleared log file: {os.path.basename(log_path)}")
        print(f"💾 Freed up: {format_size(file_size)}")
        
        print()
        print("🚀 Log cleanup complete!")
        print("New log entries will be written to the cleared file.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing log file: {e}")
        print("Make sure the application is not running.")
        return False

def main():
    """
    Main function with command line interface
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clear WhisperKey application log file",
        epilog="This will empty the log file but keep it for new entries."
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Show confirmation unless --force is used
    if not args.force:
        log_path = get_log_file_path()
        file_size = get_file_size(log_path)
        log_info = get_log_info(log_path)
        
        print("🧹 WhisperKey Log Cleanup Tool")
        print("=" * 35)
        print()
        print("This will clear the application log file.")
        print(f"Log file: {log_path}")
        if file_size > 0:
            print(f"Current size: {format_size(file_size)}")
            print(f"Total lines: {log_info['lines']:,}")
            if log_info['latest_timestamp']:
                print(f"Latest entry: {log_info['latest_timestamp']}")
        print()
        print("The log file will be emptied but kept for new entries.")
        print("No application data will be lost.")
        
        print()
        response = input("Continue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Log cleanup cancelled.")
            return False
    
    # Perform the cleanup
    success = clear_log_file()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)