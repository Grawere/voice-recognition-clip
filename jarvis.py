import json
import threading
import sys
import os
import time

import keyboard
import pyaudio
from vosk import Model, KaldiRecognizer

import tkinter as tk
from tkinter import messagebox

import pystray
from PIL import Image, ImageDraw

# ================== CONFIG DE BASE ==================

CONFIG_FILE = "config.json"
DEFAULT_HOTKEY = "alt+f10"  # raccourci NVIDIA par défaut
MODEL_PATH = r"models/vosk-model-small-fr-0.22"  # à adapter si besoin

WAKE_WORDS = [    "jarvis",
                  "jar vis",
                  "jar bis",
                  "jar vise",
                  "jarvice",
                  "jar viss",
                  "jarviz",
                  "jar vix",
                  "jarviss",
                  "jarvisse",
                  "jarvisse",
                  "jarvisse",
                  "jervi",
                  "jervis",
                  "jervise",
                  "djervis",
                  "djervi",
]
CLIP_WORDS = ["clip",
              "clip ça",
              "clipe",
              "clipe ça",
              "clippe",
              "clippe ça",
              "clip sa",
              "klip",
              "klip ça",
              "clipe le",
              "clipe le clip",
              "clip là",
              "clip la",
              "skype",
              "skype ça"
]

AUDIO_RATE = 16000
AUDIO_CHUNK = 4096

# ================== GESTION CONFIG ==================


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"hotkey": DEFAULT_HOTKEY}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "hotkey" not in data:
            data["hotkey"] = DEFAULT_HOTKEY
        return data
    except Exception:
        return {"hotkey": DEFAULT_HOTKEY}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[CONFIG] Erreur sauvegarde config: {e}")


# ================== RECO VOSK ==================


class VoskListener(threading.Thread):
    def __init__(self, get_hotkey_fn, stop_event):
        super().__init__(daemon=True)
        self.get_hotkey = get_hotkey_fn
        self.stop_event = stop_event

        print("📦 Chargement du modèle Vosk...")
        if not os.path.isdir(MODEL_PATH):
            print(f"❌ MODELE MANQUANT : {MODEL_PATH}")
            print("   Décompresse le modèle Vosk FR ici ou adapte MODEL_PATH.")
            raise SystemExit(1)

        self.model = Model(MODEL_PATH)
        self.rec = KaldiRecognizer(self.model, AUDIO_RATE)
        self.rec.SetWords(True)
        print("✓ Modèle Vosk chargé")

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=AUDIO_RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK
        )
        self.stream.start_stream()
        print("✓ Micro ouvert")

    def run(self):
        print("\n🎤 Jarvis en écoute (offline Vosk)")
        print("   Dis : 'Jarvis, clip ça !'\n")

        try:
            while not self.stop_event.is_set():
                data = self.stream.read(AUDIO_CHUNK, exception_on_overflow=False)

                if self.rec.AcceptWaveform(data):
                    result_json = self.rec.Result()
                    try:
                        result = json.loads(result_json)
                    except Exception:
                        continue

                    text = (result.get("text") or "").strip()
                    if not text:
                        continue

                    text_lower = text.lower()
                    print(f"🗣️  Détecté : \"{text_lower}\"")

                    if (any(w in text_lower for w in WAKE_WORDS)
                            and any(w in text_lower for w in CLIP_WORDS)):
                        hotkey = self.get_hotkey()
                        print(f"\n✅ Commande détectée → envoi du raccourci : {hotkey}")
                        try:
                            keyboard.send(hotkey)
                            print("   ↳ Raccourci envoyé.\n")
                        except Exception as e:
                            print(f"❌ Erreur envoi raccourci : {e}\n")

        except Exception as e:
            print(f"❌ Erreur dans VoskListener: {e}")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()
            print("🛑 VoskListener arrêté proprement")


# ================== GUI TKINTER ==================


