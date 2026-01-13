"""
╔════════════════════════════════════════════════════════════════╗
║          JARVIS SCREEN CLIPPER - Code Annoté Complet           ║
║     Reconnaissance vocale + Enregistrement écran 30 secondes    ║
╚════════════════════════════════════════════════════════════════╝

STRUCTURE DU CODE :
1. ScreenRecorder → Gère l'enregistrement d'écran + buffer
2. PerformanceMonitor → Mesure CPU/RAM en temps réel
3. VoiceCommandListener → Écoute les commandes vocales
4. Main execution → Lance tout

"""

import speech_recognition as sr
import cv2
import threading
import time
import os
import psutil
from collections import deque
from datetime import datetime
import numpy as np
import mss
import mss.tools


# ════════════════════════════════════════════════════════════════
# CLASSE 1 : PerformanceMonitor
# ════════════════════════════════════════════════════════════════

class PerformanceMonitor:
    """
    Classe qui mesure les performances du programme en temps réel.
    
    - CPU : pourcentage du processeur utilisé
    - RAM : mémoire utilisée en MB
    - FPS : frames par seconde (vitesse d'enregistrement)
    
    Exécutée dans un thread séparé pour ne pas ralentir le programme.
    """
    
    def __init__(self, update_interval=2):
        """
        update_interval : affiche les stats tous les N secondes
        """
        self.running = False
        self.update_interval = update_interval
        self.stats = {
            'cpu_percent': 0,
            'ram_mb': 0,
            'fps': 0,
            'frame_count': 0,
            'start_time': time.time()
        }
        self.lock = threading.Lock()
    
    def start(self):
        """Lance le monitoring dans un thread"""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Arrête le monitoring"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=2)
    
    def _monitor_loop(self):
        """
        Boucle infinie qui mesure CPU/RAM toutes les N secondes.
        Exécutée dans un thread séparé.
        """
        process = psutil.Process(os.getpid())
        last_display_time = time.time()
        
        while self.running:
            try:
                # Mesure CPU (interval=1 = moyenne sur 1 seconde)
                cpu_percent = process.cpu_percent(interval=1)
                
                # Mesure RAM en MB (rss = mémoire résident)
                ram_info = process.memory_info()
                ram_mb = ram_info.rss / (1024 * 1024)  # Convertir bytes → MB
                
                # Enregistre les données
                with self.lock:
                    self.stats['cpu_percent'] = cpu_percent
                    self.stats['ram_mb'] = ram_mb
                    
                    # Affiche les stats tous les update_interval secondes
                    current_time = time.time()
                    if current_time - last_display_time >= self.update_interval:
                        uptime = current_time - self.stats['start_time']
                        fps = self.stats['frame_count'] / uptime if uptime > 0 else 0
                        
                        print(f"\n📊 PERFORMANCE STATS (uptime: {uptime:.1f}s)")
                        print(f"   CPU: {cpu_percent:6.2f}% | RAM: {ram_mb:6.1f} MB | FPS: {fps:6.2f}")
                        print(f"   Frames: {self.stats['frame_count']} | Status: {'🔴 Recording' if self.running else '⏹️  Stopped'}")
                        
                        last_display_time = current_time
                
            except Exception as e:
                print(f"❌ Erreur monitoring: {e}")
                time.sleep(1)
    
    def update_frame_count(self):
        """Appelé chaque fois qu'un frame est capturé"""
        with self.lock:
            self.stats['frame_count'] += 1


# ════════════════════════════════════════════════════════════════
# CLASSE 2 : ScreenRecorder
# ════════════════════════════════════════════════════════════════

