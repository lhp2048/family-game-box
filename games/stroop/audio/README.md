# Stroop 语音素材

每题固定播报字义（如「红色」），与屏幕彩色汉字同步，不可关闭。

## 生成

```bash
.venv/bin/pip install edge-tts
.venv/bin/python games/stroop/gen_audio.py
.venv/bin/python games/stroop/generate.py
```

共 8 个文件：`red.mp3` … `white.mp3`。
