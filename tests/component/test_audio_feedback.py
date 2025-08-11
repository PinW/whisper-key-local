#!/usr/bin/env python3
"""
Audio Feedback Test Script

This script tests the file-based audio feedback functionality.
It shows how to configure and use sound files for recording events.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.audio_feedback import AudioFeedback

def test_basic_functionality():
    """
    Test basic audio feedback functionality with file paths
    
    This demonstrates how the AudioFeedback class works with sound files.
    """
    print("=== Basic Audio Feedback Test ===")
    print("This test shows how to configure audio feedback with sound files.")
    print()
    
    try:
        # Create configuration with example file paths
        print("1. Testing configuration setup...")
        config = {
            'enabled': True,
            'start_sound': 'assets/sounds/record_start.wav',
            'stop_sound': 'assets/sounds/record_stop.wav'
        }
        
        feedback = AudioFeedback(config)
        print("✓ AudioFeedback created successfully!")
        
        # Show status
        status = feedback.get_status()
        print(f"   Enabled: {status['enabled']}")
        print(f"   Windows sound available: {status['winsound_available']}")
        print(f"   Start sound path: {status['start_sound_path']}")
        print(f"   Stop sound path: {status['stop_sound_path']}")
        print(f"   Start sound exists: {status['start_sound_exists']}")
        print(f"   Stop sound exists: {status['stop_sound_exists']}")
        print()
        
        if not status['enabled']:
            print("❌ Audio feedback is not enabled (likely not on Windows)")
            return
        
        # Test the sounds (will show warnings if files don't exist)
        print("2. Testing sound playback...")
        print("   Note: If sound files don't exist, you'll see warnings in the logs")
        
        print("   Playing start sound...")
        feedback.play_start_sound()
        time.sleep(1.0)
        
        print("   Playing stop sound...")
        feedback.play_stop_sound()
        time.sleep(1.0)
        
        print("   ✓ Sound playback test complete!")
        print("   (Check logs for any file not found warnings)")
        
    except Exception as e:
        print(f"❌ Error during basic test: {e}")

def test_with_missing_files():
    """
    Test behavior when sound files are missing
    
    This shows how the system handles missing files gracefully.
    """
    print("\n=== Missing Files Test ===")
    print("This test shows what happens when sound files don't exist.")
    print()
    
    try:
        # Configuration with non-existent files
        config = {
            'enabled': True,
            'start_sound': 'nonexistent/start.wav',
            'stop_sound': 'nonexistent/stop.wav'
        }
        
        print("1. Testing with non-existent sound files...")
        feedback = AudioFeedback(config)
        
        status = feedback.get_status()
        print(f"   Start sound exists: {status['start_sound_exists']}")
        print(f"   Stop sound exists: {status['stop_sound_exists']}")
        
        if not status['enabled']:
            print("❌ Audio feedback not available")
            return
        
        print("\n2. Attempting to play non-existent sounds...")
        print("   (Should see warnings in logs but not crash)")
        
        feedback.play_start_sound()
        time.sleep(0.5)
        feedback.play_stop_sound()
        time.sleep(0.5)
        
        print("   ✓ Gracefully handled missing files!")
        
    except Exception as e:
        print(f"❌ Error during missing files test: {e}")

def test_configuration_updates():
    """
    Test updating configuration at runtime
    
    This shows how to change sound files without restarting.
    """
    print("\n=== Configuration Update Test ===")
    print("This test shows how to change sound files at runtime.")
    print()
    
    try:
        # Start with one configuration
        initial_config = {
            'enabled': True,
            'start_sound': 'sounds/beep1.wav',
            'stop_sound': 'sounds/beep2.wav'
        }
        
        print("1. Initial configuration...")
        feedback = AudioFeedback(initial_config)
        
        status = feedback.get_status()
        print(f"   Start sound: {status['start_sound_path']}")
        print(f"   Stop sound: {status['stop_sound_path']}")
        
        if not status['enabled']:
            print("❌ Audio feedback not available")
            return
        
        # Update configuration
        new_config = {
            'enabled': True,
            'start_sound': 'assets/new_start.wav',
            'stop_sound': 'assets/new_stop.wav'
        }
        
        print("\n2. Updating configuration...")
        feedback.update_config(new_config)
        
        status = feedback.get_status()
        print(f"   New start sound: {status['start_sound_path']}")
        print(f"   New stop sound: {status['stop_sound_path']}")
        
        # Test enable/disable
        print("\n3. Testing enable/disable...")
        feedback.set_enabled(False)
        print("   Disabled - no sounds should play")
        feedback.play_start_sound()  # Should do nothing
        
        feedback.set_enabled(True)
        print("   Re-enabled - sounds would play again")
        
        print("   ✓ Configuration update test complete!")
        
    except Exception as e:
        print(f"❌ Error during configuration test: {e}")

def test_empty_configuration():
    """
    Test with empty or minimal configuration
    
    This shows how the system handles missing sound file paths.
    """
    print("\n=== Empty Configuration Test ===")
    print("This test shows behavior with missing sound file paths.")
    print()
    
    try:
        # Configuration with no sound files specified
        empty_config = {
            'enabled': True
            # No start_sound or stop_sound specified
        }
        
        print("1. Testing with empty sound file configuration...")
        feedback = AudioFeedback(empty_config)
        
        status = feedback.get_status()
        print(f"   Start sound path: '{status['start_sound_path']}'")
        print(f"   Stop sound path: '{status['stop_sound_path']}'")
        
        if not status['enabled']:
            print("❌ Audio feedback not available")
            return
        
        print("\n2. Attempting to play with empty paths...")
        print("   (Should do nothing silently)")
        
        feedback.play_start_sound()  # Should do nothing
        feedback.play_stop_sound()   # Should do nothing
        
        print("   ✓ Gracefully handled empty configuration!")
        
    except Exception as e:
        print(f"❌ Error during empty configuration test: {e}")

def interactive_test():
    """
    Interactive test for manual sound file testing
    
    This lets you manually trigger sounds if you have sound files available.
    """
    print("\n=== Interactive Test ===")
    print("Manually test audio feedback with your own sound files.")
    print()
    
    try:
        # Get sound file paths from user
        print("Enter paths to sound files (or press Enter to skip):")
        start_sound = input("Start sound file path: ").strip()
        stop_sound = input("Stop sound file path: ").strip()
        
        if not start_sound and not stop_sound:
            print("No sound files provided, skipping interactive test.")
            return
        
        config = {
            'enabled': True,
            'start_sound': start_sound,
            'stop_sound': stop_sound
        }
        
        feedback = AudioFeedback(config)
        status = feedback.get_status()
        
        print(f"\nConfiguration:")
        print(f"  Start sound: {status['start_sound_path']} (exists: {status['start_sound_exists']})")
        print(f"  Stop sound: {status['stop_sound_path']} (exists: {status['stop_sound_exists']})")
        
        if not status['enabled']:
            print("❌ Audio feedback not available")
            return
        
        print("\nCommands: 'start' (play start sound), 'stop' (play stop sound), 'quit' (exit)")
        
        while True:
            command = input("\nEnter command: ").lower().strip()
            
            if command == 'quit':
                print("Goodbye!")
                break
            elif command == 'start':
                print("🎤 Playing recording START sound...")
                feedback.play_start_sound()
            elif command == 'stop':
                print("⏹️  Playing recording STOP sound...")
                feedback.play_stop_sound()
            else:
                print("Unknown command. Use: start, stop, or quit")
    
    except Exception as e:
        print(f"❌ Error in interactive test: {e}")

if __name__ == "__main__":
    """
    This runs when you execute the script directly
    """
    print("Windows Whisper App - File-Based Audio Feedback Test")
    print("=" * 60)
    print("This script tests playing sound files for recording start/stop events.")
    print("Note: Sound files won't exist yet - you'll see warnings, which is normal.\n")
    
    # Run basic test first
    test_basic_functionality()
    
    # Test missing files behavior
    test_with_missing_files()
    
    # Test configuration updates
    test_configuration_updates()
    
    # Test empty configuration
    test_empty_configuration()
    
    # Ask about interactive test
    print("\nWould you like to try the interactive test?")
    print("This lets you test with actual sound files if you have them.")
    response = input("Try interactive test (y/n): ").lower()
    if response in ['y', 'yes']:
        interactive_test()
    
    print("\n" + "=" * 60)
    print("Test complete! The audio feedback system is ready for sound files.")
    print("Next steps:")
    print("1. Create sound files (start.wav, stop.wav)")
    print("2. Update config.defaults.yaml with sound file paths") 
    print("3. Integrate into state_manager.py")