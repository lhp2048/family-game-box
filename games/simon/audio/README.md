# Simon Says 语音素材

部分 Android 平板内置 WebView **不支持** `speechSynthesis`，需要预置 MP3。

## 生成

在仓库根目录执行（用项目 `.venv`，不要用系统 `pip`）：

```bash
cd /Users/muxin/Desktop/family-smart/family-game-box
.venv/bin/pip install edge-tts
.venv/bin/python games/simon/gen_audio.py
.venv/bin/python games/simon/generate.py
```

会生成 12 个文件：

- `hands_up.mp3` … `squat.mp3`（无「老师说」）
- `say_hands_up.mp3` … `say_squat.mp3`（有「老师说」）

播放优先级：预置 MP3 → 系统 TTS → 仅文字高亮提示。
