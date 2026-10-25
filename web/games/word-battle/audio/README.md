# 单词大作战 · 字母读音素材

26 个美式英语**字母名**（A–Z），同一录音、同一说话人，用于拼读提示与敲对字母时的反馈。

## 来源与许可

| 项目 | 说明 |
| --- | --- |
| **来源** | [Peter's Useful Crap — mp3 audio files alphabet](https://www.theblog.ca/mp3-audio-files-alphabet) |
| **文件** | `only_letters-transfer_RO-07feb-2eaa0f.zip`（仅字母名，无 “A for apple” 词组） |
| **许可** | 作者 Peter（theblog.ca）在博客评论中明确允许**以任何方式使用**（可署名也可不署名），适合本开源游戏再分发；非 CC0 文本，但为明确的免版税授权 |
| **格式** | 仓库内为 **MP3**（24 kHz mono；`fetch_audio.py` 经 ffmpeg 统一转码） |

> 说明：曾使用 Wikimedia `En-us-*.ogg` 逐字母文件，因**非同一录音**听感不一致已弃用。Freesound CC0 整段字母表（如 ChotoTheBright #700028）需账号下载，本仓库改用上述已分轨的同会话包。

## 生成 / 更新素材

```bash
python3 games/word_battle/fetch_audio.py
python3 games/word_battle/generate.py   # 同步到 web/games/word-battle/audio/
```

文件命名：`a.mp3` … `z.mp3`（小写，与 `FgbAudioClips` 的 `clipIds` 一致）。

## 整词读音

游戏**不**播报整词，仅字母 MP3 + 拼写输入。