class ScreenRecorder:
    """
    Enregistre l'écran en continu dans un buffer circulaire.
    
    CONCEPT : 
    - Au lieu de sauvegarder chaque frame directement,
    - On garde un "buffer" des 30 dernières secondes
    - Quand la commande est détectée, on sauvegarde ce buffer
    
    BUFFER CIRCULAIRE :
    - `deque(maxlen=N)` : liste de taille fixe
    - Quand on atteint la limite, le plus ancien élément est supprimé
    - Quand on ajoute un nouveau, l'ancien tombe
    """
    
    def __init__(self, fps=20, duration=30, performance_monitor=None):
        """
        fps : frames par seconde (20 = bon compromis perfs/qualité)
        duration : secondes du buffer (30 = 30 dernières secondes)
        performance_monitor : objet pour mesurer les perfs
        
        Calcul du buffer :
        - Si fps=20 et duration=30 : 20 * 30 = 600 frames en mémoire
        - Chaque frame ≈ 1920x1080x3 bytes (RGB) ≈ 6-8 MB
        - Total ≈ 600 * 7 MB = ~4.2 GB si non compressé
        - Avec compression : ~100-200 MB (acceptable)
        """
        self.fps = fps
        self.duration = duration
        self.max_frames = fps * duration
        
        # Buffer circulaire : gardera exactement max_frames frames
        self.frame_buffer = deque(maxlen=self.max_frames)
        
        self.recording = False
        self.monitor = performance_monitor
        
        # Codec vidéo pour mp4
        # 'mp4v' = H.264 codec (bon compromis compression/compatibilité)
        self.fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        # Dimensions d'écran (seront mises à jour à l'exécution)
        self.frame_width = 1920
        self.frame_height = 1080

    def record_screen(self):
        """
        Capture l'écran (ou un écran précis) en continu avec mss.
        """
        print("🎥 Initialisation capture d'écran avec mss...")

        try:
            with mss.mss() as sct:
                monitors = sct.monitors  # monitors[0] = tout, monitors[1], monitors[2] = écrans
                # CHOIX DE L'ÉCRAN :
                # - monitors[0] = tous les écrans assemblés
                # - monitors[1] = écran principal
                # - monitors[2] = second écran (si tu veux celui‑là)
                monitor = monitors[1]   # mets 1 ou 2 si tu veux un écran spécifique

                scale = 0.5  # ou 0.4 si besoin

                self.frame_width = int(monitor["width"] * scale)
                self.frame_height = int(monitor["height"] * scale)

                print("✓ Capture d'écran active (mss)")
                print(f"  Zone : {self.frame_width}x{self.frame_height}")
                print(f"  Buffer : {self.max_frames} frames = {self.duration}s @ {self.fps} FPS")

                frame_count = 0
                start_time = time.time()

                while self.recording:
                    # Grab un screenshot brut
                    sct_img = sct.grab(monitor)

                    # Convertit en tableau numpy (BGRA → BGR pour OpenCV)
                    frame = np.array(sct_img)[:, :, :3]   # BGRA → BGR
                    frame = cv2.resize(frame, (self.frame_width, self.frame_height))

                    # Ajoute au buffer
                    self.frame_buffer.append(frame)
                    frame_count += 1

                    if self.monitor:
                        self.monitor.update_frame_count()

                    # Contrôle FPS
                    frame_time = time.time() - start_time
                    target_time = frame_count / self.fps
                    sleep_time = target_time - frame_time
                    if sleep_time > 0:
                        time.sleep(sleep_time)

        except Exception as e:
            print(f"❌ Exception dans record_screen (mss): {e}")
        finally:
            print("🛑 Enregistrement écran arrêté (mss)")


    def save_buffer_to_file(self, filename):
        """Sauvegarde le buffer actuel dans un fichier vidéo MP4."""
        # On fige le contenu du buffer dans une liste pour éviter toute mutation
        frames = list(self.frame_buffer)
        print(f"DEBUG: nb frames dans le buffer au moment du clip = {len(frames)}")

        if not frames:
            print("❌ Le buffer est vide! Rien à sauvegarder.")
            return

        try:
            frame_height, frame_width = frames[0].shape[:2]
            out = cv2.VideoWriter(
                filename,
                self.fourcc,
                self.fps,
                (frame_width, frame_height)
            )

            if not out.isOpened():
                print("❌ Erreur : impossible de créer le fichier vidéo")
                return

            for i, frame in enumerate(frames):
                out.write(frame)
                if (i + 1) % 100 == 0:
                    percent = (i + 1) / len(frames) * 100
                    print(f"   Progression : {percent:5.1f}% ({i + 1}/{len(frames)})")

            out.release()

            file_size_mb = os.path.getsize(filename) / (1024 * 1024)
            print(f"✅ Vidéo sauvegardée avec succès!")
            print(f"   📁 Fichier : {filename}")
            print(f"   📊 Taille : {file_size_mb:.2f} MB")
            print(f"   ⏱️  Durée : {len(frames) / self.fps:.1f} secondes")

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde : {e}")



# ════════════════════════════════════════════════════════════════
# CLASSE 3 : VoiceCommandListener
# ════════════════════════════════════════════════════════════════

