#!/usr/bin/env python3
"""
Reset User Settings Tool

This tool helps with testing by deleting the user_settings.yaml file from the
Windows AppData directory. This forces the app to recreate user settings from
the default config.yaml on the next run.

For beginners: Think of this as a "factory reset" for your app's settings.
It removes your personal settings so the app will start fresh next time.
"""

import os
import sys
import shutil
from pathlib import Path

def get_user_settings_path():
    """
    Get the path to user settings file in Windows AppData
    
    Same logic as ConfigManager._get_user_settings_path()
    """
    # Get Windows AppData path
    appdata = os.getenv('APPDATA')
    if not appdata:
        # Fallback for non-Windows systems or if APPDATA not set
        home = os.path.expanduser('~')
        appdata = os.path.join(home, 'AppData', 'Roaming')
    
    # Create whisperkey directory path
    whisperkey_dir = os.path.join(appdata, 'whisperkey')
    user_settings_file = os.path.join(whisperkey_dir, 'user_settings.yaml')
    
    return user_settings_file, whisperkey_dir

def backup_user_settings(settings_file, backup_dir=None):
    """
    Create a backup of user settings before deletion
    """
    if not os.path.exists(settings_file):
        return None
    
    if backup_dir is None:
        backup_dir = os.path.dirname(settings_file)
    
    # Create timestamped backup filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"user_settings_backup_{timestamp}.yaml"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        shutil.copy2(settings_file, backup_path)
        return backup_path
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup: {e}")
        return None

def reset_user_settings(create_backup=True):
    """
    Reset user settings by deleting the user_settings.yaml file
    """
    settings_file, settings_dir = get_user_settings_path()
    
    print("🔄 WhisperKey User Settings Reset Tool")
    print("=" * 40)
    print(f"Settings file: {settings_file}")
    print(f"Settings directory: {settings_dir}")
    print()
    
    # Check if settings exist
    if not os.path.exists(settings_file):
        print("✅ No user settings found - nothing to reset!")
        print("The app will create fresh settings on next run.")
        return True
    
    # Create backup if requested
    backup_path = None
    if create_backup:
        print("📋 Creating backup of current settings...")
        backup_path = backup_user_settings(settings_file)
        if backup_path:
            print(f"✅ Backup created: {backup_path}")
        else:
            print("⚠️  Backup failed, but continuing with reset...")
    
    # Delete the settings file
    try:
        os.remove(settings_file)
        print(f"✅ Deleted user settings file: {settings_file}")
        
        # Check if directory is empty and remove it
        if os.path.exists(settings_dir) and not os.listdir(settings_dir):
            # Keep backup files, so only remove if truly empty or only contains backups
            dir_contents = os.listdir(settings_dir)
            if not dir_contents or all(f.startswith('user_settings_backup_') for f in dir_contents):
                if not dir_contents:  # Only remove if completely empty
                    os.rmdir(settings_dir)
                    print(f"✅ Removed empty settings directory: {settings_dir}")
        
        print()
        print("🚀 Reset complete!")
        print("The app will create fresh user settings from config.defaults.yaml on next run.")
        
        if backup_path:
            print(f"💾 Your old settings are backed up at: {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting settings file: {e}")
        return False

def main():
    """
    Main function with command line interface
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reset WhisperKey user settings for testing purposes",
        epilog="This tool is primarily for testing and development."
    )
    parser.add_argument(
        '--no-backup', 
        action='store_true', 
        help='Skip creating a backup of current settings'
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Show confirmation unless --force is used
    if not args.force:
        print("🔄 WhisperKey User Settings Reset Tool")
        print("=" * 40)
        print()
        print("This will delete your personal WhisperKey settings.")
        print("The app will recreate them from the default config on next run.")
        print()
        
        if not args.no_backup:
            print("📋 A backup will be created before deletion.")
        else:
            print("⚠️  No backup will be created (--no-backup specified).")
        
        print()
        response = input("Continue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Reset cancelled.")
            return False
    
    # Perform the reset
    success = reset_user_settings(create_backup=not args.no_backup)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)