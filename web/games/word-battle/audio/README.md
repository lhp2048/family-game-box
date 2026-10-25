# 单词大作战 · 字母读音素材

26 个美式英语**字母名**（A–Z），用于拼读提示与敲对字母时的反馈。

## 来源与许可

| 项目 | 说明 |
| --- | --- |
| **来源** | [Wikimedia Commons](https://commons.wikimedia.org/wiki/Category:U.S._English_pronunciation_of_letters) — `En-us-*.ogg` 系列（如 [En-us-a.ogg](https://commons.wikimedia.org/wiki/File:En-us-a.ogg)） |
| **许可** | 上传者标注 **Public domain (PD-self)** / 自有作品，可自由复制、修改与再分发（含商业用途），无需署名（建议 README 保留本说明） |
| **格式** | 仓库内为 **MP3**（由 OGG 经 ffmpeg 转码，便于 WebView 播放） |

## 生成 / 更新素材

```bash
# 需网络 + ffmpeg
python3 games/word_battle/fetch_audio.py
python3 games/word_battle/generate.py   # 同步到 web/games/word-battle/audio/
```

文件命名：`a.mp3` … `z.mp3`（小写单字母 id，与 `FgbAudioClips` 的 `clipIds` 一致）。

## 整词读音

整词仍可使用浏览器 `speechSynthesis`（`en-US`）；若环境不支持则静默，不影响拼写。
