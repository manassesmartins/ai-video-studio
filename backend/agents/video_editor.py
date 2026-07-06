import os
import time
import glob
import shutil
import tempfile
import random

from .base import BaseAgent


class VideoEditor(BaseAgent):
    def __init__(self, config: dict = None):
        system_prompt = """Você é um Editor de Vídeo profissional especializado em:

1. Criar vídeos atraentes para YouTube com transições suaves
2. Combinar imagens, áudio e texto em produções coesas
3. Adicionar créditos e atribuições corretamente
4. Otimizar a duração e ritmo do vídeo
5. Criar aberturas e encerramentos profissionais

HABILIDADES TÉCNICAS:
- Edição com moviepy (Python)
- Transições entre cenas
- Sincronização de áudio com imagens
- Legendas e sobreposições de texto
- Geração de vídeo final em MP4"""
        super().__init__(
            name="Editor",
            role="Editor de Vídeo",
            system_prompt=system_prompt,
            config=config
        )

    def _detect_vaapi_device(self) -> str | None:
        devices = sorted(glob.glob("/dev/dri/renderD*"))
        for dev in devices:
            if os.access(dev, os.R_OK | os.W_OK):
                return dev
        return None

    def _gpu_codec_and_wrapper(self, codec: str) -> tuple:
        gpu_accel = self.config.get("gpu_accel", False)
        if not gpu_accel:
            return codec, None
        supported = {"libx264": "h264_vaapi", "libx265": "hevc_vaapi", "h264_vaapi": "h264_vaapi", "hevc_vaapi": "hevc_vaapi"}
        gpu_codec = supported.get(codec)
        if not gpu_codec:
            self.log_action(f"GPU não suportada para codec {codec}")
            return codec, None
        dev = self._detect_vaapi_device()
        if not dev:
            self.log_action("Dispositivo VAAPI não encontrado, usando CPU")
            return codec, None
        self.log_action(f"GPU VAAPI ativada: {dev}")

        wrapper_path = os.path.join(tempfile.gettempdir(), "ffmpeg-vaapi-wrapper.sh")
        ffmpeg_bin = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        with open(wrapper_path, "w") as f:
            f.write(f'''#!/bin/bash
ARGS=()
VAAPI_OK=0
for arg in "$@"; do
    if [ "$arg" = "-i" ] && [ $VAAPI_OK -eq 0 ]; then
        ARGS+=(-vaapi_device {dev})
        VAAPI_OK=1
    fi
    ARGS+=("$arg")
done
if [ $VAAPI_OK -eq 1 ]; then
    LAST="${{ARGS[-1]}}"
    unset ARGS[-1]
    ARGS+=(-vf format=nv12,hwupload "$LAST")
fi
exec {ffmpeg_bin} "${{ARGS[@]}}"
''')
        os.chmod(wrapper_path, 0o755)
        return gpu_codec, wrapper_path

    def _create_srt(self, segments, total_duration, output_path):
        """Cria arquivo .srt a partir dos segmentos."""
        if not segments:
            return ""
        dur_per_seg = total_duration / max(len(segments), 1)
        lines = []
        for i, seg in enumerate(segments):
            start = i * dur_per_seg
            end = (i + 1) * dur_per_seg
            text = seg.get("narration", seg.get("title", ""))[:200]
            def srt_ts(secs):
                h = int(secs // 3600)
                m = int((secs % 3600) // 60)
                s = int(secs % 60)
                ms = int((secs - int(secs)) * 1000)
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            lines.append(f"{i+1}\n{srt_ts(start)} --> {srt_ts(end)}\n{text}\n")
        srt_path = output_path.rsplit(".", 1)[0] + ".srt"
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return srt_path

    async def compose_video(self, audio_file: str, images: list, fmt: dict = None,
                              output_filename: str = "final_video.mp4", segments: list = None) -> str:
        self.set_status("composing")
        self.log_action("Compondo o vídeo final...")

        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "videos")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, output_filename)

        if not os.path.exists(audio_file):
            self.log_action(f"Arquivo de audio nao encontrado: {audio_file}")
            self.set_status("idle")
            return ""

        valid_images = [img for img in images if img.get("local_path") and os.path.exists(img.get("local_path", ""))]
        self.log_action(f"Usando {len(valid_images)} imagens e audio: {audio_file}")

        await self.think(f"""
O video final sera composto com:
- Audio de narracao: {audio_file}
- {len(valid_images)} imagens de noticias
- Creditos inclusos

Descreva brevemente como sera a composicao do video final.
""")

        try:
            from moviepy import (AudioFileClip, ImageClip, CompositeVideoClip, TextClip, concatenate_videoclips)

            if audio_file and os.path.exists(audio_file):
                audio_clip = AudioFileClip(audio_file)
                audio_duration = audio_clip.duration
            else:
                audio_clip = None
                audio_duration = max(len(valid_images), 1) * 5  # 5s por imagem sem áudio

            v_fmt = (fmt or {}).get("video", {})
            a_fmt = (fmt or {}).get("audio", {})
            i_fmt = (fmt or {}).get("image", {})
            vid_w = v_fmt.get("width", 1920)
            vid_h = v_fmt.get("height", 1080)
            vid_fps = v_fmt.get("fps", 24)
            vid_codec = v_fmt.get("codec", "libx264")
            vid_bitrate = v_fmt.get("bitrate", "5000k")
            vid_ext = v_fmt.get("format", "mp4")
            aud_codec = a_fmt.get("codec", "aac")
            img_w = i_fmt.get("width", 1920)
            img_h = i_fmt.get("height", 1080)

            output_filename = f"video_{int(time.time())}.{vid_ext}"
            output_path = os.path.join(output_dir, output_filename)

            img_duration = audio_duration / max(len(valid_images), 1)
            clips = []

            for i, img_info in enumerate(valid_images):
                img_path = img_info["local_path"]
                credit = img_info.get("credit", "")

                img_clip = ImageClip(img_path).resized(width=img_w, height=img_h).with_duration(img_duration)

                # Ken Burns: zoom lento
                try:
                    zoom = 1.0 + random.uniform(0.03, 0.12)
                    img_clip = (img_clip
                        .resized(lambda t: 1 + (zoom - 1) * t / max(img_duration, 0.01))
                        .with_position(lambda t: (
                            -((zoom - 1) * img_w * t / max(img_duration, 0.01)) / 2,
                            -((zoom - 1) * img_h * t / max(img_duration, 0.01)) / 2
                        )))
                except Exception:
                    pass

                try:
                    credit_txt = TextClip(
                        text=credit,
                        font_size=24,
                        color="white",
                        font="Arial",
                        stroke_color="black",
                        stroke_width=2,
                        method="caption",
                        size=(img_clip.w - 40, None)
                    ).with_duration(img_duration).with_position(("center", "bottom"))

                    title_txt = TextClip(
                        text=img_info.get("title", ""),
                        font_size=32,
                        color="white",
                        font="Arial",
                        stroke_color="black",
                        stroke_width=2,
                        method="caption",
                        size=(img_clip.w - 40, None)
                    ).with_duration(img_duration).with_position(("center", "top"))

                    composite = CompositeVideoClip([
                        img_clip,
                        title_txt,
                        credit_txt
                    ], size=(img_w, img_h))
                    clips.append(composite)
                except Exception as e:
                    self.log_action(f"Aviso: erro ao criar overlay para imagem {i}: {e}")
                    clips.append(img_clip)

            if not clips:
                from moviepy import ColorClip
                bg = ColorClip(size=(vid_w, vid_h), color=(30, 30, 30), duration=audio_duration)
                text_overlay = TextClip(
                    text="RESUMO DE NOTICIAS DE TECNOLOGIA",
                    font_size=60, color="white", font="Arial"
                ).with_duration(audio_duration).with_position("center")
                clips = [CompositeVideoClip([bg, text_overlay], size=(1920, 1080))]

            # Gera .srt com legendas
            if segments:
                srt_path = self._create_srt(segments, audio_duration, output_path)
                if srt_path:
                    self.log_action(f"Legendas salvas: {srt_path}")

            final = concatenate_videoclips(clips, method="compose")
            if audio_clip:
                final = final.with_audio(audio_clip)
            final = final.resized(width=vid_w, height=vid_h)

            gpu_codec, wrapper = self._gpu_codec_and_wrapper(vid_codec)
            if wrapper:
                self.log_action(f"Renderizando com GPU ({gpu_codec})...")
                import moviepy.video.io.ffmpeg_writer as fw
                original_ffmpeg = fw.FFMPEG_BINARY
                fw.FFMPEG_BINARY = wrapper
            else:
                self.log_action(f"Renderizando video final ({gpu_codec})...")
            try:
                final.write_videofile(
                    output_path,
                    fps=vid_fps,
                    codec=gpu_codec,
                    audio_codec=aud_codec if audio_clip else "aac",
                    bitrate=vid_bitrate,
                    temp_audiofile=os.path.join(output_dir, f"temp_{output_filename}.m4a"),
                    remove_temp=True,
                    logger=None
                )
            finally:
                if wrapper:
                    fw.FFMPEG_BINARY = original_ffmpeg

            if audio_clip:
                audio_clip.close()
            final.close()

            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                self.log_action(f"VIDEO FINAL CRIADO: {output_filename} ({file_size:.1f} MB)")
                self.set_status("idle")
                return output_path
            else:
                self.log_action("Erro: video nao foi gerado")
                self.set_status("idle")
                return ""

        except ImportError as e:
            self.log_action(f"Erro de importacao moviepy: {e}")
            self.set_status("idle")
            return ""
        except Exception as e:
            self.log_action(f"Erro na edicao do video: {e}")
            self.set_status("idle")
            return ""

    async def create_opening(self, duration: int = 5) -> str:
        self.set_status("creating_opening")
        self.log_action("Criando abertura do video...")

        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "videos")
        os.makedirs(output_dir, exist_ok=True)

        opening_path = os.path.join(output_dir, "opening.mp4")

        try:
            from moviepy import ColorClip, TextClip, CompositeVideoClip

            bg = ColorClip(size=(1920, 1080), color=(20, 30, 50), duration=duration)

            title = TextClip(
                text="RESUMO DE NOTICIAS\nDE TECNOLOGIA",
                font_size=80,
                color="white",
                font="Arial",
                method="caption",
                size=(1800, None)
            ).with_duration(duration).with_position("center")

            subtitle = TextClip(
                text="Apresentado por AI Studio",
                font_size=36,
                color="#88aaff",
                font="Arial",
                method="caption"
            ).with_duration(duration).with_position(("center", 0.7), relative=True)

            opening = CompositeVideoClip([bg, title, subtitle], size=(1920, 1080))
            gpu_codec, wrapper = self._gpu_codec_and_wrapper("libx264")
            if wrapper:
                import moviepy.video.io.ffmpeg_writer as fw
                original_ffmpeg = fw.FFMPEG_BINARY
                fw.FFMPEG_BINARY = wrapper
            try:
                opening.write_videofile(opening_path, fps=24, codec=gpu_codec, logger=None)
            finally:
                if wrapper:
                    fw.FFMPEG_BINARY = original_ffmpeg
            opening.close()

            self.log_action("Abertura criada!")
            self.set_status("idle")
            return opening_path
        except Exception as e:
            self.log_action(f"Erro ao criar abertura: {e}")
            self.set_status("idle")
            return ""
