import mido
from pynput.keyboard import Controller, Listener, Key
import time
import tkinter as tk
from tkinter import filedialog, ttk
import threading

# Initialize keyboard controller
keyboard = Controller()

# Note mapping - MIDI note numbers to keyboard keys
NOTE_MAP = {
    # High octave (DO' to DO'')
    72: 'q',  # DO'
    74: 'w',  # RE'
    76: 'e',  # MI'
    77: 'r',  # FA'
    79: 't',  # SOL'
    81: 'y',  # LA'
    83: 'u',  # SI'
    84: 'i',  # DO''
    
    # Low octave (DO to DO)
    60: 'a',  # DO
    62: 's',  # RE
    65: 'd',  # FA
    67: 'f',  # SOL
    69: 'g',  # LA
    71: 'h',  # SI
    72: 'j',  # DO (overlap with high octave)
}

class MidiPlayerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MIDI to Keystrokes Player")
        self.root.geometry("500x350")
        
        self.midi_file = None
        self.is_playing = False
        self.stop_flag = False
        
        # File selection
        file_frame = tk.Frame(root)
        file_frame.pack(pady=20)
        
        self.file_label = tk.Label(file_frame, text="No file selected", width=40)
        self.file_label.pack(side=tk.LEFT, padx=5)
        
        browse_btn = tk.Button(file_frame, text="Browse MIDI", command=self.browse_file)
        browse_btn.pack(side=tk.LEFT)
        
        # Speed control
        speed_frame = tk.Frame(root)
        speed_frame.pack(pady=20)
        
        tk.Label(speed_frame, text="Speed Multiplier:").pack()
        
        self.speed_slider = tk.Scale(
            speed_frame, 
            from_=0.1, 
            to=3.0, 
            resolution=0.1,
            orient='horizontal',
            length=300,
            tickinterval=0.5
        )
        self.speed_slider.set(1.0)
        self.speed_slider.pack()
        
        self.speed_label = tk.Label(speed_frame, text="1.0x")
        self.speed_label.pack()
        self.speed_slider.config(command=self.update_speed_label)
        
        # Control buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)
        
        self.play_btn = tk.Button(
            button_frame, 
            text="Play (F4)", 
            command=self.play_midi,
            width=15,
            state=tk.DISABLED
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            button_frame, 
            text="Stop (F3)", 
            command=self.stop_midi,
            width=15,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = tk.Label(root, text="Ready", fg="green")
        self.status_label.pack(pady=10)
        
        # Hotkey info
        hotkey_label = tk.Label(root, text="Hotkeys: F4 = Start | F3 = Stop", fg="gray")
        hotkey_label.pack(pady=5)
        
        # Start keyboard listener for hotkeys
        self.listener = Listener(on_press=self.on_key_press)
        self.listener.start()
    
    def on_key_press(self, key):
        try:
            # F4 to start
            if key == Key.f4:
                self.root.after(0, self.play_midi)
            # F3 to stop
            elif key == Key.f3:
                self.root.after(0, self.stop_midi)
        except AttributeError:
            pass
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            initialdir="/",
            title="Select MIDI File",
            filetypes=(("MIDI files", "*.mid *.midi"), ("All files", "*.*"))
        )
        if filename:
            self.midi_file = filename
            self.file_label.config(text=filename.split('/')[-1])
            self.play_btn.config(state=tk.NORMAL)
            self.status_label.config(text="File loaded", fg="green")
    
    def update_speed_label(self, value):
        self.speed_label.config(text=f"{float(value):.1f}x")
    
    def play_midi(self):
        if not self.midi_file or self.is_playing:
            return
        
        self.is_playing = True
        self.stop_flag = False
        self.play_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Playing...", fg="blue")
        
        # Run in separate thread to not freeze GUI
        thread = threading.Thread(target=self.play_midi_thread)
        thread.daemon = True
        thread.start()
    
    def play_midi_thread(self):
        try:
            midi = mido.MidiFile(self.midi_file)
            speed_multiplier = self.speed_slider.get()
            
            for msg in midi.play():
                if self.stop_flag:
                    break
                
                # Adjust timing based on speed multiplier
                if msg.time > 0:
                    time.sleep(msg.time / speed_multiplier)
                
                # Process note_on messages
                if msg.type == 'note_on' and msg.velocity > 0:
                    if msg.note in NOTE_MAP:
                        key = NOTE_MAP[msg.note]
                        keyboard.press(key)
                        keyboard.release(key)
                
                # Process note_off messages
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    pass  # Key already released after press
            
            self.root.after(0, self.playback_finished)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(
                text=f"Error: {str(e)}", fg="red"
            ))
            self.root.after(0, self.playback_finished)
    
    def stop_midi(self):
        if not self.is_playing:
            return
        self.stop_flag = True
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Stopping...", fg="orange")
    
    def playback_finished(self):
        self.is_playing = False
        self.play_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        if not self.stop_flag:
            self.status_label.config(text="Playback finished", fg="green")
        else:
            self.status_label.config(text="Stopped", fg="orange")

# Create and run GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = MidiPlayerGUI(root)
    root.mainloop()
