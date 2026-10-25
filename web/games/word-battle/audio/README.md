# 单词大作战 · 字母读音素材

26 个美式英语**字母名**（A–Z），**同一女声**连续录制后分轨，语气清晰偏利落。

## 来源与许可

| 项目 | 说明 |
| --- | --- |
| **作者** | [ChotoTheBright](https://freesound.org/people/ChotoTheBright/) |
| **录音** | Freesound [**Alphabet-English.wav**](https://freesound.org/people/ChotoTheBright/sounds/700028/)（sound ID **700028**，一次性朗读 A–Z） |
| **许可** | [**CC0 1.0**](https://creativecommons.org/publicdomain/zero/1.0/) — 可任意使用、修改与再分发，**无需署名**（建议仍保留本说明） |
| **本仓库处理** | 下载 Freesound **HQ preview** MP3 → `silencedetect` 切为 26 段 → ffmpeg 裁静音并略提音量（约 1.14×） |

（此前使用的 tim.kahn pack 4371 已替换为本音源。）

## 生成 / 更新

```bash
python3 games/word_battle/fetch_audio.py
python3 games/word_battle/generate.py   # 同步到 web/games/word-battle/audio/
```

文件命名：`a.mp3` … `z.mp3`（与 `FgbAudioClips` 的 `clipIds` 一致）。

## 整词读音

游戏**不**播报整词，仅字母 MP3 + 拼写输入。
