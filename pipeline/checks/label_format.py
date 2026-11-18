"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    thresholds = cfg["label_format"]
    overflow_tol = thresholds["overflow_tol"]
    min_box_px = thresholds["min_box_px"]
    max_box_frac = thresholds["max_box_frac"]
    dup_box_iou = thresholds["dup_box_iou"]

    issues = []
    for label_file in ds.label_files():
        stem = label_file.stem
        image_size = ds.image_size(stem)
        previous_by_class = {}

        for line_no, text in ds.read_label_lines(stem) or []:
            try:
                class_id, x, y, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError) as exc:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, str(exc), line=line_no))
                continue

            if not 0 <= class_id < len(ds.classes):
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BAD_CLASS_ID",
                        stem,
                        f"id lớp {class_id} ngoài khoảng 0..{len(ds.classes) - 1}",
                        line=line_no,
                    )
                )
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"box có kích thước không dương: w={w}, h={h}", line=line_no))
                continue

            box = (x, y, w, h)
            left, top = x - w / 2, y - h / 2
            right, bottom = x + w / 2, y + h / 2
            overflow = max(0.0, -left, -top, right - 1.0, bottom - 1.0)
            if overflow > overflow_tol:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn ảnh {overflow:.6g}",
                        line=line_no,
                        extra={"overflow": overflow},
                    )
                )

            previous = previous_by_class.setdefault(class_id, [])
            if any(iou_xywh(box, old_box) > dup_box_iou for old_box in previous):
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, "box lặp với một dòng trước cùng lớp", line=line_no))
            previous.append(box)

            if image_size is not None:
                image_w, image_h = image_size
                short_side_px = min(w * image_w, h * image_h)
                if short_side_px < min_box_px:
                    issues.append(
                        Issue(
                            "label_format",
                            WARN,
                            "BOX_TINY",
                            stem,
                            f"cạnh ngắn {short_side_px:.2f}px < {min_box_px}px",
                            line=line_no,
                        )
                    )

            area_frac = w * h
            if area_frac > max_box_frac:
                issues.append(
                    Issue(
                        "label_format",
                        WARN,
                        "BOX_HUGE",
                        stem,
                        f"diện tích box {area_frac:.6g} > {max_box_frac}",
                        line=line_no,
                    )
                )

    return issues
