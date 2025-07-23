#!/usr/bin/env python3
"""
Test Runner for Windows Whisper App

This script makes it easy to run all the component tests in the right order.
Perfect for beginners to understand how each part works!

For beginners: This is like a "test suite" - it runs all our individual tests
in a logical order to make sure everything works before using the full app.
"""

import sys
import subprocess
import os

def print_header(title):
    """Print a nice header for each test section"""
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)
    print()

def run_python_script(script_name, description):
    """
    Run a Python script and handle any errors
    
    This is a helper function that runs each test script and shows the results.
    """
    print(f"🚀 Running {script_name}...")
    print(f"📋 Test: {description}")
    print()
    
    try:
        # Check if script exists
        if not os.path.exists(script_name):
            print(f"❌ Error: {script_name} not found!")
            return False
        
        # Run the script
        print(f"▶️  Executing: python {script_name}")
        print("-" * 40)
        
        # Use subprocess to run the script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False,  # Show output in real-time
                              text=True)
        
        print("-" * 40)
        
        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully!")
        else:
            print(f"❌ {script_name} failed with exit code {result.returncode}")
            return False
        
        print()
        return True
        
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        print()
        return False

def main():
    """
    Main test runner function
    
    This runs all our component tests in the recommended order.
    """
    print_header("Windows Whisper App - Component Test Suite")
    
    print("🎯 This test runner will check all components of your speech-to-text app!")
    print("📚 Each test teaches you how a different part works.")
    print("⏱️  Take your time and read the explanations - this is for learning!")
    print()
    
    print("📋 Test Order:")
    print("1. Clipboard - Simplest component (copy/paste text)")
    print("2. Audio Recording - Test your microphone")  
    print("3. Whisper AI - Test speech-to-text (downloads AI model)")
    print("4. Global Hotkeys - Test system-wide key detection")
    print("5. Full Application - Everything working together")
    print()
    
    # Ask if user wants to proceed
    response = input("Ready to start testing? (y/n): ").lower().strip()
    if response not in ['y', 'yes']:
        print("Okay, run this script again when you're ready!")
        return
    
    print()
    
    # Define tests in order - use absolute paths based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests = [
        (os.path.join(script_dir, "component", "test_clipboard.py"), "Clipboard copy/paste functionality"),
        (os.path.join(script_dir, "component", "test_audio.py"), "Microphone audio recording"),
        (os.path.join(script_dir, "component", "test_whisper.py"), "AI speech-to-text transcription"),
        (os.path.join(script_dir, "component", "test_hotkeys.py"), "Global hotkey detection"),
    ]
    
    # Track results
    passed_tests = 0
    total_tests = len(tests)
    
    # Run each test
    for i, (script, description) in enumerate(tests, 1):
        print_header(f"Test {i}/{total_tests}: {description}")
        
        if run_python_script(script, description):
            passed_tests += 1
            print("✅ Test passed! Press Enter to continue to next test...")
        else:
            print("❌ Test had issues. Press Enter to continue anyway, or Ctrl+C to stop...")
        
        try:
            input()
        except KeyboardInterrupt:
            print("\n\n⚠️  Testing stopped by user.")
            return
        
        print()
    
    # Show final results
    print_header("Test Results Summary")
    
    print(f"📊 Tests completed: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! Your system is ready for the full application!")
        print()
        print("🚀 Next steps:")
        print("   1. Run 'python main.py' to start the full speech-to-text app")
        print("   2. Press Ctrl+Shift+Space to record speech")
        print("   3. Speak clearly, then press Ctrl+Shift+Space again to stop")
        print("   4. The transcribed text will be copied to your clipboard")
        print("   5. Paste with Ctrl+V in any application!")
        
    elif passed_tests >= total_tests // 2:
        print("⚠️  Most tests passed, but some had issues.")
        print("You can try the full app, but it might not work perfectly.")
        print("Consider reviewing the failed tests and troubleshooting.")
        
    else:
        print("❌ Several tests failed. The full app likely won't work correctly.")
        print("Please troubleshoot the failing components first:")
        print("   - Check that all Python packages are installed")
        print("   - Verify microphone permissions")
        print("   - Test running as administrator for global hotkeys")
    
    print()
    print("💡 Remember: This is a learning project!")
    print("   Understanding why tests fail is as valuable as having them pass.")

if __name__ == "__main__":
    """
    Run the test suite when script is executed directly
    """
    main()