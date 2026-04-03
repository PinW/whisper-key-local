import logging
import threading

from .platform import monitors

DEFAULTS = {
    'monitor': 'follow_focus',
    'position': 'bottom_center',
    'margin': 80,
    'font_size': 16,
    'opacity': 0.85,
    'bg_color': '#1e1e1e',
    'text_color': '#ffffff',
}

POSITION_CALCULATORS = {
    'bottom_center': lambda m, ww, wh, mg: (
        m.work_x + (m.work_width - ww) // 2,
        m.work_y + m.work_height - wh - mg,
    ),
    'top_center': lambda m, ww, wh, mg: (
        m.work_x + (m.work_width - ww) // 2,
        m.work_y + mg,
    ),
    'bottom_left': lambda m, ww, wh, mg: (
        m.work_x + mg,
        m.work_y + m.work_height - wh - mg,
    ),
    'bottom_right': lambda m, ww, wh, mg: (
        m.work_x + m.work_width - ww - mg,
        m.work_y + m.work_height - wh - mg,
    ),
    'top_left': lambda m, ww, wh, mg: (
        m.work_x + mg,
        m.work_y + mg,
    ),
    'top_right': lambda m, ww, wh, mg: (
        m.work_x + m.work_width - ww - mg,
        m.work_y + mg,
    ),
    'center': lambda m, ww, wh, mg: (
        m.work_x + (m.work_width - ww) // 2,
        m.work_y + (m.work_height - wh) // 2,
    ),
}


class PreviewOverlay:
    def __init__(self, overlay_config: dict = None):
        self.logger = logging.getLogger(__name__)
        self._config = {**DEFAULTS, **(overlay_config or {})}
        self._root = None
        self._windows = {}
        self._visible = False
        self._all_mode = self._config['monitor'] == 'all'
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_tk(self):
        try:
            monitors.set_dpi_awareness()
            import tkinter as tk
            self._tk = tk

            self._root = tk.Tk()
            self._root.withdraw()
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)

            if self._all_mode:
                self._build_all_windows()
            else:
                self._apply_style(self._root)
                self._windows[0] = _OverlayWindow(self._root, self._root, self._make_label(self._root))

            self._ready.set()
            self._root.mainloop()
        except Exception as e:
            self.logger.error(f"Preview overlay failed: {e}")
            self._ready.set()

    def _make_label(self, parent):
        import tkinter.font as tkfont
        font = tkfont.Font(family="Segoe UI", size=self._config['font_size'], weight="bold")
        label = self._tk.Label(
            parent,
            text="",
            font=font,
            fg=self._config['text_color'],
            bg=self._config['bg_color'],
            wraplength=700,
            justify="center",
            padx=20,
            pady=12,
        )
        label.pack()
        return label

    def _apply_style(self, window):
        window.attributes("-alpha", self._config['opacity'])
        window.configure(bg=self._config['bg_color'])

    def _build_all_windows(self):
        self._destroy_extra_windows()
        for mon in monitors.enumerate_monitors():
            top = self._tk.Toplevel(self._root)
            top.withdraw()
            top.overrideredirect(True)
            top.attributes("-topmost", True)
            self._apply_style(top)
            label = self._make_label(top)
            self._windows[mon.index] = _OverlayWindow(top, top, label, mon)

    def _destroy_extra_windows(self):
        for ow in self._windows.values():
            if ow.toplevel is not self._root:
                ow.toplevel.destroy()
        self._windows.clear()

    def _resolve_target_monitor(self):
        mode = self._config.get('monitor', 'follow_focus')
        if mode == 'follow_focus':
            return monitors.get_monitor_of_focused_window()
        if mode == 'cursor':
            return monitors.get_monitor_at_cursor()
        if mode == 'primary':
            return monitors.get_primary_monitor()
        if isinstance(mode, int):
            return monitors.get_monitor_by_index(mode)
        return monitors.get_primary_monitor()

    def _calculate_position(self, monitor, win_w, win_h):
        position = self._config.get('position', 'bottom_center')
        margin = self._config.get('margin', 80)
        calc = POSITION_CALCULATORS.get(position, POSITION_CALCULATORS['bottom_center'])
        return calc(monitor, win_w, win_h, margin)

    def _position_window(self, ow):
        ow.toplevel.update_idletasks()
        mon = ow.fixed_monitor if ow.fixed_monitor else self._resolve_target_monitor()
        win_w = ow.toplevel.winfo_reqwidth()
        win_h = ow.toplevel.winfo_reqheight()
        x, y = self._calculate_position(mon, win_w, win_h)
        ow.toplevel.geometry(f"+{x}+{y}")

    def update_text(self, text):
        if not self._root:
            return

        def _update():
            for ow in self._windows.values():
                ow.label.configure(text=text)
                self._position_window(ow)
                if not self._visible:
                    ow.toplevel.deiconify()
            self._visible = True

        self._root.after(0, _update)

    def show(self):
        if not self._root:
            return

        def _show():
            for ow in self._windows.values():
                ow.toplevel.deiconify()
            self._visible = True

        self._root.after(0, _show)

    def hide(self):
        if not self._root:
            return

        def _hide():
            for ow in self._windows.values():
                ow.toplevel.withdraw()
            self._visible = False

        self._root.after(0, _hide)

    def update_config(self, overlay_config: dict):
        if not self._root:
            return

        old_monitor = self._config.get('monitor')
        self._config = {**DEFAULTS, **(overlay_config or {})}
        new_monitor = self._config.get('monitor')
        new_all_mode = new_monitor == 'all'

        def _apply():
            if new_all_mode != self._all_mode:
                self._all_mode = new_all_mode
                if new_all_mode:
                    self._build_all_windows()
                else:
                    self._destroy_extra_windows()
                    self._apply_style(self._root)
                    self._windows[0] = _OverlayWindow(
                        self._root, self._root, self._make_label(self._root),
                    )

            for ow in self._windows.values():
                self._apply_style(ow.toplevel)
                ow.label.configure(
                    fg=self._config['text_color'],
                    bg=self._config['bg_color'],
                )

            if self._visible:
                for ow in self._windows.values():
                    self._position_window(ow)

        self._root.after(0, _apply)


class _OverlayWindow:
    __slots__ = ('toplevel', 'root', 'label', 'fixed_monitor')

    def __init__(self, toplevel, root, label, fixed_monitor=None):
        self.toplevel = toplevel
        self.root = root
        self.label = label
        self.fixed_monitor = fixed_monitor
