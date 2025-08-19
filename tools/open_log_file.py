#!/usr/bin/env python3
"""
Open Log File Tool

This tool opens the application log file (app.log) in an editor.
Uses the same path logic as the main application.

Usage:
    python tools/open_log_file.py
"""

import os
import sys
import subprocess
import platform

def get_log_file_path():
    """
    Get the log file path using the same logic as the main application
    
    Returns:
    - Path to app.log file
    """
    # Replicate get_user_app_data_path() logic
    if platform.system() == "Windows":
        # Windows: Use AppData\Roaming
        app_data = os.environ.get('APPDATA')
        if app_data:
            whisperkey_dir = os.path.join(app_data, "whisperkey")
        else:
            # Fallback
            whisperkey_dir = os.path.expanduser("~/.whisperkey")
    else:
        # Linux/Mac: Use ~/.whisperkey
        whisperkey_dir = os.path.expanduser("~/.whisperkey")
    
    return os.path.join(whisperkey_dir, "app.log")

def find_editor():
    """
    Find available editor in order of preference: cursor -> code -> notepad
    
    Returns:
    - tuple of (command, name) if found, ('notepad', 'Notepad') as fallback
    """
    editors = [
        ('cursor -v', 'cursor', 'Cursor'),
        ('code --version', 'code', 'VS Code'),
    ]
    
    for version_cmd, command, name in editors:
        try:
            result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
            if (result.returncode == 0 and 
                result.stdout.strip() and 
                "is not recognized as the name of a cmdlet" not in result.stderr):
                return command, name
        except:
            continue
    
    # Fallback to notepad (always available on Windows)
    return 'notepad', 'Notepad'

def open_log_file():
    """
    Open the log file in available editor
    """
    try:
        # Get the log file path
        print("🔍 Locating application log file...")
        log_path = get_log_file_path()
        
        if not os.path.exists(log_path):
            print(f"❌ Log file not found: {log_path}")
            print("💡 Try running the main application first to create the log file.")
            print("   Run: python whisper-key.py")
            return False
            
        print(f"📁 Found log file: {log_path}")
        
        # Find available editor
        print("🔍 Looking for available editor...")
        editor_command, editor_name = find_editor()
        
        print(f"✅ Found editor: {editor_name}")
        
        # Open the file in the editor
        print(f"🚀 Opening log file in {editor_name}...")
        
        try:
            # Use subprocess to open editor with the log file
            result = subprocess.run(f'{editor_command} "{log_path}"', 
                                  shell=True,
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                print(f"✅ Log file opened in {editor_name} successfully!")
                return True
            else:
                print(f"⚠️  {editor_name} returned code {result.returncode}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                print(f"💡 The file might still have opened - check {editor_name}.")
                return True  # Editor often returns non-zero but still works
                
        except subprocess.TimeoutExpired:
            print(f"✅ {editor_name} launched (timed out waiting for response - this is normal)")
            return True
            
        except Exception as e:
            print(f"❌ Failed to launch {editor_name}: {e}")
            print(f"📝 You can manually open: {log_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """
    Main function
    """
    print("🛠️  Whisper-Key Log File Opener")
    print("=" * 40)
    
    success = open_log_file()
    
    if success:
        print("\n🎉 Done! Your log file should now be open in the editor.")
        print("💡 Use this to check for errors or debug application behavior.")
    else:
        print("\n❌ Failed to open log file automatically.")
        print("💡 You can find and view the file manually at the path shown above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())