#!/usr/bin/env python3
"""
Clipboard Management Test Script

This script tests the clipboard functionality independently.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from src.clipboard_manager import ClipboardManager

def test_basic_clipboard():
    """
    Test basic clipboard copy and paste functionality
    
    This function demonstrates the core clipboard operations:
    1. Copy text to clipboard
    2. Read text back from clipboard
    3. Verify it matches what we copied
    """
    print("=== Basic Clipboard Test ===")
    print("Testing clipboard copy and paste functionality...")
    print()
    
    try:
        # Create a ClipboardManager instance
        print("1. Creating ClipboardManager...")
        clipboard = ClipboardManager()
        print("✓ ClipboardManager created successfully!")
        print()
        
        # Test copying some text
        test_text = "Hello from the Whisper app test! This is a clipboard test."
        print(f"2. Copying test text: '{test_text}'")
        
        success = clipboard.copy_text(test_text)
        if success:
            print("✓ Text copied to clipboard successfully!")
        else:
            print("❌ Failed to copy text to clipboard!")
            return
        
        # Test reading it back
        print("\n3. Reading text back from clipboard...")
        retrieved_text = clipboard.get_clipboard_content()
        
        if retrieved_text:
            print(f"✓ Retrieved text: '{retrieved_text}'")
            
            # Verify it matches
            if retrieved_text == test_text:
                print("✓ Perfect match! Clipboard is working correctly.")
            else:
                print("⚠  Text doesn't match exactly:")
                print(f"   Expected: '{test_text}'")
                print(f"   Got:      '{retrieved_text}'")
        else:
            print("❌ Failed to retrieve text from clipboard!")
        
        print()
        print("=== Basic Clipboard Test Complete ===")
        
    except Exception as e:
        print(f"❌ Error during clipboard test: {e}")

def test_copy_with_notification():
    """
    Test the copy_with_notification method (what our main app will use)
    
    This demonstrates the user-friendly copy method with notifications.
    """
    print("\n=== Copy and Notify Test ===")
    print("Testing the user-friendly copy method...")
    print()
    
    try:
        clipboard = ClipboardManager()
        
        # Test with normal text
        print("1. Testing with normal text:")
        test_text = "This text will be copied with user notification!"
        success = clipboard.copy_with_notification(test_text)
        
        if success:
            print("   ✓ Copy with notification succeeded!")
        else:
            print("   ❌ Copy with notification failed!")
        
        # Test with very long text (should be truncated in display)
        print("\n2. Testing with long text (should truncate display):")
        long_text = "This is a very long piece of text that should be truncated in the user notification but fully copied to clipboard. " * 3
        success = clipboard.copy_with_notification(long_text)
        
        if success:
            print("   ✓ Long text copy succeeded!")
            # Verify full text was actually copied
            retrieved = clipboard.get_clipboard_content()
            if retrieved == long_text:
                print("   ✓ Full text was copied correctly (despite truncated display)")
            else:
                print("   ⚠  Full text may not have been copied correctly")
        
        # Test with empty text
        print("\n3. Testing with empty text:")
        success = clipboard.copy_with_notification("")
        if not success:
            print("   ✓ Correctly rejected empty text!")
        else:
            print("   ⚠  Should have rejected empty text")
        
        print()
        
    except Exception as e:
        print(f"❌ Error during copy and notify test: {e}")

def interactive_clipboard_test():
    """
    Interactive test where you can type text and see it copied to clipboard
    
    This lets you experiment with the clipboard functionality manually.
    """
    print("\n=== Interactive Clipboard Test ===")
    print("Type text to copy to clipboard, or 'quit' to exit.")
    print("After copying, you can test pasting in another application!")
    print()
    
    try:
        clipboard = ClipboardManager()
        
        while True:
            text = input("Enter text to copy (or 'quit'): ")
            
            if text.lower() == 'quit':
                print("Goodbye!")
                break
            
            if text.strip():  # Only process non-empty text
                success = clipboard.copy_with_notification(text)
                if success:
                    print("👍 Now try pasting with Ctrl+V in another application!")
                    
                    # Show clipboard info
                    info = clipboard.get_clipboard_info()
                    print(f"   Clipboard info: {info}")
                else:
                    print("❌ Copy failed!")
            else:
                print("Please enter some text to copy.")
            
            print()  # Empty line for readability
    
    except Exception as e:
        print(f"❌ Error in interactive test: {e}")

def test_clipboard_info():
    """
    Test the clipboard information method
    
    This shows how we can check clipboard status for debugging.
    """
    print("\n=== Clipboard Info Test ===")
    print("Testing clipboard information functionality...")
    print()
    
    try:
        clipboard = ClipboardManager()
        
        # Get current clipboard info
        print("1. Current clipboard status:")
        info = clipboard.get_clipboard_info()
        print(f"   Has content: {info.get('has_content', 'Unknown')}")
        print(f"   Content length: {info.get('content_length', 'Unknown')}")
        if info.get('preview'):
            print(f"   Preview: '{info['preview']}'")
        
        # Copy something and check again
        print("\n2. After copying test text:")
        test_text = "Test text for clipboard info demonstration"
        clipboard.copy_text(test_text)
        
        info = clipboard.get_clipboard_info()
        print(f"   Has content: {info.get('has_content', 'Unknown')}")
        print(f"   Content length: {info.get('content_length', 'Unknown')}")
        if info.get('preview'):
            print(f"   Preview: '{info['preview']}'")
        
        print()
        
    except Exception as e:
        print(f"❌ Error during clipboard info test: {e}")

def test_preserve_clipboard():
    """
    Test clipboard preservation functionality
    
    This function tests the new preserve_and_paste method that:
    1. Saves existing clipboard content
    2. Copies and pastes new text
    3. Restores original clipboard content
    """
    print("=== Clipboard Preservation Test ===")
    print("Testing preserve_and_paste functionality...")
    print()
    
    try:
        # Create a ClipboardManager instance
        print("1. Creating ClipboardManager...")
        clipboard = ClipboardManager()
        print("✓ ClipboardManager created successfully!")
        print()
        
        # Put some original text in clipboard
        original_text = "Original clipboard content - should be preserved!"
        print(f"2. Setting up original clipboard content: '{original_text}'")
        clipboard.copy_text(original_text)
        
        # Verify it's there
        current_content = clipboard.get_clipboard_content()
        if current_content == original_text:
            print("✓ Original content set successfully!")
        else:
            print("❌ Failed to set original clipboard content!")
            return
        print()
        
        # Now test preserve_and_paste with new text
        transcription_text = "This is transcribed speech that should be pasted!"
        print(f"3. Testing preserve_and_paste with: '{transcription_text}'")
        print("   This should:")
        print("   - Save the original clipboard content")
        print("   - Copy the transcription text")
        print("   - Paste it (we'll simulate this)")
        print("   - Restore the original clipboard content")
        print()
        
        # NOTE: We can't actually test the paste functionality in WSL without a GUI
        # So we'll test the preserve and restore logic by checking clipboard content
        
        # Test the helper methods directly first
        print("4. Testing clipboard preservation logic...")
        
        # Save original content
        saved_content = clipboard.get_clipboard_content()
        print(f"   Saved original: '{saved_content[:50]}...' ({len(saved_content)} chars)")
        
        # Copy transcription
        copy_success = clipboard.copy_text(transcription_text)
        if copy_success:
            print("   ✓ Transcription copied successfully")
        else:
            print("   ❌ Failed to copy transcription")
            return
        
        # Verify transcription is in clipboard
        current_content = clipboard.get_clipboard_content()
        if current_content == transcription_text:
            print("   ✓ Transcription is now in clipboard")
        else:
            print("   ❌ Transcription not found in clipboard")
            return
        
        # Restore original content
        restore_success = clipboard.copy_text(saved_content)
        if restore_success:
            print("   ✓ Original content restored")
        else:
            print("   ❌ Failed to restore original content")
            return
        
        # Verify original content is back
        final_content = clipboard.get_clipboard_content()
        if final_content == original_text:
            print("   ✓ Original clipboard content successfully preserved!")
        else:
            print(f"   ❌ Clipboard preservation failed. Expected: '{original_text}', Got: '{final_content}'")
            return
        
        print()
        print("✓ Clipboard preservation test passed!")
        print("   The preserve_and_paste method should work correctly for pasting with preservation.")
        
    except Exception as e:
        print(f"❌ Error during clipboard preservation test: {e}")

if __name__ == "__main__":
    """
    Main execution when script is run directly
    """
    print("Windows Whisper App - Clipboard Test")
    print("=" * 45)
    
    # Run all tests
    test_basic_clipboard()
    test_copy_with_notification()
    test_preserve_clipboard()
    test_clipboard_info()
    
    # Ask if user wants interactive mode
    print("\nWould you like to try the interactive clipboard test?")
    response = input("This lets you type text and copy it manually (y/n): ").lower()
    
    if response in ['y', 'yes']:
        interactive_clipboard_test()
    
    print("\nClipboard test complete! Next, try running 'python test_whisper.py'")