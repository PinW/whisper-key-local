#!/usr/bin/env python3
"""
Audio Recording Test Script

This script tests the audio recording functionality independently.
It's great for learning how the AudioRecorder class works!

to make sure it can record sound properly before using it in the main app.
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.audio_recorder import AudioRecorder

def test_audio_recording():
    """
    Test the audio recording functionality
    
    This function demonstrates how our AudioRecorder class works by:
    1. Creating an AudioRecorder instance
    2. Recording for a few seconds
    3. Showing information about what was recorded
    """
    print("=== Audio Recording Test ===")
    print("This test will record audio for 3 seconds to verify your microphone works.")
    print()
    
    try:
        # Create an AudioRecorder instance
        print("1. Creating AudioRecorder...")
        recorder = AudioRecorder()
        print("✓ AudioRecorder created successfully!")
        print(f"   Sample rate: {recorder.sample_rate} Hz")
        print(f"   Channels: {recorder.channels}")
        print()
        
        # Test recording
        input("Press Enter to start 3-second recording test...")
        print()
        
        print("2. Starting recording...")
        success = recorder.start_recording()
        
        if not success:
            print("❌ Failed to start recording!")
            return
        
        print("🎤 Recording for 3 seconds... Speak now!")
        
        # Record for 3 seconds
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        print("3. Stopping recording...")
        audio_data = recorder.stop_recording()
        
        if audio_data is None:
            print("❌ No audio data was recorded!")
            return
        
        # Show information about the recorded audio
        print("✓ Recording completed!")
        print(f"   Recorded {len(audio_data)} audio samples")
        print(f"   Duration: {len(audio_data) / recorder.sample_rate:.2f} seconds")
        print(f"   Audio data type: {audio_data.dtype}")
        print(f"   Audio data shape: {audio_data.shape}")
        
        # Check if we actually recorded something (not just silence)
        audio_level = abs(audio_data).mean()
        print(f"   Average audio level: {audio_level:.6f}")
        
        if audio_level > 0.001:
            print("✓ Audio detected! Your microphone is working.")
        else:
            print("⚠  Very low audio level detected. Check your microphone volume.")
        
        print()
        print("=== Audio Test Complete ===")
        print("If you saw audio detected, your microphone is working correctly!")
        
    except Exception as e:
        print(f"❌ Error during audio test: {e}")
        print("This might indicate a microphone or audio system issue.")

def interactive_recording_test():
    """
    Interactive test where you control when to start/stop recording
    
    This is more like the real app experience where you control the recording.
    """
    print("\n=== Interactive Recording Test ===")
    print("You can start and stop recording manually.")
    print("Type 'start' to begin recording, 'stop' to end, 'quit' to exit.")
    print()
    
    try:
        recorder = AudioRecorder()
        
        while True:
            command = input("Enter command (start/stop/quit): ").lower().strip()
            
            if command == 'quit':
                if recorder.get_recording_status():
                    recorder.stop_recording()
                print("Goodbye!")
                break
            
            elif command == 'start':
                if recorder.get_recording_status():
                    print("Already recording! Use 'stop' first.")
                else:
                    success = recorder.start_recording()
                    if success:
                        print("🎤 Recording started! Say something...")
                    else:
                        print("❌ Failed to start recording!")
            
            elif command == 'stop':
                if not recorder.get_recording_status():
                    print("Not currently recording! Use 'start' first.")
                else:
                    audio_data = recorder.stop_recording()
                    if audio_data is not None:
                        duration = len(audio_data) / recorder.sample_rate
                        level = abs(audio_data).mean()
                        print(f"✓ Recording stopped! Duration: {duration:.2f}s, Level: {level:.6f}")
                    else:
                        print("❌ No audio data recorded!")
            
            else:
                print("Unknown command. Use: start, stop, or quit")
    
    except Exception as e:
        print(f"❌ Error in interactive test: {e}")

if __name__ == "__main__":
    """
    This runs when you execute the script directly
    
    "only run this code if this file is executed directly, not imported"
    """
    print("Windows Whisper App - Audio Recording Test")
    print("=" * 50)
    
    # Run the basic test first
    test_audio_recording()
    
    # Ask if user wants to try interactive mode
    print("\nWould you like to try the interactive recording test?")
    response = input("This lets you control start/stop manually (y/n): ").lower()
    
    if response in ['y', 'yes']:
        interactive_recording_test()
    
    print("\nTest complete! Next, try running 'python test_clipboard.py'")