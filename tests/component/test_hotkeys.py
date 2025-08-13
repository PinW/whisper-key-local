#!/usr/bin/env python3
"""
Global Hotkey Test Script

This script tests the global hotkey functionality independently.
"""

import sys
import os
import time
import threading
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.hotkey_listener import HotkeyListener

class MockStateManager:
    """
    A fake StateManager for testing hotkeys
    """
    
    def __init__(self):
        self.hotkey_press_count = 0
    
    def toggle_recording(self):
        """
        Fake version of toggle_recording that just prints a message
        """
        self.hotkey_press_count += 1
        print(f"🔥 HOTKEY DETECTED! (Press #{self.hotkey_press_count})")
        print("   In the real app, this would start/stop recording.")
        print("   Press the hotkey again to test multiple presses.")
        print()

def test_hotkey_basic():
    """
    Test basic hotkey functionality
    
    This demonstrates whether global hotkeys work on your system.
    """
    print("=== Basic Hotkey Test ===")
    print("Testing if global hotkeys work on your system...")
    print()
    
    try:
        # Create mock state manager
        print("1. Creating test components...")
        mock_state = MockStateManager()
        
        # Create hotkey listener with default hotkey (Ctrl+Shift+Space)
        print("2. Setting up hotkey listener...")
        print("   Default hotkey: Ctrl+Shift+Space")
        
        hotkey_listener = HotkeyListener(
            state_manager=mock_state,
            recording_hotkey="ctrl+shift+space"
        )
        
        print("✓ Hotkey listener created successfully!")
        print(f"✓ Listening for: {hotkey_listener.recording_hotkey}")
        print()
        
        # Test the hotkey
        print("3. Testing hotkey detection:")
        print("🎯 Now press Ctrl+Shift+Space to test the hotkey!")
        print("   (Make sure this terminal window doesn't need to be focused)")
        print("   You should see a 'HOTKEY DETECTED!' message when you press it.")
        print()
        print("   Press the hotkey a few times to test, then press Enter here to continue...")
        
        input()  # Wait for user to press Enter
        
        # Show results
        if mock_state.hotkey_press_count > 0:
            print(f"✅ SUCCESS! Detected {mock_state.hotkey_press_count} hotkey presses!")
            print("   Global hotkeys are working correctly on your system.")
        else:
            print("❌ No hotkey presses detected.")
            print("   This might indicate:")
            print("   - Hotkey conflicts with other applications")
            print("   - Permission issues (try running as administrator)")
            print("   - Antivirus software blocking global hotkeys")
        
        # Clean up
        hotkey_listener.stop_listening()
        time.sleep(0.5)  # Give it time to stop properly
        print("✓ Hotkey listener stopped")
        
        print()
        print("=== Basic Hotkey Test Complete ===")
        
        return mock_state.hotkey_press_count > 0
        
    except Exception as e:
        print(f"❌ Error during hotkey test: {e}")
        return False

def test_different_hotkeys():
    """
    Test different hotkey combinations to find what works best
    
    Some hotkey combinations might conflict with other applications.
    This test helps find a good hotkey for your system.
    """
    print("\n=== Different Hotkey Combinations Test ===")
    print("Testing various hotkey combinations to find the best one for your system...")
    print()
    
    # List of hotkeys to test
    hotkeys_to_test = [
        "ctrl+shift+space",
        "ctrl+alt+space", 
        "alt+shift+space",
        "ctrl+shift+v",
        "ctrl+alt+v"
    ]
    
    for i, hotkey in enumerate(hotkeys_to_test, 1):
        try:
            print(f"Test {i}: {hotkey}")
            print(f"   Setting up hotkey: {hotkey}")
            
            mock_state = MockStateManager()
            hotkey_listener = HotkeyListener(
                state_manager=mock_state,
                recording_hotkey=hotkey
            )
            
            print(f"   ✓ Listening for: {hotkey}")
            print(f"   🎯 Press {hotkey} now, then press Enter to continue...")
            
            input()  # Wait for user interaction
            
            if mock_state.hotkey_press_count > 0:
                print(f"   ✅ {hotkey} works! ({mock_state.hotkey_press_count} presses detected)")
            else:
                print(f"   ❌ {hotkey} not detected (might conflict with other apps)")
            
            hotkey_listener.stop_listening()
            time.sleep(0.5)  # Give it time to stop properly
            print()
            
        except Exception as e:
            print(f"   ❌ Error with {hotkey}: {e}")
            print()