class VoiceCommandListener:
    """
    Écoute les commandes vocales via le microphone.
    
    PROCESS :
    1. Initialise le recognizer (Google Speech Recognition)
    2. Boucle infinie : écoute l'audio
    3. Envoie à Google API pour reconnaissance
    4. Si "jarvis" ET "clip" détectés → trigger le clip
    
    LATENCE :
    - Envoyer à Google : ~500-1000ms
    - Reconnaitre : ~500-2000ms
    - Total : ~1-3 secondes entre la parole et l'action
    """
    
    def __init__(self, recorder, language="fr-FR"):
        """
        recorder : instance ScreenRecorder
        language : code langue (fr-FR = français)
        """
        self.recorder = recorder
        self.language = language
        
        # Google Speech Recognition
        self.recognizer = sr.Recognizer()
        
        # Microphone par défaut
        self.microphone = sr.Microphone()
        
        # Ajuste le recognizer au bruit ambiant
        # À lancer une fois, pas à chaque itération!
        print("🎤 Calibrage du microphone...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✓ Microphone calibré")
        except Exception as e:
            print(f"⚠️  Attention : {e}")
    
    def listen_for_command(self):
        """
        Boucle infinie d'écoute vocale.
        
        TIMEOUT :
        - timeout=1 → écoute 1 seconde max avant timeout
        - phrase_time_limit=10 → la phrase peut durer max 10 secondes
        """
        print("\n🎤 Écoute vocale activée...")
        print("   Dis : 'Jarvis, clip ça !'")
        print("   (Appuie Ctrl+C pour arrêter)\n")
        
        with self.microphone as source:
            try:
                # Boucle écoute
                while self.recorder.recording:
                    try:
                        # Écoute un audio (timeout court = moins de lag)
                        print("⏳ Écoute...", end='\r')
                        audio = self.recognizer.listen(
                            source,
                            timeout=1,
                            phrase_time_limit=10
                        )
                        print("        ", end='\r')  # Efface "Écoute..."
                        
                    except sr.UnknownValueError:
                        # Pas d'audio détecté
                        continue
                    except sr.RequestError as e:
                        # Erreur réseau (pas Internet?)
                        print(f"\n⚠️  Erreur réseau : {e}")
                        continue
                    except sr.WaitTimeoutError:
                        # Timeout normal = pas d'audio
                        continue
                    
                    try:
                        # Envoie l'audio à Google pour reconnaissance
                        # language="fr-FR" → français
                        text = self.recognizer.recognize_google(
                            audio,
                            language=self.language
                        )
                        
                        # Affiche ce qui a été reconnu
                        print(f"🗣️  Détecté : \"{text}\"")
                        
                        # Vérifie si c'est la commande
                        text_lower = text.lower()
                        if "jarvis" in text_lower and "clip" in text_lower:
                            print("\n✅ COMMANDE DÉTECTÉE!")
                            self.on_command_detected()
                    
                    except sr.UnknownValueError:
                        print("❌ Texte non compris (essaie de parler plus fort)")
                    except sr.RequestError as e:
                        print(f"❌ Erreur API Google : {e}")
            
            except KeyboardInterrupt:
                print("\n🛑 Écoute arrêtée par l'utilisateur")
            except Exception as e:
                print(f"❌ Erreur dans listen_for_command: {e}")
    
    def on_command_detected(self):
        """
        Appelé quand la commande "Jarvis, clip ça !" est détectée.
        """
        # Génère un nom de fichier unique avec timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"clip_{timestamp}.mp4"
        
        # Affiche les infos
        print(f"\n🎬 Sauvegarde du clip...")
        print(f"   Timestamp : {timestamp}")
        
        # Sauvegarde le buffer
        self.recorder.save_buffer_to_file(filename)


# ════════════════════════════════════════════════════════════════
# MAIN : Exécution du programme
# ════════════════════════════════════════════════════════════════

def main():
    """
    Point d'entrée du programme.
    
    STRUCTURE :
    1. Crée les instances des classes
    2. Lance le monitoring
    3. Lance l'enregistrement d'écran dans un thread
    4. Lance l'écoute vocale (bloquant) dans le thread principal
    5. À l'arrêt : nettoie tout
    """
    
    print("\n" + "=" * 60)
    print("  🎤 JARVIS SCREEN CLIPPER")
    print("  Reconnaissance vocale + Enregistrement écran")
    print("=" * 60 + "\n")
    
    try:
        # ─── INITIALISATION ───
        
        # Crée le monitor de performance
        monitor = PerformanceMonitor(update_interval=2)
        monitor.start()
        
        # Crée l'enregistreur d'écran
        # fps=15 : si tu as une machine lente, réduis à 10
        # fps=20 : bonne qualité
        # fps=30 : très gourmand
        recorder = ScreenRecorder(fps=20, duration=30, performance_monitor=monitor)
        
        # Crée l'écouteur vocal
        listener = VoiceCommandListener(recorder)
        
        # ─── DÉMARRAGE ───
        
        # Lance l'enregistrement d'écran dans un thread
        # daemon=True = le thread s'arrête quand le programme se ferme
        recorder.recording = True
        screen_thread = threading.Thread(
            target=recorder.record_screen,
            daemon=True,
            name="ScreenRecorderThread"
        )
        screen_thread.start()
        
        # Attend 2 secondes que le buffer se remplisse un peu
        print("⏳ Attente de l'initialisation...\n")
        time.sleep(2)
        
        # Lance l'écoute vocale (bloquant = le reste du code attend)
        # Cette boucle continue jusqu'à Ctrl+C
        listener.listen_for_command()
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du programme...")
    
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # ─── NETTOYAGE ───
        print("\n🧹 Nettoyage...")
        
        # Arrête l'enregistrement
        recorder.recording = False
        
        # Attend que le thread d'enregistrement se termine
        screen_thread.join(timeout=5)
        
        # Arrête le monitoring
        monitor.stop()
        
        print("✅ Programme terminé proprement\n")


# ════════════════════════════════════════════════════════════════
# EXÉCUTION
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
