import threading
import tkinter as tk

class VisualIndicator:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self._thread = None
        self._root = None
        self._canvas = None
        self.is_running = False
        self.current_state = "idle"
        
    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_tk_loop, daemon=True)
        self._thread.start()
        
    def _run_tk_loop(self):
        # Dedicated thread for the Tkinter event loop
        self._root = tk.Tk()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)
        self._root.attributes("-transparentcolor", "black")
            
        # Minimal bar just above the bottom taskbar
        w = 300
        h = 6
        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()
        
        # Position slightly higher to clear Windows taskbar (~40-50px)
        x = (screen_width // 2) - (w // 2)
        y = screen_height - h - 50
        
        self._root.geometry(f"{w}x{h}+{x}+{y}")
        self._root.configure(bg='black')
        
        self._canvas = tk.Canvas(self._root, width=w, height=h, bg='black', highlightthickness=0)
        self._canvas.pack()
        
        # Start hidden
        self._root.withdraw()
        
        self._root.protocol("WM_DELETE_WINDOW", self.stop)
        self._root.mainloop()

    def update_state(self, new_state: str):
        self.current_state = new_state
        if self._root is not None:
            # Safely schedule the UI update on the Tk thread without focus stealing
            try:
                self._root.after(0, self._render_state)
            except Exception:
                pass
                
    def _render_state(self):
        if not self.is_running or not self._root:
            return
            
        if self.current_state in ["recording", "processing"]:
            color = "#228b22" if self.current_state == "recording" else "#ffa500" # Green or Orange
            
            self._root.deiconify()
            self._root.lift()
            self._root.attributes("-topmost", True)
            self._canvas.delete("all")
            self._canvas.create_rectangle(0, 0, 300, 6, fill=color, outline="")
            self._root.update()
        else:
            self._root.withdraw()
            
    def stop(self):
        self.is_running = False
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass
            self._root = None
