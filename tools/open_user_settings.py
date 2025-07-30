#!/usr/bin/env python3
"""
Open User Settings Tool

This tool opens the user settings file (user_settings.yaml) in Cursor editor.
Replicates the path logic used by the main application.

Usage:
    python tools/open_user_settings.py
"""

import os
import sys
import subprocess
import platform

def get_user_settings_path():
    """
    Get the user settings file path using the same logic as ConfigManager
    
    Returns:
    - Path to user_settings.yaml file
    """
    # Replicate ConfigManager._get_user_settings_path() logic
    if platform.system() == "Windows":
        # Windows: Use AppData\Roaming
        app_data = os.environ.get('APPDATA')
        if app_data:
            user_settings_dir = os.path.join(app_data, "whisperkey")
        else:
            # Fallback
            user_settings_dir = os.path.expanduser("~/.whisperkey")
    else:
        # Linux/Mac: Use ~/.whisperkey
        user_settings_dir = os.path.expanduser("~/.whisperkey")
    
    return os.path.join(user_settings_dir, "user_settings.yaml")

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

def open_user_settings():
    """
    Open the user settings file in available editor
    """
    try:
        # Get the user settings path
        print("🔍 Locating user settings file...")
        settings_path = get_user_settings_path()
        
        if not os.path.exists(settings_path):
            print(f"❌ User settings file not found: {settings_path}")
            print("💡 Try running the main application first to create the settings file.")
            print("   Run: python whisper-key.py")
            return False
            
        print(f"📁 Found user settings: {settings_path}")
        
        # Find available editor
        print("🔍 Looking for available editor...")
        editor_command, editor_name = find_editor()
        
        print(f"✅ Found editor: {editor_name}")
        
        # Open the file in the editor
        print(f"🚀 Opening user settings in {editor_name}...")
        
        try:
            # Use subprocess to open editor with the settings file
            result = subprocess.run(f'{editor_command} "{settings_path}"', 
                                  shell=True,
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                print(f"✅ User settings opened in {editor_name} successfully!")
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
            print(f"📝 You can manually open: {settings_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """
    Main function
    """
    print("🛠️  Whisper-Key User Settings Opener")
    print("=" * 40)
    
    success = open_user_settings()
    
    if success:
        print("\n🎉 Done! Your user settings should now be open in Cursor.")
        print("💡 Make changes and save the file - they'll take effect on next app restart.")
    else:
        print("\n❌ Failed to open user settings automatically.")
        print("💡 You can find and edit the file manually at the path shown above.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())