class JarvisGUI:
    def __init__(self, root, config, on_hotkey_change, on_quit):
        self.root = root
        self.config = config
        self.on_hotkey_change = on_hotkey_change
        self.on_quit = on_quit

        self.capturing_hotkey = False

        self.root.title("Jarvis - Clip")
        self.root.geometry("320x160")
        self.root.resizable(False, False)

        try:
            self.root.iconbitmap(default="")  # si tu ajoutes un .ico plus tard
        except Exception:
            pass

        frame = tk.Frame(root, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Raccourci clip :").pack(anchor="w")

        self.hotkey_var = tk.StringVar(value=self.config["hotkey"])
        self.hotkey_label = tk.Label(
            frame,
            textvariable=self.hotkey_var,
            font=("Segoe UI", 12, "bold")
        )
        self.hotkey_label.pack(pady=(0, 8))

        self.info_label = tk.Label(
            frame,
            text="Clique sur 'Changer la touche',\npuis tape la combinaison.",
            justify="left"
        )
        self.info_label.pack(pady=(0, 8))

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill="x")

        self.change_btn = tk.Button(
            btn_frame, text="Changer la touche",
            command=self.start_capture_hotkey
        )
        self.change_btn.pack(side="left", padx=(0, 5))

        quit_btn = tk.Button(
            btn_frame, text="Quitter",
            command=self.on_quit
        )
        quit_btn.pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.root.bind("<KeyPress>", self.on_key_press)

    def on_close(self):
        self.root.withdraw()

    def start_capture_hotkey(self):
        if self.capturing_hotkey:
            return
        self.capturing_hotkey = True
        self.info_label.config(text="Tape la combinaison...\n(par ex. Alt+F10)")
        self.hotkey_label.config(fg="blue")

        threading.Thread(target=self.capture_hotkey_thread, daemon=True).start()

    def capture_hotkey_thread(self):
        try:
            combo = keyboard.read_hotkey(suppress=False)
            if combo:
                self.root.after(0, self.finish_capture_hotkey, combo)
        except Exception as e:
            print(f"[GUI] Erreur capture hotkey: {e}")
            self.root.after(0, self.finish_capture_hotkey, None)

    def finish_capture_hotkey(self, combo):
        self.capturing_hotkey = False
        self.hotkey_label.config(fg="black")
        self.info_label.config(
            text="Clique sur 'Changer la touche',\npuis tape la combinaison."
        )

        if not combo:
            return

        self.config["hotkey"] = combo
        save_config(self.config)
        self.hotkey_var.set(combo)
        self.on_hotkey_change(combo)
        messagebox.showinfo("Jarvis", f"Nouveau raccourci : {combo}")

    def on_key_press(self, event):
        pass


# ================== SYSTRAY ==================


def create_tray_image():
    img = Image.new("RGB", (64, 64), "black")
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill="#1e90ff")
    d.text((22, 20), "J", fill="white")
    return img


# ================== MAIN ==================


def main():
    config = load_config()
    hotkey_lock = threading.Lock()
    current_hotkey = {"value": config["hotkey"]}

    def get_hotkey():
        with hotkey_lock:
            return current_hotkey["value"]

    def set_hotkey(new_hotkey):
        with hotkey_lock:
            current_hotkey["value"] = new_hotkey
        print(f"[CONFIG] Hotkey mis à jour : {new_hotkey}")

    stop_event = threading.Event()

    listener = VoskListener(get_hotkey_fn=get_hotkey, stop_event=stop_event)
    listener.start()

    root = tk.Tk()
    gui = JarvisGUI(
        root,
        config=config,
        on_hotkey_change=set_hotkey,
        on_quit=lambda: quit_all(root, stop_event)
    )
    root.withdraw()  # fenêtre cachée au démarrage

    def on_tray_show(icon, item):
        root.after(0, root.deiconify)  # n’ouvre la fenêtre que sur clic menu

    def on_tray_quit(icon, item):
        root.after(0, lambda: quit_all(root, stop_event))
        icon.stop()

    icon = pystray.Icon(
        "Jarvis",
        create_tray_image(),
        "Jarvis - Clip",
        menu=pystray.Menu(
            pystray.MenuItem("Ouvrir", on_tray_show),
            pystray.MenuItem("Quitter", on_tray_quit)
        )
    )

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    # NE PAS déiconifier au démarrage
    # root.deiconify()

    try:
        root.mainloop()
    finally:
        stop_event.set()
        time.sleep(0.5)
        print("✅ Jarvis terminé.")



def quit_all(root, stop_event):
    if messagebox.askokcancel("Quitter Jarvis", "Arrêter Jarvis et quitter ?"):
        stop_event.set()
        root.destroy()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
