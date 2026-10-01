# Stroop 语音素材

部分 Android 平板内置 WebView **不支持** `speechSynthesis`，预置 MP3 播报字义（如「红色」）。

## 生成

```bash
.venv/bin/pip install edge-tts
.venv/bin/python games/stroop/gen_audio.py
.venv/bin/python games/stroop/generate.py
```

共 8 个文件：`red.mp3` … `white.mp3`。
