import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import keyboard  # global hotkeys
import pydirectinput
from mido import MidiFile

# -----------------------------
# YOUR KEY MAPPING (exact)
# -----------------------------
DEGREE_TO_KEY_UP = {1: "q", 2: "w", 3: "e", 4: "r", 5: "t", 6: "y", 7: "u"}
KEY_DO_DOUBLE_UP = "i"
DEGREE_TO_KEY_LO = {1: "a", 2: "s", 3: "d", 4: "f", 5: "g", 6: "h", 7: "j"}

MAJOR_PC_TO_DEGREE = {0: 1, 2: 2, 4: 3, 5: 4, 7: 5, 9: 6, 11: 7}


class MidiLuteGUI:
    # Notes starting within this window are treated as one chord and pressed together.
    CHORD_WINDOW = 0.03  # seconds (try 0.05 if your MIDI is more "strummed")

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("MIDI → Lute Keys (F4 Play / F3 Stop)")

        self.midi_path = tk.StringVar(value="")
        self.do_midi = tk.IntVar(value=60)      # MIDI note number for DO (base octave)
        self.transpose = tk.IntVar(value=0)     # semitone shift

        # speed multiplier applied to delays:
        # 1.00 = normal
        # 0.20 = 5× faster
        # 3.00 = 3× slower
        self.speed = tk.DoubleVar(value=1.00)

        self.status = tk.StringVar(value="Idle.")
        self._stop_flag = threading.Event()
        self._thread = None

        # Keys currently held down (for chords)
        self._held_keys = set()

        self._build_ui()

        keyboard.add_hotkey("f4", lambda: self.root.after(0, self.start))
        keyboard.add_hotkey("f3", lambda: self.root.after(0, self.stop))
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        frm = tk.Frame(self.root, padx=10, pady=10)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="MIDI file:").grid(row=0, column=0, sticky="w")
        tk.Entry(frm, textvariable=self.midi_path, width=52).grid(row=0, column=1, sticky="we")
        tk.Button(frm, text="Browse...", command=self.browse).grid(row=0, column=2, padx=(8, 0))

        tk.Label(frm, text="DO MIDI (A = do, Q = do'):").grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Entry(frm, textvariable=self.do_midi, width=10).grid(row=1, column=1, sticky="w", pady=(8, 0))

        tk.Label(frm, text="Transpose (semitones):").grid(row=2, column=0, sticky="w", pady=(8, 0))
        tk.Entry(frm, textvariable=self.transpose, width=10).grid(row=2, column=1, sticky="w", pady=(8, 0))

        self.speed_text = tk.StringVar(value="Speed: 1.00×")

        def on_speed_change(_):
            mult = float(self.speed.get())
            speed_x = 1.0 / mult if mult > 0 else 0
            self.speed_text.set(f"Speed: {speed_x:.2f}×")

        tk.Label(frm, text="Speed (drag while playing):").grid(row=3, column=0, sticky="w", pady=(8, 0))
        tk.Scale(
            frm,
            from_=0.20, to=3.00,
            resolution=0.05,
            orient="horizontal",
            variable=self.speed,
            length=260,
            command=on_speed_change
        ).grid(row=3, column=1, sticky="w", pady=(8, 0))
        tk.Label(frm, textvariable=self.speed_text).grid(row=3, column=2, sticky="w", padx=(8, 0), pady=(8, 0))

        tk.Button(frm, text="Start (F4)", command=self.start).grid(row=4, column=0, sticky="w", pady=(12, 0))
        tk.Button(frm, text="Stop (F3)", command=self.stop).grid(row=4, column=1, sticky="w", pady=(12, 0))

        tk.Label(frm, textvariable=self.status, fg="blue").grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(12, 0)
        )

        frm.columnconfigure(1, weight=1)
        on_speed_change(None)

    def browse(self):
        path = filedialog.askopenfilename(
            title="Select MIDI file",
            filetypes=[("MIDI files", "*.mid *.midi"), ("All files", "*.*")]
        )
        if path:
            self.midi_path.set(path)

    def press(self, key: str):
        pydirectinput.keyDown(key)

    def release(self, key: str):
        pydirectinput.keyUp(key)

    def note_to_key(self, note: int, do_midi: int):
        diff = note - do_midi
        octave = diff // 12
        pc = diff % 12

        degree = MAJOR_PC_TO_DEGREE.get(pc)
        if degree is None:
            return None  # skips sharps/flats

        if octave <= 0:
            return DEGREE_TO_KEY_LO[degree]
        if octave == 1:
            return DEGREE_TO_KEY_UP[degree]
        if degree == 1:
            return KEY_DO_DOUBLE_UP
        return DEGREE_TO_KEY_UP[degree]

    def start(self):
        if self._thread and self._thread.is_alive():
            self.status.set("Already playing. Press F3 to stop.")
            return

        path = self.midi_path.get().strip()
        if not path:
            messagebox.showerror("Missing file", "Choose a .mid/.midi file first.")
            return

        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()
        self.status.set("Stopping...")

    def _sleep_scaled(self, seconds: float):
        remaining = seconds
        while remaining > 0 and not self._stop_flag.is_set():
            step = min(0.02, remaining)
            time.sleep(step)
            remaining -= step

    def _worker(self):
        try:
            mid = MidiFile(self.midi_path.get().strip())
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("MIDI error", str(e)))
            return

        base_do = int(self.do_midi.get()) + int(self.transpose.get())

        self.root.after(0, lambda: self.status.set("Starting in 2s… focus the game/app window."))
        time.sleep(2.0)
        self.root.after(0, lambda: self.status.set("Playing… (F3 stop)"))

        self._held_keys.clear()

        pending_note_ons = []
        pending_time = 0.0

        def flush_pending():
            for m in pending_note_ons:
                key = self.note_to_key(m.note, base_do)
                if key and key not in self._held_keys:
                    self.press(key)
                    self._held_keys.add(key)
            pending_note_ons.clear()

        for msg in mid:
            if self._stop_flag.is_set():
                break

            dt = (msg.time or 0) * float(self.speed.get())

            # If time is passing, we may want to treat accumulated near-simultaneous notes as a chord.
            if dt > 0:
                pending_time += dt
                if pending_note_ons and pending_time >= self.CHORD_WINDOW:
                    flush_pending()
                    pending_time = 0.0

                self._sleep_scaled(dt)
                if self._stop_flag.is_set():
                    break

            # Buffer NOTE ONs so notes that start "almost together" get pressed together.
            if msg.type == "note_on" and msg.velocity > 0:
                pending_note_ons.append(msg)
                continue

            # Before NOTE OFF or other events, press any pending chord notes first.
            if pending_note_ons:
                flush_pending()
                pending_time = 0.0

            # Release logic
            if msg.type == "note_off" or (msg.type == "note_on" and getattr(msg, 'velocity', 0) == 0):
                key = self.note_to_key(msg.note, base_do)
                if key and key in self._held_keys:
                    self.release(key)
                    self._held_keys.remove(key)

        # Flush anything left
        if pending_note_ons:
            flush_pending()

        # Safety release
        for k in list(self._held_keys):
            try:
                self.release(k)
            except Exception:
                pass
        self._held_keys.clear()

        self.root.after(0, lambda: self.status.set("Stopped." if self._stop_flag.is_set() else "Finished."))

    def on_close(self):
        self._stop_flag.set()

        for k in list(getattr(self, "_held_keys", set())):
            try:
                self.release(k)
            except Exception:
                pass

        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    MidiLuteGUI(root)
    root.mainloop()
