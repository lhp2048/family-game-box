# 单词大作战 · 字母读音素材

26 个英语**字母名**（A–Z），同一女声（Claire）英式读音，分轨后偏干脆。

## 来源与许可

| 项目 | 说明 |
| --- | --- |
| **作者** | [groovy_turnokk](https://freesound.org/people/groovy_turnokk/) |
| **录音** | Freesound [**ClairesAlphabet.mp3**](https://freesound.org/people/groovy_turnokk/sounds/147504/)（sound ID **147504**） |
| **许可** | [**CC BY 4.0**](https://creativecommons.org/licenses/by/4.0/) — 可再分发与修改，**须署名**（见 `ATTRIBUTION.md`） |
| **本仓库处理** | 下载 Freesound **HQ preview** MP3 → `silencedetect` 分轨（约 52 段取偶数段为 26 字母）→ 略提音量 |

非北约音标字母（alpha/bravo），仅为 A–Z 字母名。

## 生成 / 更新

```bash
python3 games/word_battle/fetch_audio.py
python3 games/word_battle/generate.py
```

文件命名：`a.mp3` … `z.mp3`（与 `FgbAudioClips` 的 `clipIds` 一致）。

## 整词读音

游戏**不**播报整词，仅字母 MP3 + 拼写输入。
