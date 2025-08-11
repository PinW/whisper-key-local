#!/usr/bin/env python3
"""
Whisper AI Transcription Test Script

This script tests the Whisper speech-to-text functionality independently.
Great for learning how AI transcription works!

we want to make sure the AI can understand speech and convert it to text correctly.
"""

import sys
import os
import time
import numpy as np
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.whisper_engine import WhisperEngine
from src.audio_recorder import AudioRecorder

def test_whisper_model_loading():
    """
    Test if we can load the Whisper AI model
    
    This is the first step - making sure the AI "brain" loads correctly.
    """
    print("=== Whisper Model Loading Test ===")
    print("Testing if we can load the Whisper AI model...")
    print("Note: First time may take a few minutes to download the model!")
    print()
    
    try:
        print("1. Creating WhisperEngine (this downloads the model if needed)...")
        whisper = WhisperEngine(model_size="tiny")  # Start with smallest/fastest model
        print("✓ WhisperEngine created successfully!")
        
        # Get model information
        model_info = whisper.get_model_info()
        print(f"   Model size: {model_info['model_size']}")
        print(f"   Device: {model_info['device']}")
        print(f"   Compute type: {model_info['compute_type']}")
        print(f"   Model loaded: {model_info['model_loaded']}")
        
        print()
        print("✓ Whisper model is ready for transcription!")
        print("=== Model Loading Test Complete ===")
        
        return whisper
        
    except Exception as e:
        print(f"❌ Error loading Whisper model: {e}")
        print("This might be due to:")
        print("  - Network issues (model download)")
        print("  - Missing faster-whisper library")
        print("  - Insufficient disk space")
        return None

