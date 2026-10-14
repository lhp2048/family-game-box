#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse the Chinese quiz markdown bank into questions.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
BANK_PATH = HERE / "bank.md"
OUT_PATH = HERE.parents[1] / "web" / "games" / "yuwen" / "questions.json"

STAGES: List[Dict[str, str]] = [
    {"id": "zuyin", "title": "字音"},
    {"id": "zixing", "title": "字形"},
    {"id": "chengyu", "title": "成语"},
    {"id": "ciyu", "title": "词语与虚词"},
    {"id": "bingju", "title": "病句"},
    {"id": "biaodian", "title": "标点符号"},
    {"id": "mingju", "title": "名句默写"},
    {"id": "changshi", "title": "文学常识"},
    {"id": "wenyan-base", "title": "文言文基础"},
    {"id": "gushi", "title": "古诗词鉴赏"},
    {"id": "yuyan", "title": "语言表达"},
    {"id": "xiandai", "title": "现代文阅读"},
    {"id": "zonghe", "title": "综合性学习"},
    {"id": "xiuci", "title": "修辞手法"},
    {"id": "wenyan-read", "title": "文言文阅读"},
    {"id": "xiandai-extra", "title": "现代文补充"},
    {"id": "gushi-extra", "title": "古诗词补充"},
    {"id": "yingyong", "title": "应用文"},
    {"id": "mingzhu", "title": "名著阅读"},
]

_PART_RE = re.compile(r"^# 第.+部分", re.M)
_Q_RE = re.compile(r"^\*\*(\d+)\.\*\*\s*(.*)$")
_PROMPT_RE = re.compile(r"^\*\*题型\*\*[：:]\s*(.*)$")
_RANGE_RE = re.compile(r"(\d+)\s*[—–\-]+\s*(\d+)\s*题")
_OPT_RE = re.compile(r"(?:^|[\s。！？；:：）)])([A-D])[\.．、]")
_ANSWER_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*([A-Da-d])\s*\|(.*)\|\s*$")
_PASSAGE_HINT_RE = re.compile(r"语段[：:]|阅读下面的语段")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_PY_RE = re.compile(r"（([A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńňǹɡ\s]+)）")
_TONE = str.maketrans(
    {
        "ā": "a", "á": "a", "ǎ": "a", "à": "a",
        "ē": "e", "é": "e", "ě": "e", "è": "e",
        "ī": "i", "í": "i", "ǐ": "i", "ì": "i",
        "ō": "o", "ó": "o", "ǒ": "o", "ò": "o",
        "ū": "u", "ú": "u", "ǔ": "u", "ù": "u",
        "ǖ": "v", "ǘ": "v", "ǚ": "v", "ǜ": "v", "ü": "v",
        "ń": "n", "ň": "n", "ǹ": "n",
    }
)
_INITIALS = ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w")
_NEAR_INITIAL = {
    "z": "zh", "zh": "z", "c": "ch", "ch": "c", "s": "sh", "sh": "s",
    "n": "l", "l": "n", "d": "t", "t": "d", "b": "p", "p": "b", "g": "k", "k": "g",
}
_reading_cache: Dict[str, List[str]] = {}


