import os
from gtts import gTTS
from .base import BaseAgent


class VoiceArtist(BaseAgent):
    def __init__(self, config: dict = None):
        system_prompt = """Você é um Artista de Voz / Locutor profissional.

SUAS HABILIDADES:
1. Converter textos em áudio com dicção clara e ritmo adequado
2. Dividir o roteiro em segmentos para melhor organização do áudio
3. Garantir que a narração soe natural e envolvente
4. Sugerir entonações e pausas para melhor experiência do ouvinte

Você trabalha com sistemas de TTS para gerar áudio em português do Brasil.
Sempre verifique a qualidade do áudio gerado."""
        super().__init__(
            name="Locutor",
            role="Artista de Voz",
            system_prompt=system_prompt,
            config=config
        )

    def _audio_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "output", "audio")

    async def text_to_speech(self, text: str, filename: str, lang: str = "pt-br",
                              voice: str = None, model: str = None) -> str:
        self.set_status("recording")
        self._report("Gerando áudio...", 20)

        os.makedirs(self._audio_dir(), exist_ok=True)
        filepath = os.path.join(self._audio_dir(), filename)

        voice = voice or self.config.get("voice", "pt-BR-FranciscaNeural")

        self.log_action(f"Gerando áudio (voz={voice})...")

        if voice:
            try:
                import edge_tts
                self._report("Gerando com Edge TTS...", 40)
                communicate = edge_tts.Communicate(text[:4000], voice)
                await communicate.save(filepath)
                if os.path.getsize(filepath) > 100:
                    self.log_action(f"Edge TTS: áudio salvo ({os.path.getsize(filepath)} bytes)")
                    self._report("Áudio concluído", 100)
                    self.set_status("idle")
                    return filepath
                self.log_action("Edge TTS retornou áudio vazio, fallback para gTTS")
            except ImportError:
                self.log_action("edge-tts não instalado, fallback para gTTS")
            except Exception as e:
                self.log_action(f"Edge TTS falhou ({e}), fallback para gTTS")
        else:
            self.log_action("Nenhuma voz configurada, usando gTTS")

        try:
            self._report("Gerando com gTTS...", 40)
            tts = gTTS(text=text[:4000], lang=lang, slow=False)
            tts.save(filepath)
            self.log_action(f"gTTS: áudio salvo ({os.path.getsize(filepath)} bytes)")
            self._report("Áudio concluído", 100)
            self.set_status("idle")
            return filepath
        except Exception as e:
            self.log_action(f"gTTS falhou: {e}")
            self._report("Erro no áudio", 0)
            self.set_status("idle")
            return ""

    async def test_voice(self, text: str = "Olá, esta é a nova voz do seu narrador.", voice: str = "pt-BR-FranciscaNeural", model: str = "") -> str:
        self.log_action(f"Testando voz: {voice}...")
        return await self.text_to_speech(text, "test_voice.mp3", voice=voice)

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

        intro_prompt = self.config.get("intro_prompt", "").strip()
        outro_prompt = self.config.get("outro_prompt", "").strip()

        if intro_prompt:
            full_text = intro_prompt
        else:
            full_text = "Olá pessoal! Sejam bem-vindos ao nosso resumo de notícias de tecnologia. Vamos conferir as principais novidades do mundo tech hoje."

        full_text += " " + joined_text

        if outro_prompt:
            full_text += " " + outro_prompt

        full_text = full_text[:4500]

        main_audio = await self.text_to_speech(full_text, f"{output_name}_full.mp3")
        audio_files["full"] = main_audio

        for i, segment in enumerate(segments):
            seg_text = segment.get("narration", "")
            if len(seg_text) > 10:
                seg_file = await self.text_to_speech(
                    seg_text[:4500],
                    f"{output_name}_segment_{i}.mp3"
                )
                audio_files[f"segment_{i}"] = seg_file

        self.log_action(f"Geração de áudio concluída! {len(audio_files)} arquivos")
        self.set_status("idle")
        return audio_files
