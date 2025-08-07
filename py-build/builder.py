# py-build/builder.py
import subprocess
import sys
from pathlib import Path

def build():
    """Execute PowerShell build script on Windows from WSL."""
    print("🚀 Starting build via Windows PowerShell...")
    
    # Get PowerShell script path
    ps_script = Path(__file__).parent / "build-windows.ps1"
    
    try:
        # Execute PowerShell script (it handles all path configuration)
        cmd = [
            "powershell.exe", 
            "-ExecutionPolicy", "Bypass",
            "-File", str(ps_script)
        ]
        
        print(f"📦 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False, text=True)
        
        if result.returncode == 0:
            print("✅ Windows build completed successfully!")
        else:
            print("❌ Windows build failed!")
            sys.exit(1)
        
    except FileNotFoundError:
        print("❌ PowerShell not found! Make sure you're running from WSL with Windows PowerShell available.")
        sys.exit(1)

if __name__ == "__main__":
    build()