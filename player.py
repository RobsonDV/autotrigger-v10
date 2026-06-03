"""
Player de áudio usando python-vlc.
Suporta arquivos locais (MP3, WAV, OGG...) e streams por URL, incluindo playlists M3U.
Requer VLC instalado no sistema.
"""
import threading
import time

try:
    import vlc
    VLC_AVAILABLE = True
except Exception:
    VLC_AVAILABLE = False

# Extensões de playlist que precisam de MediaListPlayer
_PLAYLIST_EXTS = (".m3u", ".m3u8", ".pls", ".xspf", ".asx")


class AudioPlayer:
    def __init__(self):
        self._instance = None
        self._player = None           # vlc.MediaPlayer
        self._list_player = None      # vlc.MediaListPlayer (para M3U/playlists)
        self._monitor_thread: threading.Thread | None = None
        self._stop_monitor = threading.Event()
        self._on_finished = None
        self._generation = 0          # evita callbacks de threads antigas
        self._output_device_id = ""   # ID MMDevice Windows do dispositivo de saída
        self._log = lambda msg, level="info": print(f"[Player][{level}] {msg}")

        if VLC_AVAILABLE:
            try:
                self._instance = vlc.Instance(
                    "--quiet",
                    "--no-video",
                    "--network-caching=8000",
                    "--live-caching=8000",
                    "--sout-mux-caching=8000",
                )
            except Exception as exc:
                print(f"[Player] Erro ao iniciar instância VLC: {exc}")

    # ── public API ────────────────────────────────────────────────────────────

    def is_vlc_available(self) -> bool:
        return VLC_AVAILABLE and self._instance is not None

    def set_output_device(self, device_id: str):
        """Define o dispositivo de saída Windows MMDevice para o VLC usar."""
        self._output_device_id = device_id

    def set_on_finished(self, callback):
        """Define callback chamado ao fim natural da mídia (não em stop() manual)."""
        self._on_finished = callback

    def set_log(self, callback):
        self._log = callback

    def play(self, source: str, duration_seconds: int = 0) -> bool:
        """
        Reproduz um arquivo local ou URL de stream/playlist.
        duration_seconds > 0 → usa timer fixo (para streaming online).
        Retorna True se iniciou sem erros.
        """
        if not self.is_vlc_available():
            self._log("VLC não disponível.", "error")
            return False

        self.stop()
        self._generation += 1
        gen = self._generation

        # Detecta se é playlist pelo final da URL (ignora query string)
        source_lower = source.lower().split("?")[0]
        is_playlist = source_lower.endswith(_PLAYLIST_EXTS)

        try:
            self._player = self._instance.media_player_new()

            # Configura dispositivo de saída ANTES de iniciar (síncrono)
            # Isso evita que o VLC abra o device padrão e depois mude,
            # o que causaria áudio duplicado na transição.
            if self._output_device_id:
                try:
                    self._player.audio_output_set("mmdevice")
                    self._player.audio_output_device_set(
                        "mmdevice", self._output_device_id
                    )
                except Exception as exc:
                    self._log(f"Aviso ao configurar saída de áudio: {exc}", "warn")

            if is_playlist:
                self._log(f"Modo playlist (M3U/PLS): {source}", "info")
                media_list = self._instance.media_list_new([source])
                self._list_player = self._instance.media_list_player_new()
                self._list_player.set_media_player(self._player)
                self._list_player.set_media_list(media_list)
                self._list_player.play()
            else:
                media = self._instance.media_new(source)
                self._player.set_media(media)
                self._player.play()

            self._stop_monitor.clear()
            self._monitor_thread = threading.Thread(
                target=self._monitor_playback,
                args=(duration_seconds, gen),
                daemon=True,
                name="player-monitor",
            )
            self._monitor_thread.start()
            return True

        except Exception as exc:
            self._log(f"Erro ao reproduzir '{source}': {exc}", "error")
            return False

    # ── internal ──────────────────────────────────────────────────────────────

    def _monitor_playback(self, duration_seconds: int, generation: int):
        """
        Modo STREAM (duration_seconds > 0):
          Aguarda VLC iniciar (máx 15s) → conta o tempo via sleep → chama on_finished.
          Loga status a cada 10s para diagnóstico.

        Modo ARQUIVO (duration_seconds == 0):
          Aguarda estado Ended/Error/Stopped do VLC → chama on_finished.
        """
        if duration_seconds > 0:
            # Aguarda início do stream
            self._log("Conectando ao stream...", "info")
            deadline = time.time() + 15.0
            started = False
            while time.time() < deadline and not self._stop_monitor.is_set():
                try:
                    st = self._player.get_state() if self._player else None
                except Exception:
                    break
                if st == vlc.State.Playing:
                    started = True
                    break
                if st == vlc.State.Error:
                    self._log("Erro VLC ao conectar ao stream. Verificar URL.", "error")
                    break
                time.sleep(0.3)

            if not started and not self._stop_monitor.is_set():
                self._log("Stream não iniciou no timeout — verificar URL/conexão.", "warn")
            elif started:
                self._log(f"Stream ativo. Tocando por {duration_seconds}s.", "success")

            # Conta o tempo via sleep (independente do estado VLC)
            elapsed = 0.0
            last_log_at = 0.0
            while elapsed < duration_seconds and not self._stop_monitor.is_set():
                time.sleep(0.5)
                elapsed += 0.5
                if elapsed - last_log_at >= 10.0:
                    last_log_at = elapsed
                    remaining = int(duration_seconds - elapsed)
                    m, s = divmod(remaining, 60)
                    try:
                        st = self._player.get_state() if self._player else "?"
                        st_name = st.name if hasattr(st, "name") else str(st)
                    except Exception:
                        st_name = "?"
                    self._log(f"Streaming... restam {m:02d}:{s:02d} | VLC: {st_name}", "info")
        else:
            # Arquivo local: aguarda fim natural
            time.sleep(0.5)
            while not self._stop_monitor.is_set():
                if self._player is None:
                    break
                try:
                    state = self._player.get_state()
                except Exception:
                    break
                if state in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
                    break
                time.sleep(0.2)

        # Só chama on_finished se não houve stop() manual e geração é válida
        if not self._stop_monitor.is_set() and self._generation == generation:
            self.stop()
            cb = self._on_finished
            if cb:
                cb()

    def stop(self):
        """Para a reprodução imediatamente."""
        self._stop_monitor.set()
        if self._list_player is not None:
            try:
                self._list_player.stop()
                self._list_player.release()
            except Exception:
                pass
            self._list_player = None
        if self._player is not None:
            try:
                self._player.stop()
                self._player.release()
            except Exception:
                pass
            self._player = None

    def is_playing(self) -> bool:
        if self._player is None:
            return False
        try:
            return self._player.get_state() == vlc.State.Playing
        except Exception:
            return False

    def release(self):
        """Libera todos os recursos VLC."""
        self.stop()
        if self._instance is not None:
            try:
                self._instance.release()
            except Exception:
                pass
            self._instance = None
