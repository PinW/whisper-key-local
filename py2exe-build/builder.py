# build/builder.py
import py2exe
import shutil
import sys
import os
import zipfile
from config import APP_NAME, APP_VERSION, ENTRY_POINT, DIST_DIR, PY2EXE_OPTIONS, DATA_FILES

# Increase recursion limit to handle deep dependency chains
sys.setrecursionlimit(5000)

# Add project root to Python path so py2exe can find src modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)
print(f"Added to Python path: {project_root}")

def build():
    """Executes the py2exe build process."""
    print(f"--- Starting {APP_NAME} Build ---")

    if DIST_DIR.exists():
        print(f"Cleaning previous build directory: {DIST_DIR}")
        shutil.rmtree(DIST_DIR)
    
    # Build in project root/dist using absolute path from current script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # Go up one level from py2exe-build/
    build_dir = os.path.join(project_root, 'dist', f'WhisperKey-v{APP_VERSION}')
    os.makedirs(os.path.dirname(build_dir), exist_ok=True)
    print(f"Build directory: {build_dir}")

    try:
        print("Running py2exe freeze...")
        
        # Use Windows user directory path
        py2exe.freeze(
            console=[{"script": ENTRY_POINT}],  # Icon optional for now
            options={"py2exe": {**PY2EXE_OPTIONS, "dist_dir": build_dir}},
            data_files=DATA_FILES,
        )
        
        # Verify the build actually created files
        if os.path.exists(build_dir):
            files = os.listdir(build_dir)
            print(f"\n✅ Build successful!")
            print(f"   Build directory: {build_dir}")
            print(f"   Files created: {len(files)} files")
            print(f"   Main executable: {os.path.join(build_dir, 'whisper-key.exe')}")
            
            # Post-build: Extract sounddevice DLLs from library.zip if they exist there
            _extract_sounddevice_dlls(build_dir)
            
        else:
            print(f"\n❌ Build claimed success but no files created in {build_dir}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Build Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()