# 单词大作战 · 字母读音素材

26 个美式英语**字母名**（A–Z），**同一女声**、语气偏柔和，用于拼读与敲对字母时的反馈。

## 来源与许可

| 项目 | 说明 |
| --- | --- |
| **作者** | [tim.kahn](https://freesound.org/people/tim.kahn/) |
| **合集** | Freesound pack [**The Alphabet**](https://freesound.org/people/tim.kahn/packs/4371/)（`a.wav` … `z.wav`，女声） |
| **Sound ID** | `67712`（a）… `67737`（z） |
| **许可** | [**CC BY 4.0**](https://creativecommons.org/licenses/by/4.0/) — 可再分发与修改，**须署名** |
| **署名建议** | Letter sounds by tim.kahn (Freesound), CC BY 4.0 — https://freesound.org/people/tim.kahn/packs/4371/ |

本仓库中的 MP3 由 Freesound **HQ preview**（或可选 API 下载的原始 WAV）经 ffmpeg **`silenceremove` 裁掉首尾静音** + 略提音量（约 1.12×）后生成，单字母约 **0.4–0.7s**，拼读更利落。

## 生成 / 更新

```bash
# 默认：从 Freesound CDN 拉取 HQ preview（无需账号）
python3 games/word_battle/fetch_audio.py

# 可选：下载原始 WAV（需 Freesound API token）
FREESOUND_API_KEY=... python3 games/word_battle/fetch_audio.py

python3 games/word_battle/generate.py   # 同步到 web/games/word-battle/audio/
```

文件命名：`a.mp3` … `z.mp3`（与 `FgbAudioClips` 的 `clipIds` 一致）。

## 整词读音

游戏**不**播报整词，仅字母 MP3 + 拼写输入。
