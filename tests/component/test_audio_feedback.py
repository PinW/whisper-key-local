#!/usr/bin/env python3
"""
Audio Feedback Test Script

This script tests the audio feedback functionality independently.
It lets you hear what the start/stop sounds are like!

For beginners: This is like testing a doorbell before installing it - 
we want to make sure the sounds work and sound good before using them in the main app.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.audio_feedback import AudioFeedback

def test_basic_functionality():
    """
    Test basic audio feedback functionality
    
    This function demonstrates how our AudioFeedback class works by:
    1. Creating an AudioFeedback instance with default settings
    2. Testing both start and stop sounds
    3. Showing status information
    """
    print("=== Basic Audio Feedback Test ===")
    print("This test will play the default start and stop sounds.")
    print()
    
    try:
        # Create default configuration
        print("1. Creating AudioFeedback with default settings...")
        default_config = {
            'enabled': True,
            'start_sound': {
                'frequency': 800,  # Higher pitch for start
                'duration': 200    # Short beep
            },
            'stop_sound': {
                'frequency': 600,  # Lower pitch for stop  
                'duration': 300    # Longer beep
            }
        }
        
        feedback = AudioFeedback(default_config)
        print("✓ AudioFeedback created successfully!")
        
        # Show status
        status = feedback.get_status()
        print(f"   Enabled: {status['enabled']}")
        print(f"   Windows sound available: {status['winsound_available']}")
        print(f"   Start sound: {status['start_sound']['frequency']}Hz, {status['start_sound']['duration']}ms")
        print(f"   Stop sound: {status['stop_sound']['frequency']}Hz, {status['stop_sound']['duration']}ms")
        print()
        
        if not status['enabled']:
            print("❌ Audio feedback is not enabled (likely not on Windows)")
            return
        
        # Test the sounds
        input("Press Enter to test the sounds...")
        feedback.test_sounds()
        
        print()
        print("✓ Basic test complete!")
        
    except Exception as e:
        print(f"❌ Error during basic test: {e}")

def test_custom_sounds():
    """
    Test audio feedback with custom sound configurations
    
    This shows how different frequencies and durations sound.
    """
    print("\n=== Custom Sound Test ===")
    print("This test will play various custom sound configurations.")
    print()
    
    # Different sound configurations to test
    sound_configs = [
        {
            'name': 'High Pitched (like old computer)',
            'config': {
                'enabled': True,
                'start_sound': {'frequency': 1000, 'duration': 150},
                'stop_sound': {'frequency': 500, 'duration': 400}
            }
        },
        {
            'name': 'Low Pitched (like submarine sonar)',
            'config': {
                'enabled': True,
                'start_sound': {'frequency': 400, 'duration': 250},
                'stop_sound': {'frequency': 300, 'duration': 500}
            }
        },
        {
            'name': 'Quick Beeps (like microwave)',
            'config': {
                'enabled': True,
                'start_sound': {'frequency': 800, 'duration': 100},
                'stop_sound': {'frequency': 800, 'duration': 100}
            }
        }
    ]
    
    try:
        for i, sound_test in enumerate(sound_configs, 1):
            print(f"{i}. Testing: {sound_test['name']}")
            
            feedback = AudioFeedback(sound_test['config'])
            status = feedback.get_status()
            
            if not status['enabled']:
                print("   ❌ Audio feedback not available")
                continue
            
            input(f"   Press Enter to hear '{sound_test['name']}' sounds...")
            
            print("   Playing start sound...")
            feedback.play_start_sound()
            time.sleep(0.8)  # Wait between sounds
            
            print("   Playing stop sound...")
            feedback.play_stop_sound()
            time.sleep(1.0)  # Wait before next test
            
            print("   ✓ Test complete!")
            print()
        
    except Exception as e:
        print(f"❌ Error during custom sound test: {e}")

def test_configuration_changes():
    """
    Test changing configuration at runtime
    
    This shows how settings can be updated without restarting.
    """
    print("=== Configuration Change Test ===")
    print("This test shows how to change settings on the fly.")
    print()
    
    try:
        # Start with one configuration
        initial_config = {
            'enabled': True,
            'start_sound': {'frequency': 600, 'duration': 200},
            'stop_sound': {'frequency': 400, 'duration': 300}
        }
        
        feedback = AudioFeedback(initial_config)
        
        if not feedback.get_status()['enabled']:
            print("❌ Audio feedback not available")
            return
        
        print("1. Initial configuration:")
        print("   Start: 600Hz, 200ms | Stop: 400Hz, 300ms")
        input("   Press Enter to test initial sounds...")
        feedback.test_sounds()
        
        # Update configuration
        new_config = {
            'enabled': True,
            'start_sound': {'frequency': 900, 'duration': 150},
            'stop_sound': {'frequency': 500, 'duration': 400}
        }
        
        print("\n2. Updating configuration...")
        feedback.update_config(new_config)
        print("   New - Start: 900Hz, 150ms | Stop: 500Hz, 400ms")
        input("   Press Enter to test updated sounds...")
        feedback.test_sounds()
        
        # Test enable/disable
        print("\n3. Testing enable/disable...")
        feedback.set_enabled(False)
        print("   Disabled - no sounds should play")
        input("   Press Enter to test (should be silent)...")
        feedback.test_sounds()
        
        feedback.set_enabled(True)
        print("   Re-enabled - sounds should play again")
        input("   Press Enter to test (should make sounds)...")
        feedback.test_sounds()
        
        print("\n✓ Configuration test complete!")
        
    except Exception as e:
        print(f"❌ Error during configuration test: {e}")

def interactive_sound_test():
    """
    Interactive test where you can manually trigger sounds
    
    This simulates what it would be like in the actual app.
    """
    print("\n=== Interactive Sound Test ===")
    print("Manually trigger start/stop sounds like in the real app.")
    print("Commands: 'start' (play start sound), 'stop' (play stop sound), 'quit' (exit)")
    print()
    
    try:
        # Use default configuration
        config = {
            'enabled': True,
            'start_sound': {'frequency': 800, 'duration': 200},
            'stop_sound': {'frequency': 600, 'duration': 300}
        }
        
        feedback = AudioFeedback(config)
        
        if not feedback.get_status()['enabled']:
            print("❌ Audio feedback not available")
            return
        
        print("Audio feedback ready! Try the commands below:")
        
        while True:
            command = input("\nEnter command (start/stop/quit): ").lower().strip()
            
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
    
    For beginners: This script helps you understand what the audio feedback 
    sounds like before integrating it into the main application.
    """
    print("Windows Whisper App - Audio Feedback Test")
    print("=" * 50)
    print("This script tests the sounds that play when recording starts/stops.")
    print("Make sure your speakers/headphones are on!\n")
    
    # Run basic test first
    test_basic_functionality()
    
    # Ask about additional tests
    print("\nWould you like to try different sound styles?")
    response = input("This tests various frequencies and durations (y/n): ").lower()
    if response in ['y', 'yes']:
        test_custom_sounds()
    
    print("\nWould you like to test configuration changes?")
    response = input("This shows how to update settings at runtime (y/n): ").lower()
    if response in ['y', 'yes']:
        test_configuration_changes()
    
    print("\nWould you like to try the interactive test?")
    response = input("This lets you manually trigger start/stop sounds (y/n): ").lower()
    if response in ['y', 'yes']:
        interactive_sound_test()
    
    print("\n" + "=" * 50)
    print("Test complete! You now know what the audio feedback sounds like.")
    print("Next step: integrate this into the main app's state_manager.py")