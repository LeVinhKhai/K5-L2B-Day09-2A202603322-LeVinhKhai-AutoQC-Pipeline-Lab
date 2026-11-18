"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


DROP_LINE_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _fix_log(image, line, action, before, after):
    return {
        "image": image,
        "line": "" if line is None else line,
        "action": action,
        "before": before,
        "after": after,
    }


def _line_ending(text):
    if text.endswith("\r\n"):
        return "\r\n"
    if text.endswith("\n"):
        return "\n"
    if text.endswith("\r"):
        return "\r"
    return ""


def _clip_yolo_line(text):
    class_id, x, y, width, height = parse_yolo_line(text)
    left = max(0.0, x - width / 2)
    top = max(0.0, y - height / 2)
    right = min(1.0, x + width / 2)
    bottom = min(1.0, y + height / 2)

    if right <= left or bottom <= top:
        return None

    clipped = (
        (left + right) / 2,
        (top + bottom) / 2,
        right - left,
        bottom - top,
    )
    values = " ".join(format(value, ".12g") for value in clipped)
    return f"{class_id} {values}"


def fix(ds, issues, cfg):
    error_issues = [issue for issue in issues if issue.severity == ERROR]
    fixes = []

    remove_stems = {
        issue.image
        for issue in error_issues
        if issue.code.startswith("DUP_IMAGE_") or issue.code in REMOVE_IMAGE_CODES
    }
    removed = set()
    for issue in error_issues:
        stem = issue.image
        if stem not in remove_stems or stem in removed:
            continue

        image_path = ds.image_path(stem)
        label_path = ds.label_path(stem)
        existing = [path.name for path in (image_path, label_path) if path is not None and path.exists()]
        if not existing:
            removed.add(stem)
            continue

        if image_path is not None:
            image_path.unlink(missing_ok=True)
        label_path.unlink(missing_ok=True)
        removed.add(stem)
        fixes.append(_fix_log(stem, None, "remove_image", ", ".join(existing), "đã xoá ảnh và nhãn"))

    rename_requested = any(issue.code == "BAD_CLASS_NAME" for issue in error_issues)
    if rename_requested:
        try:
            data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        current_names = ds.yaml_names() if ds.yaml_path.exists() else {}
        wanted_names = list(cfg["classes"])
        current_ordered = [current_names[i] for i in sorted(current_names)]
        if current_ordered != wanted_names or len(current_names) != len(wanted_names):
            data["names"] = wanted_names
            ds.yaml_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            fixes.append(
                _fix_log(
                    "data.yaml",
                    None,
                    "rename_classes",
                    str(current_ordered),
                    str(wanted_names),
                )
            )

    needs_label_seen = set()
    for issue in error_issues:
        stem = issue.image
        if issue.code != "MISSING_LABEL_FILE" or stem in remove_stems or stem in needs_label_seen:
            continue
        if ds.image_path(stem) is not None and not ds.label_path(stem).exists():
            fixes.append(_fix_log(stem, None, "needs_label", "(không có file)", "chuyển người gán"))
            needs_label_seen.add(stem)

    drops = defaultdict(set)
    clips = defaultdict(set)
    stem_order = []
    planned_stems = set()
    for issue in error_issues:
        stem = issue.image
        if stem in remove_stems or issue.line is None:
            continue
        if issue.code not in DROP_LINE_CODES and issue.code != "BOX_OUT_OF_IMAGE":
            continue
        if stem not in planned_stems:
            stem_order.append(stem)
            planned_stems.add(stem)
        if issue.code in DROP_LINE_CODES:
            drops[stem].add(issue.line)
        else:
            clips[stem].add(issue.line)

    for stem in stem_order:
        label_path = ds.label_path(stem)
        if not label_path.exists():
            continue

        original_lines = label_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        output_lines = []
        stem_fixes = []

        for line_no, original in enumerate(original_lines, 1):
            before = original.rstrip("\r\n")
            if line_no in drops[stem]:
                stem_fixes.append(_fix_log(stem, line_no, "drop_line", before, ""))
                continue

            if line_no in clips[stem]:
                try:
                    after = _clip_yolo_line(before)
                except (ValueError, OverflowError):
                    output_lines.append(original)
                    continue
                if after is None:
                    stem_fixes.append(_fix_log(stem, line_no, "drop_line", before, ""))
                    continue
                if after != before:
                    output_lines.append(after + _line_ending(original))
                    stem_fixes.append(_fix_log(stem, line_no, "clip_box", before, after))
                    continue

            output_lines.append(original)

        if stem_fixes:
            label_path.write_text("".join(output_lines), encoding="utf-8")
            fixes.extend(stem_fixes)

    return fixes
