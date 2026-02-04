# macOS Menu Bar Icons Research

Research on macOS menu bar (status bar) icons: template images, size requirements, design guidelines, and Python implementation.

**Research Date:** 2026-02-04

---

## 1. Template Images

### What Are Template Images?

A template image is an `NSImage` whose colors are ignored by the system - only the alpha channel (opacity/transparency) information is used. macOS automatically tints template images to match the current system appearance (light or dark mode).

From [Apple Developer Documentation](https://developer.apple.com/documentation/appkit/nsimage/istemplate):
> "A Boolean value that determines whether the image represents a template image."

When you specify a template image for a status bar item, the system colorizes the image with a standard color suitable for the current appearance. You cannot control which color is used - this is handled automatically by macOS.

### How Template Images Work

1. **Alpha channel defines the shape**: The visible parts of your icon are determined by the alpha (opacity) values
2. **Color is ignored**: Whatever color you use (typically black) is replaced by the system
3. **Automatic adaptation**: In light mode, icons appear dark; in dark mode, icons appear light
4. **No separate assets needed**: One template image works for both modes

### How to Create a Template Image

There are two methods to mark an image as a template:

**Method 1 - Programmatic (recommended for runtime)**:
```python
# Using PyObjC
from AppKit import NSImage
image = NSImage.alloc().initWithContentsOfFile_("/path/to/icon.png")
image.setTemplate_(True)
```

**Method 2 - File naming convention**:
Name your image file with "Template" suffix (e.g., `iconTemplate.png`, `MyIconTemplate@2x.png`). When loaded with `NSImage(named:)`, macOS automatically recognizes it as a template.

### Technical Requirements for Template Images

- **Use only black pixels** with varying alpha/opacity levels for content
- **Transparent background** (alpha = 0) for areas that should not be visible
- **Alpha channel is required**: The image must have an alpha channel - images without alpha won't work correctly as templates
- **PDF files must have transparency**: PDFs without an alpha channel won't function as template images

---

## 2. Size Requirements

### Menu Bar Height History

From [Bjango - Designing macOS menu bar extras](https://bjango.com/articles/designingmenubarextras/):

| macOS Version | Menu Bar Height |
|--------------|-----------------|
| System 1 | 19pt |
| Mac OS X beta | 21pt |
| Yosemite | 22pt |
| Big Sur onwards | 24pt |
| MacBook Pro with notch (14"/16") | 37pt |

**Note**: 1 point = 1 non-Retina pixel = 2 Retina pixels

### Working Area

Despite menu bar height variations, the **working area for menu bar extras is fixed at 22pt maximum height**. Items cannot be taller than this.

### Recommended Icon Dimensions

| Scale | Canvas Size | Content Size | Notes |
|-------|-------------|--------------|-------|
| @1x | 22x22 px | 16x16 px centered | Non-Retina displays |
| @2x | 44x44 px | 32x32 px centered | Retina displays |

**Key guidance from [Bjango](https://bjango.com/articles/designingmenubarextras/)**:
> "A good size for a circular item to feel the same weight as system menu bar items is 16x16pt."

### Retina Considerations

- Always provide both @1x and @2x variants for PNG assets
- Or use vector formats (PDF, SVG) which scale automatically
- Name convention: `icon.png` (1x) and `icon@2x.png` (2x)
- For template images: `iconTemplate.png` and `iconTemplate@2x.png`

---

## 3. Design Guidelines

### Apple's Recommendations

From [Apple HIG - The Menu Bar](https://developer.apple.com/design/human-interface-guidelines/the-menu-bar):
- Avoid using icons for menu titles
- Make menu titles as short as possible without losing clarity
- If you include icons in menus, only do so where they add significant value

### Template Image Design Best Practices

From [Bjango](https://bjango.com/articles/designingmenubarextras/):

1. **Solid color artwork**: Since color is ignored, create icons as solid color (typically black)
2. **Use opacity for shading**: Different opacity levels can indicate state (like Wi-Fi signal strength)
3. **Apple's opacity standard**: 35% opacity for disabled/inactive elements
4. **No padding typically needed**: Unless required for vertical centering
5. **Test with Reduce Transparency**: The accessibility setting converts the menu bar to solid dark/light grey - verify your icons remain visible

### Why Template Images Are Preferred

- Automatically adapt to light/dark mode
- Match system icon appearance
- No need to maintain multiple color variants
- Consistent with macOS design language

### When NOT to Use Template Images

- If your icon requires specific colors (brand colors)
- If you need a full-color representation
- Note: Colored icons may have visibility issues in dark mode

---

## 4. File Formats

### Supported Formats

From [Bjango](https://bjango.com/articles/designingmenubarextras/):

| Format | Pros | Cons |
|--------|------|------|
| **PDF** | Single file, resolution-independent, supports vectors | Must have alpha channel |
| **SVG** | Single file, resolution-independent, web-compatible | Less native macOS support |
| **PNG (pair)** | Wide compatibility, precise pixel control | Requires @1x and @2x files |
| **Code-drawn** | Dynamic content (clocks, dates) | More complex implementation |

### Recommendations

**For static icons**: Use PDF (single file, scales automatically) or PNG pairs (more control)

**For dynamic icons**: Draw with code using Core Graphics/AppKit

### Asset Catalogs (Xcode)

If building a native macOS app:
- Create an Asset Catalog (.xcassets)
- Add Image Set for your icon
- Check "Render As: Template Image" in the inspector
- Provide @1x and @2x variants

---

## 5. Implementation in Python

### Using pystray

[pystray](https://github.com/moses-palmer/pystray) is a cross-platform system tray library. On macOS, it uses the Darwin backend which automatically sets template mode.

From the pystray source code (`_darwin.py`):
```python
# pystray automatically converts PIL images to NSImage and sets template mode
self._icon_image.setTemplate_(AppKit.YES)
self._status_item.button().setImage_(self._icon_image)
```

**Basic pystray usage**:
```python
import pystray
from PIL import Image

# Load or create image
image = Image.open("icon.png")

# Create icon (pystray handles template mode automatically on macOS)
icon = pystray.Icon("app_name", image, "Tooltip", menu)
icon.run()
```

**Important notes for pystray on macOS**:
- `run()` must be called from the main thread
- The Darwin backend requires the application runloop
- Radio button menu items are not supported on macOS

### Using rumps (macOS-only)

[rumps](https://github.com/jaredks/rumps) (Ridiculously Uncomplicated macOS Python Statusbar apps) provides more direct control over template mode.

```python
import rumps

class MyApp(rumps.App):
    def __init__(self):
        super(MyApp, self).__init__(
            "My App",
            icon="icon.png",
            template=True  # Enable template mode for dark mode support
        )

if __name__ == "__main__":
    MyApp().run()
```

**Template property in rumps**:
> "If set to `True`, template mode is enabled and the icon will be displayed correctly in dark menu bar mode."

### Direct PyObjC Approach

For maximum control, use PyObjC directly:

```python
from AppKit import (
    NSStatusBar, NSImage, NSVariableStatusItemLength,
    NSBundle, YES
)

# Create status bar item
statusbar = NSStatusBar.systemStatusBar()
status_item = statusbar.statusItemWithLength_(NSVariableStatusItemLength)

# Load image and set as template
image = NSImage.alloc().initByReferencingFile_("/path/to/icon.png")
image.setTemplate_(YES)  # Critical for dark mode support

# Apply to status item
status_item.button().setImage_(image)
```

### Platform-Specific Icon Selection

For cross-platform apps, you may want different approaches:

```python
import sys

if sys.platform == "darwin":
    # Use template image on macOS
    icon_path = "iconTemplate.png"  # or use setTemplate_(True)
elif sys.platform == "win32":
    # Use colored icon on Windows
    icon_path = "icon-colored.png"
else:
    # Linux
    icon_path = "icon-light.png"  # Light icon for dark panels
```

---

## 6. Common Pitfalls

### What Breaks Dark/Light Mode Adaptation

1. **Not using template mode**
   - Colored icons won't adapt to dark mode
   - Solution: Use `setTemplate_(True)` or name files with "Template" suffix

2. **Missing alpha channel**
   - PDFs or PNGs without transparency won't render correctly as templates
   - Solution: Ensure your images have proper alpha channels

3. **Using colored pixels in template images**
   - Only the alpha channel is used; colors are ignored
   - Solution: Use black pixels with varying opacity levels

4. **Menu bar color follows wallpaper (Big Sur+)**
   - From [Apple Community](https://discussions.apple.com/thread/252046054): "The Menu Bar color is now based on your wallpaper rather than the Dark Mode setting"
   - This can cause icon visibility issues even with proper template images
   - Solution: Test with various wallpapers; consider "Reduce Transparency" accessibility setting

5. **Incorrect icon sizing**
   - Icons larger than 22pt will be clipped
   - Icons not centered may appear misaligned
   - Solution: Use 22x22pt canvas with 16x16pt content centered

6. **Not providing @2x assets**
   - Icons appear blurry on Retina displays
   - Solution: Always provide @2x variants or use vector formats (PDF/SVG)

7. **Third-party app icons not updating**
   - Some apps cache icons or don't respond to appearance changes
   - Workaround: `killall -KILL SystemUIServer` can force refresh
   - Or restart the application

8. **pystray threading issues on macOS**
   - The Darwin backend must run on the main thread
   - `run_detached()` may cause issues on Apple Silicon (M-series chips)
   - Solution: Call `run()` from main thread, avoid `run_detached()` on macOS

### Testing Checklist

- [ ] Test in both light and dark mode
- [ ] Test with different wallpapers (light and dark)
- [ ] Test with "Reduce Transparency" enabled (System Preferences > Accessibility > Display)
- [ ] Test on Retina and non-Retina displays
- [ ] Test on MacBook Pro with notch (taller menu bar)
- [ ] Verify icon is visible in both modes without being washed out

---

## Sources

### Apple Documentation
- [Apple Developer - NSImage isTemplate](https://developer.apple.com/documentation/appkit/nsimage/istemplate)
- [Apple HIG - The Menu Bar](https://developer.apple.com/design/human-interface-guidelines/the-menu-bar)
- [Apple HIG - SF Symbols](https://developer.apple.com/design/human-interface-guidelines/sf-symbols)
- [Apple Developer Forums - Create a template image](https://developer.apple.com/forums/thread/106293)

### Third-Party Guides
- [Bjango - Designing macOS menu bar extras](https://bjango.com/articles/designingmenubarextras/) (comprehensive guide)
- [The Icon Handbook - Mac OS X Icon Reference Chart](https://iconhandbook.co.uk/reference/chart/osx/)

### Python Libraries
- [pystray - GitHub](https://github.com/moses-palmer/pystray)
- [pystray Documentation](https://pystray.readthedocs.io/en/latest/)
- [rumps - GitHub](https://github.com/jaredks/rumps) (macOS-only)
- [PyObjC - GitHub](https://github.com/ronaldoussoren/pyobjc)

### Troubleshooting
- [Apple Community - Menu bar dark mode issues](https://discussions.apple.com/thread/252046054)
- [TechBloat - Third-party menu bar icons in dark mode](https://www.techbloat.com/how-to-make-third-party-menu-bar-icons-look-better-with-dark-mode-on-mac.html)

---

## Summary: Quick Reference

### For a macOS menu bar icon that works in light and dark mode:

1. **Create your icon**:
   - 22x22pt canvas, 16x16pt content centered
   - Use black pixels with varying opacity
   - Transparent background
   - Export as PNG with alpha channel

2. **Provide Retina variants**:
   - `iconTemplate.png` (22x22 px)
   - `iconTemplate@2x.png` (44x44 px)
   - Or use a single PDF with transparency

3. **Enable template mode in code**:
   ```python
   image.setTemplate_(True)  # PyObjC/rumps
   # or pystray handles this automatically
   ```

4. **Test thoroughly** in both appearance modes and with various wallpapers
