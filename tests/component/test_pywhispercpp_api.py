#!/usr/bin/env python3
"""
Test to understand pywhispercpp return format
"""

import numpy as np

def test_return_format():
    """Test what pywhispercpp.transcribe actually returns"""
    try:
        from pywhispercpp.model import Model
        
        print("Creating model...")
        model = Model(model="tiny")
        
        print("Creating test audio...")
        sample_rate = 16000
        duration = 1.0
        frequency = 440
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t).astype(np.float32)
        
        print("Calling transcribe...")
        result = model.transcribe(audio_data)
        
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        # Try to unpack as (segments, info)
        try:
            segments, info = result
            print("✓ Successfully unpacked as (segments, info)")
            print(f"Segments type: {type(segments)}")
            print(f"Info type: {type(info)}")
        except (ValueError, TypeError) as e:
            print(f"❌ Cannot unpack as (segments, info): {e}")
            
            # Maybe it's just segments?
            try:
                segments = list(result)
                print(f"✓ Treating result as segments list, got {len(segments)} segments")
                for i, segment in enumerate(segments):
                    print(f"  Segment {i}: {type(segment)}")
                    if hasattr(segment, 'text'):
                        print(f"    Text: {segment.text}")
            except Exception as e2:
                print(f"❌ Cannot treat as segments: {e2}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_return_format()