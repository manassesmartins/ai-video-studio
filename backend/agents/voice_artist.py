import os
from gtts import gTTS
from .base import BaseAgent


class VoiceArtist(BaseAgent):
    def __init__(self, api_key: str):
        system_prompt = """Você é um Artista de Voz / Locutor profissional.

SUAS HABILIDADES:
1. Converter textos em áudio com dicção clara e ritmo adequado
2. Dividir o roteiro em segmentos para melhor organização do áudio
3. Garantir que a narração soe natural e envolvente
4. Sugerir entonações e pausas para melhor experiência do ouvinte

Você trabalha com o Google TTS (gTTS) para gerar áudio em português do Brasil.
Sempre verifique a qualidade do áudio gerado."""
        super().__init__(
            name="Locutor",
            role="Artista de Voz",
            system_prompt=system_prompt,
            api_key=api_key
        )

    async def text_to_speech(self, text: str, filename: str, lang: str = "pt-br") -> str:
        self.set_status("recording")
        self.log_action(f"Gravando áudio: {filename}...")

        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "audio")
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(filepath)
            self.log_action(f"✅ Áudio salvo: {filename} ({os.path.getsize(filepath)} bytes)")
            self.set_status("idle")
            return filepath
        except Exception as e:
            self.log_action(f"❌ Erro ao gerar áudio: {str(e)}")
            self.set_status("idle")
            return ""

    async def generate_narration(self, segments: list, output_name: str = "narration") -> dict:
        self.set_status("planning")
        self.log_action("Planejando a gravação da narração...")

        audio_files = {}
        full_narration = []

        for i, segment in enumerate(segments):
            narration_text = segment.get("narration", "")

            if not narration_text:
                continue

            full_narration.append(narration_text)

        joined_text = "\n\n".join(full_narration)

        self.set_status("recording")
        self.log_action("Gerando áudio completo da narração...")

        intro_text = "Olá pessoal! Sejam bem-vindos ao nosso resumo de notícias de tecnologia. "
        intro_text += "Vamos conferir as principais novidades do mundo tech hoje. "
        intro_text += joined_text[:4900]

        main_audio = await self.text_to_speech(intro_text, f"{output_name}_full.mp3")
        audio_files["full"] = main_audio

        for i, segment in enumerate(segments):
            seg_text = segment.get("narration", "")
            if len(seg_text) > 10:
                seg_file = await self.text_to_speech(
                    seg_text[:4900],
                    f"{output_name}_segment_{i}.mp3"
                )
                audio_files[f"segment_{i}"] = seg_file

        self.log_action(f"✅ Geração de áudio concluída! {len(audio_files)} arquivos")
        self.set_status("idle")
        return audio_files
