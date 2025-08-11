#!/usr/bin/env python3
"""
Clear Model Cache Tool

This tool helps clean up downloaded Whisper model files by deleting the
HuggingFace cache directory. This can free up significant disk space
(models range from 39MB to 1.5GB each).

downloads AI models to your computer, and this tool removes them so they'll
be re-downloaded fresh next time you use the app.
"""

import os
import sys
import shutil
from pathlib import Path

def get_cache_directory():
    """
    Get the path to HuggingFace cache directory on Windows
    
    HuggingFace stores models in %USERPROFILE%\\.cache\\huggingface\\hub\\
    """
    # Get Windows user profile path
    userprofile = os.getenv('USERPROFILE')
    if not userprofile:
        # Fallback for non-Windows systems
        home = os.path.expanduser('~')
        userprofile = home
    
    # HuggingFace cache directory
    cache_dir = os.path.join(userprofile, '.cache', 'huggingface', 'hub')
    
    return cache_dir

def get_directory_size(path):
    """
    Calculate total size of directory in bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception:
        pass  # If we can't access some files, just continue
    return total_size

def format_size(bytes_size):
    """
    Convert bytes to human readable format
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def list_cached_models(cache_dir):
    """
    List all cached models and their sizes
    """
    if not os.path.exists(cache_dir):
        return []
    
    models = []
    try:
        for item in os.listdir(cache_dir):
            model_path = os.path.join(cache_dir, item)
            if os.path.isdir(model_path):
                size = get_directory_size(model_path)
                # Try to extract readable name from folder
                if item.startswith('models--openai--whisper-'):
                    model_name = item.replace('models--openai--whisper-', '')
                elif item.startswith('models--'):
                    model_name = item.replace('models--', '').replace('--', '/')
                else:
                    model_name = item
                
                models.append({
                    'name': model_name,
                    'path': model_path,
                    'size': size,
                    'folder': item
                })
    except Exception:
        pass
    
    return models


def clear_model_cache():
    """
    Clear the HuggingFace model cache directory
    """
    cache_dir = get_cache_directory()
    
    # Check if cache directory exists
    if not os.path.exists(cache_dir):
        print("✅ No model cache found - nothing to clean!")
        print("Models will be downloaded fresh when needed.")
        return True
    
    # List cached models
    models = list_cached_models(cache_dir)
    if not models:
        print("✅ No models found in cache - nothing to clean!")
        return True
    
    # Calculate total size
    total_size = sum(model['size'] for model in models)
    
    print(f"📊 Found {len(models)} cached model(s):")
    for model in models:
        print(f"   • {model['name']}: {format_size(model['size'])}")
    print(f"📏 Total cache size: {format_size(total_size)}")
    print()
    
    
    # Delete the cache directory
    try:
        print("🗑️  Deleting cache directory...")
        shutil.rmtree(cache_dir)
        print(f"✅ Deleted cache directory: {cache_dir}")
        print(f"💾 Freed up: {format_size(total_size)}")
        
        print()
        print("🚀 Cleanup complete!")
        print("Models will be re-downloaded automatically when needed.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deleting cache directory: {e}")
        return False

def main():
    """
    Main function with command line interface
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Clear WhisperKey model cache to free up disk space",
        epilog="This will delete downloaded Whisper models. They'll be re-downloaded when needed."
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Show confirmation unless --force is used
    if not args.force:
        cache_dir = get_cache_directory()
        print("🧹 WhisperKey Model Cache Cleanup Tool")
        print("=" * 45)
        print()
        print("This will delete all downloaded Whisper model files.")
        print(f"Cache directory: {cache_dir}")
        print()
        print("Models will be re-downloaded automatically when needed.")
        print("First-time usage after cleanup may be slower while downloading.")
        
        print()
        response = input("Continue? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("❌ Cleanup cancelled.")
            return False
    
    # Perform the cleanup
    success = clear_model_cache()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)