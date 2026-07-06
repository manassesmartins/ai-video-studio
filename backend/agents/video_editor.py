import os
from .base import BaseAgent


class VideoEditor(BaseAgent):
    def __init__(self, api_key: str):
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
            api_key=api_key
        )

    async def compose_video(self, audio_file: str, images: list, output_filename: str = "final_video.mp4") -> str:
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

            audio_clip = AudioFileClip(audio_file)
            audio_duration = audio_clip.duration

            img_duration = audio_duration / max(len(valid_images), 1)
            clips = []

            for i, img_info in enumerate(valid_images):
                img_path = img_info["local_path"]
                credit = img_info.get("credit", "")

                img_clip = ImageClip(img_path).with_duration(img_duration)

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
                    ], size=img_clip.size)
                    clips.append(composite)
                except Exception as e:
                    self.log_action(f"Aviso: erro ao criar overlay para imagem {i}: {e}")
                    clips.append(img_clip)

            if not clips:
                from moviepy import ColorClip
                bg = ColorClip(size=(1920, 1080), color=(30, 30, 30), duration=audio_duration)
                text_overlay = TextClip(
                    text="RESUMO DE NOTICIAS DE TECNOLOGIA",
                    font_size=60, color="white", font="Arial"
                ).with_duration(audio_duration).with_position("center")
                clips = [CompositeVideoClip([bg, text_overlay], size=(1920, 1080))]

            final = concatenate_videoclips(clips, method="compose")
            final = final.with_audio(audio_clip)
            final = final.resized(width=1920)

            self.log_action("Renderizando video final...")
            final.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile_path=os.path.join(output_dir, "temp-audio.m4a"),
                remove_temp=True,
                logger=None
            )

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
            opening.write_videofile(opening_path, fps=24, codec="libx264", logger=None)
            opening.close()

            self.log_action("Abertura criada!")
            self.set_status("idle")
            return opening_path
        except Exception as e:
            self.log_action(f"Erro ao criar abertura: {e}")
            self.set_status("idle")
            return ""
