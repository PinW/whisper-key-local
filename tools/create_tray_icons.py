#!/usr/bin/env python3
"""
Icon Generator for System Tray

This utility creates the icon files needed for the system tray feature.
We generate simple 16x16 pixel icons in different colors to represent app states.

For beginners: This is a helper script that creates small image files (icons) 
that will appear in your system tray to show what the app is doing.
"""

from PIL import Image, ImageDraw
import os

def create_circular_icon(color, size=16, output_path=None):
    """
    Create a simple circular icon with the specified color
    
    Parameters:
    - color: RGB tuple like (255, 0, 0) for red
    - size: Icon size in pixels (default 16x16 for system tray)
    - output_path: Where to save the icon file
    """
    # Create a new image with transparent background
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a filled circle with a border
    border_width = 1
    circle_bounds = [border_width, border_width, size-border_width-1, size-border_width-1]
    
    # Draw main circle
    draw.ellipse(circle_bounds, fill=color, outline=(64, 64, 64, 255), width=border_width)
    
    if output_path:
        image.save(output_path, 'PNG')
        print(f"Created icon: {output_path}")
    
    return image

def create_microphone_icon(color, size=16, output_path=None):
    """
    Create a simple microphone-style icon
    """
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Simple microphone representation - rounded rectangle + base
    mic_width = size // 3
    mic_height = size // 2
    mic_x = (size - mic_width) // 2
    mic_y = 2
    
    # Microphone capsule
    draw.rounded_rectangle(
        [mic_x, mic_y, mic_x + mic_width, mic_y + mic_height],
        radius=mic_width//4,
        fill=color,
        outline=(64, 64, 64, 255),
        width=1
    )
    
    # Microphone stand/base
    stand_y = mic_y + mic_height + 1
    draw.line([size//2, stand_y, size//2, size-2], fill=(64, 64, 64, 255), width=2)
    draw.line([size//2-2, size-2, size//2+2, size-2], fill=(64, 64, 64, 255), width=2)
    
    if output_path:
        image.save(output_path, 'PNG')
        print(f"Created icon: {output_path}")
    
    return image

def main():
    """
    Generate all the tray icons we need for different app states
    """
    print("Creating system tray icons...")
    
    # Define the asset directory path
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
    
    # Make sure assets directory exists
    os.makedirs(assets_dir, exist_ok=True)
    
    # Color scheme for different states
    colors = {
        'idle': (100, 149, 237),     # Cornflower blue - calm, ready state
        'recording': (220, 20, 60),   # Crimson red - active recording
        'processing': (255, 165, 0)   # Orange - working/thinking
    }
    
    # Create circular icons for each state
    for state, color in colors.items():
        icon_path = os.path.join(assets_dir, f'tray_{state}.png')
        if state == 'recording':
            # Use microphone icon for recording state
            create_microphone_icon(color, output_path=icon_path)
        else:
            # Use circular icons for other states
            create_circular_icon(color, output_path=icon_path)
    
    print(f"\nAll icons created successfully in: {assets_dir}")
    print("Icons created:")
    print("- tray_idle.png (blue circle) - App ready, waiting for hotkey")
    print("- tray_recording.png (red microphone) - Currently recording audio")  
    print("- tray_processing.png (orange circle) - Processing/transcribing audio")

if __name__ == "__main__":
    main()