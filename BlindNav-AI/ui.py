"""Tkinter dashboard UI for BlindNav AI."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import ttk

from navigator import BlindNavEngine, StatusUpdate


class BlindNavUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Vision Companion")
        self.root.geometry("420x640")
        self.root.configure(bg="#05080f")
        self.root.resizable(False, False)

        self.status_queue: queue.Queue[StatusUpdate] = queue.Queue()
        self.engine = BlindNavEngine()
        self.engine.set_update_callback(self._on_update)

        self.running = False
        self.status_text = tk.StringVar(value="STOPPED")
        self.alert_text = tk.StringVar(value="Waiting for start")
        self.fps_text = tk.StringVar(value="0.0")
        self.risk_text = tk.StringVar(value="LOW")
        self.error_text = tk.StringVar(value="")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_status)

    def _build_ui(self) -> None:
        title = tk.Label(self.root, text="Vision Companion", fg="#F8FAFC", bg="#05080f", font=("Helvetica", 28, "bold"))
        title.pack(pady=(24, 2))

        subtitle = tk.Label(self.root, text="Audio-first blind navigation assistant", fg="#8FA2BF", bg="#05080f", font=("Helvetica", 11))
        subtitle.pack(pady=(0, 18))

        self.canvas = tk.Canvas(self.root, width=280, height=280, bg="#05080f", highlightthickness=0)
        self.canvas.pack()
        self._draw_status_circle()

        controls = tk.Frame(self.root, bg="#05080f")
        controls.pack(pady=18)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 11, "bold"), padding=8)

        self.start_btn = ttk.Button(controls, text="Start", command=self._start)
        self.start_btn.grid(row=0, column=0, padx=8)

        self.stop_btn = ttk.Button(controls, text="Stop", command=self._stop)
        self.stop_btn.grid(row=0, column=1, padx=8)

        cards = tk.Frame(self.root, bg="#05080f")
        cards.pack(fill="x", padx=14, pady=(10, 6))

        self._card(cards, "GPS", "TRACKED", 0, 0)
        self._card(cards, "VISION", self.fps_text, 0, 1, prefix="FPS ")
        self._card(cards, "RISK", self.risk_text, 1, 0)
        self._card(cards, "ALERT", self.alert_text, 1, 1)

        error_lbl = tk.Label(self.root, textvariable=self.error_text, fg="#FF6B6B", bg="#05080f", font=("Helvetica", 10), wraplength=380)
        error_lbl.pack(pady=(8, 0))

    def _card(self, parent: tk.Widget, label: str, value: str | tk.StringVar, r: int, c: int, prefix: str = "") -> None:
        box = tk.Frame(parent, bg="#0D1320", bd=1, relief="solid", highlightbackground="#1E2A43", highlightthickness=1)
        box.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
        parent.grid_columnconfigure(c, weight=1)

        tk.Label(box, text=label, fg="#5D7395", bg="#0D1320", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        if isinstance(value, tk.StringVar):
            tk.Label(box, textvariable=value, fg="#E6EDF8", bg="#0D1320", font=("Helvetica", 13, "bold"), wraplength=160, justify="left").pack(anchor="w", padx=10, pady=(0, 10))
        else:
            tk.Label(box, text=f"{prefix}{value}", fg="#E6EDF8", bg="#0D1320", font=("Helvetica", 13, "bold")).pack(anchor="w", padx=10, pady=(0, 10))

    def _draw_status_circle(self) -> None:
        self.canvas.delete("all")
        color = "#00E5A8" if self.running else "#00C98D"
        self.canvas.create_oval(20, 20, 260, 260, outline=color, width=3)
        icon = "🎤" if self.running else "🔇"
        self.canvas.create_text(140, 125, text=icon, fill=color, font=("Helvetica", 34, "bold"))
        self.canvas.create_text(140, 175, text=self.status_text.get(), fill=color, font=("Helvetica", 16, "bold"))

    def _start(self) -> None:
        if self.running:
            return
        self.running = True
        self.status_text.set("RUNNING")
        self.error_text.set("")
        self._draw_status_circle()
        self.engine.start()

    def _stop(self) -> None:
        if not self.running:
            return
        self.engine.stop()
        self.running = False
        self.status_text.set("STOPPED")
        self._draw_status_circle()

    def _on_update(self, update: StatusUpdate) -> None:
        self.status_queue.put(update)

    def _poll_status(self) -> None:
        try:
            while True:
                update = self.status_queue.get_nowait()
                self.running = update.running
                self.status_text.set("RUNNING" if update.running else "STOPPED")
                self.fps_text.set(f"{update.fps:.1f}")
                self.risk_text.set(update.risk)
                self.alert_text.set(update.last_alert)
                self.error_text.set(update.error)
                self._draw_status_circle()
        except queue.Empty:
            pass
        finally:
            self.root.after(150, self._poll_status)

    def _on_close(self) -> None:
        self.engine.shutdown()
        self.root.destroy()


def run_ui() -> None:
    root = tk.Tk()
    BlindNavUI(root)
    root.mainloop()