def _is_han(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _base(syllable: str) -> str:
    return syllable.strip().lower().replace("u:", "v").translate(_TONE)


def _split_syllable(syllable: str) -> Tuple[str, str]:
    for initial in _INITIALS:
        if syllable.startswith(initial):
            return initial, syllable[len(initial):]
    return "", syllable


def _readings(ch: str) -> List[str]:
    cached = _reading_cache.get(ch)
    if cached is not None:
        return cached
    from pypinyin import Style, pinyin

    rows = pinyin(ch, style=Style.NORMAL, heteronym=True, errors=lambda item: [])
    found = []
    if rows and rows[0]:
        for item in rows[0]:
            base = _base(str(item))
            if base and base not in found:
                found.append(base)
    _reading_cache[ch] = found
    return found


def _matches(ch: str, syllable: str) -> bool:
    return syllable in _readings(ch)


def _near(ch: str, syllable: str) -> bool:
    want_initial, want_final = _split_syllable(syllable)
    for reading in _readings(ch):
        initial, final = _split_syllable(reading)
        if final != want_final or not final:
            continue
        if initial == want_initial or _NEAR_INITIAL.get(initial) == want_initial:
            return True
    return False


def _hot_offsets(word: str, syllables: List[str], ordered: bool = True) -> List[int]:
    bases = [item for item in (_base(s) for s in syllables) if item]
    if not word or not bases:
        return []
    if ordered and len(bases) == len(word):
        return list(range(len(word)))
    exact = [idx for idx, ch in enumerate(word) if any(_matches(ch, item) for item in bases)]
    if exact:
        return exact
    near = [idx for idx, ch in enumerate(word) if any(_near(ch, item) for item in bases)]
    return near


def _mark_hot(text: str) -> str:
    """把加点字包成高亮标记。题库用 ** **，或把注音紧挨在字、词后面。"""
    chars = list(text)
    hot = [False] * len(chars)
    skip = [False] * len(chars)
    for match in _BOLD_RE.finditer(text):
        for idx in range(match.start(1), match.end(1)):
            hot[idx] = True
        for idx in (match.start(), match.start() + 1, match.end() - 2, match.end() - 1):
            if 0 <= idx < len(chars):
                skip[idx] = True
    for match in _PY_RE.finditer(text):
        end = match.start()
        start = end
        while start > 0 and _is_han(text[start - 1]):
            start -= 1
        word = text[start:end]
        for offset in _hot_offsets(word, match.group(1).split()):
            hot[start + offset] = True
    out: List[str] = []
    idx = 0
    while idx < len(chars):
        if skip[idx]:
            idx += 1
            continue
        if hot[idx]:
            end = idx
            while end < len(chars) and hot[end] and not skip[end]:
                end += 1
            chunk = "".join(chars[pos] for pos in range(idx, end) if not skip[pos])
            if chunk:
                out.append('<em class="yuwen-mark">%s</em>' % chunk)
            idx = end
            continue
        out.append(chars[idx])
        idx += 1
    return "".join(out)


def _strip_mark(text: str) -> str:
    return text.replace('<em class="yuwen-mark">', "").replace("</em>", "")


def _em(text: str) -> str:
    return '<em class="yuwen-mark">%s</em>' % text


def _render_hot_word(word: str, offsets: List[int]) -> str:
    chosen = set(offsets)
    out: List[str] = []
    idx = 0
    while idx < len(word):
        if idx in chosen:
            end = idx
            while end < len(word) and end in chosen:
                end += 1
            out.append(_em(word[idx:end]))
            idx = end
            continue
        out.append(word[idx])
        idx += 1
    return "".join(out)


def _replace_once_plain(text: str, word: str, replacement: str) -> str:
    parts = re.split(r"(<em class=\"yuwen-mark\">.*?</em>)", text)
    for idx, part in enumerate(parts):
        if part.startswith("<em ") or word not in part:
            continue
        parts[idx] = part.replace(word, replacement, 1)
        break
    return "".join(parts)


def _wrap_term(text: str, term: str) -> str:
    if not term or len(term) > 12 or term not in _strip_mark(text):
        return text
    parts = re.split(r"(<em class=\"yuwen-mark\">.*?</em>)", text)
    for idx, part in enumerate(parts):
        if part.startswith("<em "):
            continue
        parts[idx] = part.replace(term, _em(term))
    return "".join(parts)


def _mark_gloss(text: str) -> str:
    matches = list(re.finditer(r"（([\u4e00-\u9fff]{1,8})[：:]", text))
    for match in reversed(matches):
        head = match.group(1)
        before = text[: match.start()]
        pos = before.rfind(head)
        if pos < 0:
            continue
        text = text[:pos] + _em(head) + text[pos + len(head):]
    return text


def _listed_words(stem: str) -> List[str]:
    plain = _strip_mark(stem)
    found = re.search(r"（([^）]*[\u4e00-\u9fff][^）]*)）", plain)
    if not found or not re.search(r"[\s　]", found.group(1)):
        return []
    words = []
    for piece in re.split(r"[\s　]+", found.group(1).strip()):
        if piece and all(_is_han(ch) or ch == "儿" for ch in piece):
            words.append(piece)
    return words if len(words) >= 2 else []


def _syllable_columns(options: Dict[str, str], count: int) -> List[List[str]]:
    columns: List[List[str]] = [[] for _ in range(count)]
    token = re.compile(r"[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńňǹɡ]+")
    for text in options.values():
        parts = re.split(r"[；;]", _strip_mark(text))
        if len(parts) < count:
            continue
        for idx in range(count):
            columns[idx].extend(token.findall(parts[idx]))
    return columns


def _options_are_pinyin(options: Dict[str, str]) -> bool:
    plain = [_strip_mark(text) for text in options.values()]
    return all(re.fullmatch(r"[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüńňǹɡ\s；;、，,]+", text or "") for text in plain)


def _leading_term(stem: str) -> str:
    plain = _strip_mark(stem).lstrip()
    match = re.match(r"^（([\u4e00-\u9fff]{1,8})）", plain)
    return match.group(1) if match else ""


def _quoted_term(text: str) -> str:
    plain = _strip_mark(text)
    match = re.search(r"加点词['‘“\"「]([^'’“”\"」]{1,12})['’“”\"」]", plain)
    return match.group(1) if match else ""


def _mark_jiadian(item: Dict[str, Any]) -> None:
    """题干写了「加点」，但没标粗体、也没把注音紧挨着字时，仍高亮那个字或词。"""
    blob = (item.get("prompt") or "") + (item.get("stem") or "")
    if "加点" not in _strip_mark(blob):
        return
    item["options"] = {key: _mark_gloss(value) for key, value in item["options"].items()}
    words = _listed_words(item.get("stem") or "")
    if words and _options_are_pinyin(item["options"]):
        columns = _syllable_columns(item["options"], len(words))
        stem = item.get("stem") or ""
        for idx, word in enumerate(words):
            syllables = columns[idx] if idx < len(columns) else []
            offsets = _hot_offsets(word, syllables, ordered=False) if syllables else []
            if not offsets:
                offsets = list(range(len(word)))
            stem = _replace_once_plain(stem, word, _render_hot_word(word, offsets))
        item["stem"] = stem
        return
    term = _leading_term(item.get("stem") or "")
    plain_stem = _strip_mark(item.get("stem") or "")
    after_label = re.sub(r"^（[\u4e00-\u9fff]{1,8}）", "", plain_stem.lstrip())
    term_in_question = bool(term) and (
        term in after_label
        or any(term in _strip_mark(value) for value in item["options"].values())
    )
    if term and term_in_question:
        item["stem"] = _wrap_term(item.get("stem") or "", term)
        item["options"] = {key: _wrap_term(value, term) for key, value in item["options"].items()}
        if item.get("passage"):
            item["passage"] = _wrap_term(item["passage"], term)
        return
    quoted = _quoted_term(blob)
    if quoted:
        item["stem"] = _wrap_term(item.get("stem") or "", quoted)


def _clean_inline(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = _mark_hot(text)
    return text.strip()


def split_options(body: str) -> Tuple[str, Dict[str, str]]:
    marks = list(_OPT_RE.finditer(body))
    # Keep the first A, then the following B/C/D in order. Extra letters inside
    # an option (rare) stay in that option's text.
    picked: List[re.Match[str]] = []
    expect = "A"
    for mark in marks:
        letter = mark.group(1)
        if letter == expect:
            picked.append(mark)
            expect = chr(ord(expect) + 1)
            if expect > "D":
                break
    if len(picked) != 4 or [m.group(1) for m in picked] != ["A", "B", "C", "D"]:
        raise ValueError("options not A-D")
    stem = _clean_inline(body[: picked[0].start(1)])
    options: Dict[str, str] = {}
    for idx, mark in enumerate(picked):
        start = mark.end()
        end = picked[idx + 1].start(1) if idx + 1 < len(picked) else len(body)
        options[mark.group(1)] = _clean_inline(body[start:end])
        if not options[mark.group(1)]:
            raise ValueError("empty option %s" % mark.group(1))
    return stem, options


def _parse_answers(text: str) -> Dict[int, Dict[str, str]]:
    found: Dict[int, Dict[str, str]] = {}
    for line in text.splitlines():
        match = _ANSWER_RE.match(line.strip())
        if not match:
            continue
        num = int(match.group(1))
        found[num] = {
            "answer": match.group(2).upper(),
            "explain": _clean_inline(match.group(3)),
        }
    return found


def _split_parts(text: str) -> List[str]:
    cut = text.find("\n# 附录")
    if cut >= 0:
        text = text[:cut]
    parts: List[str] = []
    indexes = [m.start() for m in _PART_RE.finditer(text)]
    for idx, start in enumerate(indexes):
        end = indexes[idx + 1] if idx + 1 < len(indexes) else len(text)
        parts.append(text[start:end])
    return parts


def _parse_questions(section: str, stage_id: str) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []
    passage_buf: List[str] = []
    active_passage = ""
    active_group = ""
    active_title = ""
    active_range: Optional[Tuple[int, int]] = None
    rest_of_heading = False
    prompt = ""
    heading = ""
    q_num: Optional[int] = None
    q_lines: List[str] = []

    def in_shared(num: int) -> bool:
        if not active_passage:
            return False
        if rest_of_heading:
            return True
        if active_range is None:
            return False
        return active_range[0] <= num <= active_range[1]

    def flush() -> None:
        nonlocal q_num, q_lines
        if q_num is None:
            return
        body = "\n".join(q_lines).strip()
        try:
            stem, options = split_options(body)
        except ValueError as exc:
            raise ValueError("q %s: %s\n%s" % (q_num, exc, body[:400])) from exc
        item: Dict[str, Any] = {
            "id": q_num,
            "stage": stage_id,
            "prompt": prompt,
            "stem": stem,
            "options": options,
            "passage": "",
            "group": "",
            "groupTitle": "",
        }
        if in_shared(q_num):
            item["passage"] = active_passage
            item["group"] = active_group
            item["groupTitle"] = active_title
        elif _PASSAGE_HINT_RE.search(stem):
            item["group"] = "%s-item-%d" % (stage_id, q_num)
            item["groupTitle"] = "语段第 %d 题" % q_num
        _mark_jiadian(item)
        questions.append(item)
        q_num = None
        q_lines = []

    for raw in section.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            flush()
            heading = line[3:].strip()
            passage_buf = []
            active_passage = ""
            active_group = ""
            active_title = heading
            rest_of_heading = False
            active_range = None
            range_match = _RANGE_RE.search(heading)
            if range_match:
                active_range = (int(range_match.group(1)), int(range_match.group(2)))
            elif heading.startswith("文段"):
                rest_of_heading = True
            continue

        prompt_match = _PROMPT_RE.match(line.strip())
        if prompt_match and q_num is None:
            prompt = _clean_inline(prompt_match.group(1))
            range_match = _RANGE_RE.search(prompt)
            if range_match:
                active_range = (int(range_match.group(1)), int(range_match.group(2)))
                rest_of_heading = False
            elif "完成各题" in prompt or "完成下列" in prompt:
                rest_of_heading = True
            continue

        q_match = _Q_RE.match(line.strip())
        if q_match:
            flush()
            if passage_buf and not active_passage:
                active_passage = _clean_inline("\n".join(passage_buf))
                passage_buf = []
                active_group = "%s-%s" % (stage_id, heading or "group")
            q_num = int(q_match.group(1))
            rest = q_match.group(2).strip()
            q_lines = [rest] if rest else []
            continue

        if q_num is None:
            stripped = line.strip()
            if not stripped or stripped.startswith("---") or stripped.startswith("|"):
                continue
            if stripped.startswith(">"):
                passage_buf.append(stripped.lstrip(">").strip())
            else:
                passage_buf.append(stripped)
            continue

        q_lines.append(line)

    flush()
    return questions


def parse_bank(text: str) -> Dict[str, Any]:
    parts = _split_parts(text)
    if len(parts) != len(STAGES):
        raise ValueError("expected %d parts, got %d" % (len(STAGES), len(parts)))

    questions: List[Dict[str, Any]] = []
    for stage, part in zip(STAGES, parts):
        answer_at = part.find("\n## 第")
        if answer_at < 0:
            raise ValueError("missing answers in %s" % stage["id"])
        # The first "## 第" inside a part is the answer heading.
        answer_heading = part.find("\n## 第", 1)
        questions_text = part[:answer_heading]
        answers = _parse_answers(part[answer_heading:])
        parsed = _parse_questions(questions_text, stage["id"])
        for item in parsed:
            key = answers.get(item["id"])
            if not key:
                raise ValueError("missing answer for %s" % item["id"])
            item["answer"] = key["answer"]
            item["explain"] = key["explain"]
        known = {item["id"] for item in parsed}
        extra = sorted(set(answers) - known)
        if extra:
            raise ValueError("%s has answers without questions: %s" % (stage["id"], extra[:8]))
        questions.extend(parsed)

    questions.sort(key=lambda item: item["id"])
    ids = [item["id"] for item in questions]
    if ids != list(range(1, len(ids) + 1)):
        missing = [n for n in range(1, (ids[-1] if ids else 0) + 1) if n not in set(ids)]
        raise ValueError("question ids not contiguous, missing %s" % missing[:12])

    stages = []
    for stage in STAGES:
        owned = [q for q in questions if q["stage"] == stage["id"]]
        flash = sum(1 for q in owned if not q["group"])
        groups = []
        seen = set()
        for q in owned:
            if not q["group"] or q["group"] in seen:
                continue
            seen.add(q["group"])
            title = q["groupTitle"] or q["group"]
            title = re.sub(r"（[^）]*）", "", title).strip()
            title = re.sub(r"^[A-H]\s*组\s*", "", title).strip()
            if "-item-" in q["group"]:
                title = "语段 %d" % (len(groups) + 1)
            groups.append({
                "id": q["group"],
                "title": title or q["group"],
                "count": sum(1 for item in owned if item["group"] == q["group"]),
            })
        if flash and groups:
            rhythm = "mixed"
        elif groups:
            rhythm = "passage"
        else:
            rhythm = "flash"
        stages.append({
            "id": stage["id"],
            "title": stage["title"],
            "rhythm": rhythm,
            "flashCount": flash,
            "groups": groups,
        })

    return {"version": 1, "stages": stages, "questions": questions}


def main() -> None:
    data = parse_bank(BANK_PATH.read_text(encoding="utf-8"))
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print("questions %d -> %s" % (len(data["questions"]), OUT_PATH))
    for stage in data["stages"]:
        print(
            "%s %s flash=%d groups=%d"
            % (stage["rhythm"], stage["title"], stage["flashCount"], len(stage["groups"]))
        )


if __name__ == "__main__":
    main()
