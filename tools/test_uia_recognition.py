#!/usr/bin/env python3

import importlib
import sys



EDIT_CONTROL_TYPES = {
    "EditControl",
    "DocumentControl",
    "ComboBoxControl",
}

DEFAULT_MAX_DEPTH = 10
DEFAULT_MAX_COUNT = 1500


def describe_control(control):
    return {
        "name": control.Name,
        "type": control.ControlTypeName,
        "class": control.ClassName,
        "automation_id": control.AutomationId,
        "enabled": control.IsEnabled,
        "focusable": control.IsKeyboardFocusable,
    }


def format_control(info, indent=""):
    print(f"{indent}name: {info['name']}")
    print(f"{indent}type: {info['type']}")
    print(f"{indent}class: {info['class']}")
    print(f"{indent}automation_id: {info['automation_id']}")
    print(f"{indent}enabled: {info['enabled']}")
    print(f"{indent}focusable: {info['focusable']}")


def is_editable(control):
    if control.ControlTypeName not in EDIT_CONTROL_TYPES:
        return False
    if not control.IsEnabled or not control.IsKeyboardFocusable:
        return False
    pattern = control.GetValuePattern()
    if pattern:
        try:
            return not pattern.IsReadOnly
        except Exception:
            return True
    return True


def has_text_pattern(control):
    try:
        pattern = control.GetTextPattern()
    except Exception:
        pattern = None
    return pattern is not None


def iter_controls(control, max_depth, max_count):
    stack = [(control, 0)]
    count = 0
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue
        yield current
        count += 1
        if count >= max_count:
            return
        try:
            children = current.GetChildren()
        except Exception:
            children = []
        for child in reversed(children):
            stack.append((child, depth + 1))


def list_editable_controls(root, max_depth=DEFAULT_MAX_DEPTH, max_count=DEFAULT_MAX_COUNT):
    matches = []
    for control in iter_controls(root, max_depth=max_depth, max_count=max_count):
        if is_editable(control):
            matches.append(control)
    return matches


def list_text_controls(root, max_depth=DEFAULT_MAX_DEPTH, max_count=DEFAULT_MAX_COUNT):
    matches = []
    for control in iter_controls(root, max_depth=max_depth, max_count=max_count):
        if has_text_pattern(control):
            matches.append(control)
    return matches


def normalize_target_names(args):
    if args:
        return [name.strip().lower() for name in args if name.strip()]
    return ["cursor"]


def list_top_level_windows(auto_module):
    root = auto_module.GetRootControl()
    if not root:
        return []
    try:
        children = root.GetChildren()
    except Exception:
        return []
    return [child for child in children if child.ControlTypeName == "WindowControl"]


def load_uiautomation():
    try:
        auto_module = importlib.import_module("uiautomation")
    except Exception as exc:
        print(f"Failed to import uiautomation: {exc}")
        return None
    return auto_module


def main():
    if sys.platform != "win32":
        print("This tool only runs on Windows.")
        return 1

    auto_module = load_uiautomation()
    if auto_module is None:
        return 1

    target_names = normalize_target_names(sys.argv[1:])

    focused = auto_module.GetFocusedControl()
    if focused:
        print("Focused control")
        format_control(describe_control(focused), "  ")
    else:
        print("Focused control")
        print("  none")

    windows = list_top_level_windows(auto_module)
    print("\nMatching windows")

    matches = []
    for window in windows:
        name = (window.Name or "").lower()
        if any(target in name for target in target_names):
            matches.append(window)

    if not matches:
        print("  none")
        return 0

    for idx, window in enumerate(matches, start=1):
        info = describe_control(window)
        print(f"\n{idx}.")
        format_control(info, "  ")
        editable = list_editable_controls(window)
        print("  editable_controls:")
        if not editable:
            print("    none")
        else:
            for edit_idx, control in enumerate(editable, start=1):
                print(f"    {edit_idx}.")
                format_control(describe_control(control), "      ")

        text_controls = list_text_controls(window)
        print("  text_controls:")
        if not text_controls:
            print("    none")
        else:
            for text_idx, control in enumerate(text_controls, start=1):
                print(f"    {text_idx}.")
                format_control(describe_control(control), "      ")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
