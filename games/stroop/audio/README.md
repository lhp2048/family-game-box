# Stroop 语音素材

播报玩法：试次只显示墨色色块，语音播报颜色名作干扰。

## 生成

```bash
.venv/bin/pip install edge-tts
.venv/bin/python games/stroop/gen_audio.py
.venv/bin/python games/stroop/generate.py
```

共 8 个文件：`red.mp3` … `white.mp3`（内容为「红色」等）。
