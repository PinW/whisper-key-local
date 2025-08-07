# py-build/builder.py
import subprocess
import sys
from pathlib import Path
from config import APP_NAME

def build():
    """Execute PowerShell build script on Windows from WSL."""
    print(f"🚀 Starting {APP_NAME} build via Windows PowerShell...")
    
    # Get paths for Windows execution
    project_root = Path(__file__).parent.parent
    ps_script = project_root / "py-build" / "build-windows.ps1"
    
    # Convert WSL paths to Windows paths using wslpath
    try:
        import subprocess
        windows_project_root = subprocess.run(['wslpath', '-w', str(project_root)], 
                                            capture_output=True, text=True, check=True).stdout.strip()
        windows_script = subprocess.run(['wslpath', '-w', str(ps_script)], 
                                      capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        print("❌ Failed to convert WSL paths to Windows paths")
        sys.exit(1)
    
    try:
        # Execute PowerShell script via Windows
        cmd = [
            "powershell.exe", 
            "-ExecutionPolicy", "Bypass",
            "-File", windows_script,
            "-ProjectRoot", windows_project_root
        ]
        
        print(f"📦 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ Windows build completed successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print("❌ Windows build failed!")
        print(f"Error: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ PowerShell not found! Make sure you're running from WSL with Windows PowerShell available.")
        sys.exit(1)

if __name__ == "__main__":
    build()