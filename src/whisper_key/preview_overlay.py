import logging
import threading


class PreviewOverlay:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._root = None
        self._label = None
        self._visible = False
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run_tk(self):
        try:
            import tkinter as tk
            import tkinter.font as tkfont

            self._root = tk.Tk()
            self._root.withdraw()
            self._root.overrideredirect(True)
            self._root.attributes("-topmost", True)
            self._root.attributes("-alpha", 0.85)
            self._root.configure(bg="#1e1e1e")

            font = tkfont.Font(family="Segoe UI", size=16, weight="bold")

            self._label = tk.Label(
                self._root,
                text="",
                font=font,
                fg="#ffffff",
                bg="#1e1e1e",
                wraplength=700,
                justify="center",
                padx=20,
                pady=12,
            )
            self._label.pack()

            self._ready.set()
            self._root.mainloop()
        except Exception as e:
            self.logger.error(f"Preview overlay failed: {e}")
            self._ready.set()

    def _position_bottom_center(self):
        self._root.update_idletasks()
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()
        win_w = self._root.winfo_reqwidth()
        win_h = self._root.winfo_reqheight()
        x = (screen_w - win_w) // 2
        y = screen_h - win_h - 80
        self._root.geometry(f"+{x}+{y}")

    def update_text(self, text):
        if not self._root or not self._label:
            return

        def _update():
            self._label.configure(text=text)
            self._position_bottom_center()
            if not self._visible:
                self._root.deiconify()
                self._visible = True

        self._root.after(0, _update)

    def show(self):
        if not self._root:
            return

        def _show():
            self._root.deiconify()
            self._visible = True

        self._root.after(0, _show)

    def hide(self):
        if not self._root:
            return

        def _hide():
            self._root.withdraw()
            self._visible = False

        self._root.after(0, _hide)