def test_hotkey_while_using_other_apps():
    """
    Test hotkeys while using other applications
    
    This is the real test - hotkeys should work even when you're in other programs.
    """
    print("\n=== Cross-Application Hotkey Test ===")
    print("Testing hotkeys while using other applications...")
    print("This is the most important test - hotkeys should work everywhere!")
    print()
    
    try:
        mock_state = MockStateManager()
        hotkey_listener = HotkeyListener(
            state_manager=mock_state,
            recording_hotkey="ctrl+shift+space"
        )
        
        print("✓ Hotkey listener active: Ctrl+Shift+Space")
        print()
        print("📋 Instructions:")
        print("1. Open another application (Notepad, Word, browser, etc.)")
        print("2. Click in that application so it has focus")
        print("3. Press Ctrl+Shift+Space while in that application")
        print("4. Come back here and check if it was detected")
        print()
        print("This tests whether hotkeys work globally (the key feature we need)!")
        print()
        
        # Give user time to test
        print("Testing for 30 seconds... Press Ctrl+Shift+Space in different apps!")
        
        start_time = time.time()
        while time.time() - start_time < 30:
            if mock_state.hotkey_press_count == 0:
                remaining = int(30 - (time.time() - start_time))
                print(f"\r⏰ {remaining} seconds remaining... Press the hotkey in any app!", end="")
                time.sleep(1)
            else:
                break
        
        print()  # New line after countdown
        
        if mock_state.hotkey_press_count > 0:
            print(f"🎉 EXCELLENT! Detected {mock_state.hotkey_press_count} hotkey presses from other applications!")
            print("   This means global hotkeys work perfectly for your speech-to-text app!")
        else:
            print("😕 No hotkey presses detected from other applications.")
            print("   This suggests the hotkey might not work globally, which could be due to:")
            print("   - Windows security settings")
            print("   - Antivirus software")
            print("   - Other applications capturing the same hotkey")
            print("   - Administrative permissions needed")
        
        hotkey_listener.stop_listening()
        time.sleep(0.5)  # Give it time to stop properly
        
        print()
        print("=== Cross-Application Test Complete ===")
        
        return mock_state.hotkey_press_count > 0
        
    except Exception as e:
        print(f"❌ Error during cross-application test: {e}")
        return False

def interactive_hotkey_test():
    """
    Interactive test where you can try different hotkeys and see what works
    """
    print("\n=== Interactive Hotkey Test ===")
    print("Try different hotkey combinations interactively!")
    print("Type a hotkey combination to test it, or 'quit' to exit.")
    print()
    print("Examples of hotkey format:")
    print("  ctrl+shift+space")
    print("  alt+shift+v")
    print("  ctrl+alt+d")
    print()
    
    current_listener = None
    mock_state = None
    
    try:
        while True:
            # Stop previous listener if exists
            if current_listener:
                current_listener.stop_listening()
                time.sleep(0.5)  # Give it time to stop
            
            hotkey = input("Enter hotkey to test (or 'quit'): ").lower().strip()
            
            if hotkey == 'quit':
                print("Goodbye!")
                break
            
            if not hotkey:
                print("Please enter a hotkey combination.")
                continue
            
            try:
                print(f"\n🎯 Testing hotkey: {hotkey}")
                
                mock_state = MockStateManager()
                current_listener = HotkeyListener(
                    state_manager=mock_state,
                    recording_hotkey=hotkey
                )
                
                print(f"✓ Now listening for: {hotkey}")
                print("Press the hotkey to test it, then press Enter to try another...")
                
                input()
                
                if mock_state.hotkey_press_count > 0:
                    print(f"✅ {hotkey} works! Detected {mock_state.hotkey_press_count} presses.")
                else:
                    print(f"❌ {hotkey} not detected.")
                
                print()
                
            except Exception as e:
                print(f"❌ Error with '{hotkey}': {e}")
                print("Make sure you use the format: modifier+modifier+key")
                print("Valid modifiers: ctrl, alt, shift")
                print()
    
    except Exception as e:
        print(f"❌ Error in interactive test: {e}")
    
    finally:
        # Clean up
        if current_listener:
            current_listener.stop_listening()

if __name__ == "__main__":
    """
    Main execution when script is run directly
    """
    print("Windows Whisper App - Global Hotkey Test")
    print("=" * 48)
    print()
    print("IMPORTANT: Global hotkeys let you trigger the app from anywhere!")
    print("This is crucial for speech-to-text to work in any application.")
    print()
    
    # Run basic test first
    basic_success = test_hotkey_basic()
    
    if basic_success:
        print("\n🎉 Basic hotkey test passed! Would you like to run more tests?")
        print("1. Test different hotkey combinations")
        print("2. Test hotkeys across different applications (recommended)")
        print("3. Interactive hotkey tester")
        print("4. Skip to integration test")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            test_different_hotkeys()
        elif choice == "2":
            cross_app_success = test_hotkey_while_using_other_apps()
            if cross_app_success:
                print("\n🎉 Perfect! Your system fully supports global hotkeys!")
            else:
                print("\n⚠️  Global hotkeys might need troubleshooting for full functionality.")
        elif choice == "3":
            interactive_hotkey_test()
        elif choice == "4":
            print("Moving on to integration test...")
        else:
            print("Invalid choice, skipping additional tests...")
    
    else:
        print("\n⚠️  Basic hotkey test failed. This needs to be resolved before the main app will work.")
        print("Consider running this test as administrator or checking for hotkey conflicts.")
    
    print("\nHotkey test complete! Next, try running 'python whisper-key.py' to test the full app!")