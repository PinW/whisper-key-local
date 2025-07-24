#!/usr/bin/env python3
"""
Isolated PyWhisperCpp Component Test

This script tests pywhispercpp in complete isolation to diagnose boot issues.
Tests basic functionality step by step to identify where the problem occurs.
"""

import sys
import os
import traceback
import numpy as np

def test_import():
    """Test if we can import pywhispercpp"""
    print("=== Import Test ===")
    try:
        from pywhispercpp.model import Model
        print("✓ Successfully imported pywhispercpp.model.Model")
        return True
    except ImportError as e:
        print(f"❌ Failed to import pywhispercpp: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing pywhispercpp: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_model_creation():
    """Test basic Model instantiation"""
    print("\n=== Model Creation Test ===")
    try:
        from pywhispercpp.model import Model
        
        print("Testing Model creation with minimal parameters...")
        model = Model(model="tiny")
        print("✓ Successfully created Model with tiny model")
        
        print("Testing Model creation with n_threads parameter...")
        model_with_threads = Model(model="tiny", n_threads=4)
        print("✓ Successfully created Model with n_threads=4")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create Model: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_model_transcribe():
    """Test basic transcription with dummy audio"""
    print("\n=== Transcription Test ===")
    try:
        from pywhispercpp.model import Model
        
        print("Creating model...")
        model = Model(model="tiny", n_threads=2)
        print("✓ Model created")
        
        print("Creating dummy audio data...")
        # Create simple sine wave as test audio (longer to avoid "too short" warning)
        sample_rate = 16000
        duration = 2.0  # 2 seconds to meet minimum requirement
        frequency = 440  # A note
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        print(f"✓ Created {len(audio_data)} samples of audio data")
        print(f"Audio data shape: {audio_data.shape}")
        print(f"Audio data type: {audio_data.dtype}")
        
        print("Attempting transcription...")
        segments = model.transcribe(audio_data)
        
        print("✓ Transcription completed without errors")
        print(f"Segments type: {type(segments)}")
        print(f"Number of segments: {len(segments)}")
        
        # Try to access segment attributes
        for i, segment in enumerate(segments):
            print(f"Segment {i}: {type(segment)}")
            try:
                print(f"  Text: '{segment.text}'")
                print(f"  Start: {segment.start}")
                print(f"  End: {segment.end}")
            except AttributeError as e:
                print(f"  Segment missing attributes: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcription test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def test_whisper_engine_integration():
    """Test our WhisperEngine class with pywhispercpp"""
    print("\n=== WhisperEngine Integration Test ===")
    try:
        # Add parent directory to path to import our modules
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
        from src.whisper_engine import WhisperEngine
        
        print("Creating WhisperEngine...")
        engine = WhisperEngine(model_size="tiny", n_threads=2)
        print("✓ WhisperEngine created successfully")
        
        # Test with dummy audio
        print("Testing transcription with dummy audio...")
        sample_rate = 16000
        duration = 1.0
        frequency = 440
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        result = engine.transcribe_audio(audio_data, sample_rate)
        print(f"✓ Transcription result: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ WhisperEngine integration test failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all tests in sequence"""
    print("PyWhisperCpp Isolated Component Test")
    print("=" * 50)
    print("This test will help diagnose pywhispercpp boot issues")
    print()
    
    tests = [
        ("Import Test", test_import),
        ("Model Creation Test", test_model_creation),
        ("Transcription Test", test_model_transcribe),
        ("WhisperEngine Integration Test", test_whisper_engine_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print()
    
    # Determine overall result
    if all(results.values()):
        print("🎉 All tests PASSED! pywhispercpp is working correctly.")
        print("The issue may be elsewhere in the main app.")
    else:
        print("⚠️  Some tests FAILED. This indicates a pywhispercpp issue.")
        print("Check the error messages above for clues.")
    
    print()
    print("If tests are failing:")
    print("1. Check that pywhispercpp is properly installed")
    print("2. Try: pip uninstall pywhispercpp && pip install git+https://github.com/absadiki/pywhispercpp")
    print("3. Check Python version compatibility")
    print("4. Verify WSL/Windows environment isn't causing issues")

if __name__ == "__main__":
    main()