def test_transcription_with_recording():
    """
    Test complete workflow: record audio → transcribe with Whisper
    
    This is like the real app workflow but controlled manually.
    """
    print("\n=== Audio Recording + Transcription Test ===")
    print("This test will record your voice and transcribe it with AI!")
    print()
    
    # First load Whisper
    whisper = test_whisper_model_loading()
    if not whisper:
        print("❌ Cannot proceed without Whisper model!")
        return
    
    try:
        # Create audio recorder
        print("\n2. Creating AudioRecorder...")
        recorder = AudioRecorder()
        print("✓ AudioRecorder ready!")
        
        # Record audio
        print("\n3. Recording Test:")
        input("Press Enter when ready to record for 5 seconds...")
        print()
        
        print("🎤 Recording for 5 seconds... Speak clearly!")
        print("Try saying something like: 'Hello, this is a test of the speech recognition system.'")
        
        recorder.start_recording()
        
        for i in range(5, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        audio_data = recorder.stop_recording()
        
        if audio_data is None:
            print("❌ No audio recorded!")
            return
        
        print(f"✓ Recorded {len(audio_data) / recorder.sample_rate:.2f} seconds of audio")
        
        # Transcribe with Whisper
        print("\n4. Transcribing with Whisper AI...")
        print("🧠 AI is thinking... (this may take a few seconds)")
        
        transcribed_text = whisper.transcribe_audio(audio_data, recorder.sample_rate)
        
        if transcribed_text:
            print(f"✅ Transcription successful!")
            print(f"📝 You said: '{transcribed_text}'")
            print()
            print("How accurate was the transcription?")
            print("✓ Perfect = AI understood everything correctly")
            print("⚠ Good = AI got most words right")
            print("❌ Poor = AI misunderstood many words")
        else:
            print("❌ Transcription failed or no speech detected!")
            print("Try speaking louder or more clearly.")
        
        print()
        print("=== Recording + Transcription Test Complete ===")
        
    except Exception as e:
        print(f"❌ Error during transcription test: {e}")

def test_different_model_sizes():
    """
    Test different Whisper model sizes to compare speed vs accuracy
    
    Bigger models are more accurate but slower.
    """
    print("\n=== Model Size Comparison Test ===")
    print("Comparing different Whisper model sizes...")
    print("Note: This will download multiple models (may take time)")
    print()
    
    models_to_test = ["tiny", "base"]  # Skip "small" for now as it's large
    
    # Create some fake audio for testing (just for demonstration)
    # In a real test, you'd use recorded audio
    sample_rate = 16000
    duration = 2  # 2 seconds
    fake_audio = np.random.normal(0, 0.01, int(sample_rate * duration)).astype(np.float32)
    
    print("Creating test audio data for comparison...")
    print("(Note: This is just noise for demonstration - won't transcribe meaningfully)")
    print()
    
    for model_size in models_to_test:
        try:
            print(f"Testing {model_size} model:")
            
            start_time = time.time()
            whisper = WhisperEngine(model_size=model_size)
            load_time = time.time() - start_time
            
            print(f"   ✓ Loaded in {load_time:.2f} seconds")
            
            # Test transcription speed (though fake audio won't produce real text)
            start_time = time.time()
            result = whisper.transcribe_audio(fake_audio, sample_rate)
            transcribe_time = time.time() - start_time
            
            print(f"   ✓ Transcription took {transcribe_time:.2f} seconds")
            print(f"   📊 Result: {result or 'No text (expected with fake audio)'}")
            print()
            
        except Exception as e:
            print(f"   ❌ Error with {model_size} model: {e}")
            print()

def interactive_transcription_test():
    """
    Interactive test where you can record multiple times
    
    This lets you experiment with different speech patterns and see how well
    the AI understands different types of speech.
    """
    print("\n=== Interactive Transcription Test ===")
    print("Record and transcribe as many times as you want!")
    print("Type 'record' to make a recording, 'quit' to exit.")
    print()
    
    # Load Whisper once
    whisper = WhisperEngine(model_size="tiny")
    recorder = AudioRecorder()
    
    print("✓ System ready for interactive testing!")
    print()
    print("Tips for better transcription:")
    print("  - Speak clearly and at normal pace")
    print("  - Avoid background noise")
    print("  - Try different types of sentences")
    print("  - Test with technical terms, names, numbers")
    print()
    
    try:
        while True:
            command = input("Enter 'record' to transcribe speech, or 'quit' to exit: ").lower().strip()
            
            if command == 'quit':
                print("Goodbye!")
                break
            
            elif command == 'record':
                duration = input("Recording duration in seconds (default 5): ").strip()
                try:
                    duration = int(duration) if duration else 5
                    duration = max(1, min(10, duration))  # Limit between 1-10 seconds
                except ValueError:
                    duration = 5
                
                print(f"\n🎤 Recording for {duration} seconds... Speak now!")
                
                recorder.start_recording()
                
                for i in range(duration, 0, -1):
                    print(f"   {i}...")
                    time.sleep(1)
                
                audio_data = recorder.stop_recording()
                
                if audio_data:
                    print("🧠 Transcribing...")
                    text = whisper.transcribe_audio(audio_data, recorder.sample_rate)
                    
                    if text:
                        print(f"📝 Transcription: '{text}'")
                    else:
                        print("❌ No speech detected")
                else:
                    print("❌ Recording failed")
                
                print()  # Empty line for readability
            
            else:
                print("Unknown command. Use 'record' or 'quit'.")
    
    except Exception as e:
        print(f"❌ Error in interactive test: {e}")

if __name__ == "__main__":
    """
    Main execution when script is run directly
    """
    print("Windows Whisper App - AI Transcription Test")
    print("=" * 50)
    
    # Test model loading first
    whisper = test_whisper_model_loading()
    
    if whisper:
        print("\nWhich test would you like to run?")
        print("1. Record and transcribe test (recommended)")
        print("2. Model size comparison")
        print("3. Interactive transcription test")
        print("4. Skip to next component test")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            test_transcription_with_recording()
        elif choice == "2":
            test_different_model_sizes()
        elif choice == "3":
            interactive_transcription_test()
        elif choice == "4":
            print("Skipping to next test...")
        else:
            print("Invalid choice, running default test...")
            test_transcription_with_recording()
    
    print("\nWhisper test complete! Next, try running 'python test_hotkeys.py'")