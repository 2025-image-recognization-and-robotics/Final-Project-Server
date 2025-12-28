from __future__ import annotations

import threading
import tkinter as tk
from typing import Iterable

from src.core.logging import logger
from src.perception.yolo_inference import YoloInference


class SimpleTargetSelector:
    """Runs a minimal Tkinter GUI in a background thread.

    Usage:
        gui = SimpleTargetSelector(yolo, target_list)
        gui.start()
        # later: gui.stop()

    The GUI will call yolo.set_target(selected) when the user selects a class.
    """

    def __init__(self, yolo: YoloInference, targets: Iterable[str]) -> None:
        self._yolo = yolo
        self._targets = list(targets)
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._listbox: tk.Listbox | None = None
        self._running = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("SimpleTargetSelector GUI started")

    def stop(self) -> None:
        self._running.clear()
        if self._root:
            try:
                # Ask the Tkinter thread to quit via event
                self._root.event_generate("<<QuitRequested>>")
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("SimpleTargetSelector GUI stopped")

    def _on_select(self, event: tk.Event | None = None) -> None:
        if not self._listbox:
            return
        sel = self._listbox.curselection()
        if not sel:
            # Nothing selected -> clear target
            self._yolo.set_target("")
            return
        idx = sel[0]
        target = self._targets[idx]
        try:
            self._yolo.set_target(target)
            logger.info(f"GUI set target: {target}")
        except Exception as e:
            logger.error(f"Failed to set target from GUI: {e}")

    def _run(self) -> None:
        # Create the Tk root and widgets in this thread
        root = tk.Tk()
        self._root = root
        root.title("Select YOLO Target")

        frame = tk.Frame(root, padx=8, pady=8)
        frame.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(frame, text="Choose target class:")
        label.pack(anchor=tk.W)

        listbox = tk.Listbox(frame, height=min(10, len(self._targets)), exportselection=False)
        for t in self._targets:
            listbox.insert(tk.END, t)
        listbox.pack(fill=tk.BOTH, expand=True)
        listbox.bind("<<ListboxSelect>>", self._on_select)
        self._listbox = listbox

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(6, 0))

        clear_btn = tk.Button(btn_frame, text="Clear", command=lambda: self._clear_selection())
        clear_btn.pack(side=tk.LEFT, padx=(0, 4))

        quit_btn = tk.Button(btn_frame, text="Quit GUI", command=root.quit)
        quit_btn.pack(side=tk.LEFT)

        # Custom event to stop the loop
        root.bind("<<QuitRequested>>", lambda e: root.quit())

        try:
            root.mainloop()
        except Exception:
            pass
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    def _clear_selection(self) -> None:
        if self._listbox:
            self._listbox.selection_clear(0, tk.END)
        try:
            self._yolo.set_target("")
            logger.info("GUI cleared target")
        except Exception as e:
            logger.error(f"Failed to clear target from GUI: {e}")

