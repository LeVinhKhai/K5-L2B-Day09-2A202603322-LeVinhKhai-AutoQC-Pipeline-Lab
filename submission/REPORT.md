# Báo cáo Day 09 — <Lê Vĩnh Khải>, <2A202603322>

> Các số liệu QC được đối chiếu từ submission/reports/, calibration và manifest. Kết quả training raw vs clean đã hoàn thành và được trình bày tại mục 5.

## 1. Kết luận trước
**Pipeline kết luận Release / Hold / Rework? Bao nhiêu ảnh vào, bao nhiêu ảnh ra dataset?** Pipeline kết luận **HOLD**: intake nhận **202/224 ảnh** và loại 22; `clean_v1` có **202 ảnh** nhưng chỉ là **bản nháp**, chưa được Release. Sau khi mô phỏng người duyệt 80/80 ảnh theo ngân sách, không còn ERROR nhưng vẫn còn **38/202 ảnh chưa duyệt có WARN (18,81%)**, vượt ngưỡng Hold 10%; lệnh pipeline có mã thoát 10.

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_SIZE` (ERROR) | 3 ảnh/224 | Máy, intake | Loại ảnh có cạnh ngắn dưới 250 px. |
| `CORRUPT_IMAGE` (ERROR) | 2 ảnh/224 | Máy, intake | Ảnh không giải mã đầy đủ nên không thể dùng an toàn. |
| `DUP_IMAGE_EXACT` (ERROR) | 8 ảnh/224 | Máy, intake | Trùng từng byte; giữ ảnh xuất hiện trước. |
| `DUP_IMAGE_NEAR` (ERROR) | 4 ảnh/224 | Máy + xác nhận thêm | pHash ≤ 12; bốn cặp trong run cuối đã được loại, nhưng ngưỡng phải được kiểm tra bằng mắt để tránh false positive. |
| `LEAK_TEST` (ERROR) | 5 ảnh/224 | Máy, intake | Loại ảnh trùng kho test/gold_val để tránh rò rỉ. |
| `BAD_CLASS_ID` (ERROR) | 6 dòng/202 ảnh | Máy | Xóa dòng có class ngoài 0–3. |
| `BAD_CLASS_NAME` (ERROR) | 2 issue/1 `data.yaml` | Máy | Sửa một lần `Person`, `Bus` về danh sách lớp chuẩn. |
| `BAD_FORMAT` (ERROR) | 3 dòng/202 ảnh | Máy | Xóa dòng thiếu cột hoặc có `nan/inf`. |
| `BOX_OUT_OF_IMAGE` (ERROR) | 8 dòng/202 ảnh | Máy | Clip box vào biên ảnh và ghi before/after. |
| `BOX_ZERO` (ERROR) | 4 dòng/202 ảnh | Máy | Box không có diện tích nên phải xóa. |
| `DUP_BOX` (ERROR) | 7 dòng/202 ảnh | Máy | Xóa box lặp cùng lớp. |
| `MISSING_LABEL_FILE` (ERROR) | 6 ảnh/202 | Người | Máy chỉ ghi `needs_label`, không được bịa file nhãn. |
| `BOX_HUGE` (WARN) | 3 dòng/202 ảnh | Người | Cần xác nhận box lớn là đúng vật hay box quá lỏng. |
| `BOX_TINY` (WARN) | 6 dòng/202 ảnh | Người | Vật nhỏ có thể hợp lệ; sau clip vòng 2 có 7 cảnh báo. |
| `CLASS_RARE` (WARN) | 4 issue cấp dataset | Điều tra | Các token lớp sai `-1`, `4`, `7`, `93` làm thống kê bất thường trước autofix. |
| `EMPTY_LABEL` (WARN) | 12 ảnh/202 | Người | Có thể là ảnh nền hoặc thiếu toàn bộ nhãn. |
| `POSSIBLE_FALSE_POS` (WARN) | 29 dòng/202 ảnh | Người | Model chỉ đưa ý kiến thứ hai, không đủ tin cậy để máy xóa box. |
| `POSSIBLE_LOOSE_BOX` (WARN) | 28 issue/202 ảnh | Người | Cần nhìn ảnh để chỉnh box lỏng/lệch. |
| `POSSIBLE_MISSING` (WARN) | 53 issue/202 ảnh | Người | Cần annotator xác nhận và thêm vật bị bỏ sót nếu đúng. |
| `POSSIBLE_WRONG_CLASS` (WARN) | 18 issue/202 ảnh | Người | Nhầm lớp hợp lệ là lỗi ngữ nghĩa, model không được tự sửa. |

`02_error_list_v1.csv` có 211 dòng vì giữ cả 22 ERROR intake để truy vết; phần QC vòng 1 trên 202 ảnh riêng biệt có **36 ERROR và 153 WARN**. `03_fixes.csv` ghi **35 hành động**: 20 `drop_line`, 8 `clip_box`, 1 `rename_classes` và 6 `needs_label`; tức 29 sửa đổi an toàn và 6 lần chuyển việc cho người. QC vòng 2 còn **6 ERROR**, 148 WARN và hàng đợi **125 ảnh**.

**Vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?** Hàng đợi cộng trọng số theo rủi ro: `NEEDS_LABEL` = 10, `POSSIBLE_WRONG_CLASS` = 3, `POSSIBLE_MISSING`/`POSSIBLE_FALSE_POS` = 2, `POSSIBLE_LOOSE_BOX` = 1,5, rồi cộng dấu vết autofix. Vì vậy `img_0020` đứng đầu (11,524; vừa drop dòng, vừa nghi thiếu và sai lớp), tiếp theo là 6 ảnh thiếu file nhãn (10 điểm). `06_review_log.csv` xác nhận người mô phỏng xem **80 ảnh**; **74/80 ảnh** có ít nhất một mã lỗi ngữ nghĩa, bao phủ **94 dòng cảnh báo ngữ nghĩa** trong v2: 51 missing, 18 wrong-class, 13 false-positive và 12 loose-box (một ảnh có thể có nhiều mã).

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 12 | 1.00/0.50 → 1.00/0.67 | Ưu tiên precision để hạn chế xóa nhầm ảnh. Ngưỡng 16 cho recall cao hơn (0.83) trên tập calib nhưng đã gây false positive khi kiểm tra ảnh raw. Chọn 12 để giữ các trường hợp near-duplicate rõ ràng và tránh những cặp khác nội dung có pHash distance = 16. |
| `second_opinion.conf` | 0.25 | 0.60 | MISSING: 0.50/1.00 → 0.57/1.00; WRONG_CLASS: 0.56/0.83 → 0.62/0.83; LOOSE: 0.29/0.40 → 0.20/0.20; FALSE_POS giữ 0.36/1.00 | Tăng precision của missing và wrong-class mà giữ recall tương ứng; đánh đổi là loose-box mất recall. Không chọn 0.8 dù precision cao hơn vì recall missing giảm còn 0.75. |

**Một chỗ calibration có thể đánh lừa?** Tập calibration chỉ có 39 ảnh, trong đó 6 trường hợp near-duplicate được chèn. Ở `phash_dist=16`, precision đạt 1.00, recall 0.83 và F1 0.91 trên calib, nhưng precision 1.00 này không bảo đảm an toàn trên raw.

Với ngưỡng 16, pipeline loại 31/224 ảnh, gồm 7 `DUP_IMAGE_NEAR`. Contact sheet quan sát thủ công cho thấy hai false positive rõ ràng:

- `img_0011` (tennis) bị ghép với `img_0008` (trượt tuyết), pHash distance 16.
- `img_0177` (lướt sóng) bị ghép với `img_0113` (người ngồi bàn), pHash distance 16.
Sau khi giảm xuống 12 và giữ `second_opinion.conf=0.60`, pipeline loại **22/224** thay vì 31/224 và giữ 202 ảnh thay vì 193. Ngưỡng 12 thận trọng hơn với false positive, nhưng recall near-duplicate trên calib chỉ 0.67 nên vẫn có thể bỏ sót biến đổi mạnh.
**Bằng chứng trực quan:** [Xem contact sheet 7 cặp near-duplicate](evidence/near_duplicate_review.png).
## 4. Cửa chặn và điều pipeline KHÔNG bắt được
**Gate có chặn đúng không?** Có. Run chuẩn sau review không còn ERROR nhưng còn 38/202 ảnh WARN chưa review (18,81% ≥ 10%), nên **HOLD**, exit code 10. Thử nghiệm `--budget 0 --reports work/rep_nb --export-dir work/exp_nb` giữ nguyên 6 `MISSING_LABEL_FILE`, nên **REWORK**, exit code 20; `work/rep_nb/08_summary.json` ghi `exported: null`, chứng minh dataset không được xuất khi còn lỗi bắt buộc. Trong run chuẩn, manifest có 202 ảnh và quyết định Hold: đây là bản nháp, không phải bản Release.
**Bằng chứng REWORK:** [Xem kết quả kiểm thử budget = 0](evidence/rework_summary.json).
**Điểm mù có bằng chứng:** (1) pHash đo cấu trúc ảnh chứ không hiểu nội dung: hai cặp khác nội dung ở distance 16 nêu trên từng bị coi là trùng; giảm ngưỡng tránh hai false positive nhưng recall calib 0.67 cho thấy ảnh trùng biến đổi mạnh có thể lọt. (2) Model checker không phải ground truth: tại conf 0.60, recall `POSSIBLE_LOOSE_BOX` chỉ 0.20 và wrong-class 0.83; `img_0007` được quan sát thủ công là nghi thiếu car nhưng không xuất hiện trong bất kỳ error list nào, nên vẫn **cần người xác minh**. (3) Check `CLASS_RARE` chỉ dùng ngưỡng tuyệt đối; `class_stats.csv` cuối có 574 person nhưng chỉ 32 bus và 41 truck, song không cảnh báo mất cân bằng tương đối này.

**Ghi chú quan sát thủ công ban đầu (CP1, chưa phải kết quả pipeline):** Khi xem ảnh do `scripts/viz_labels.py` tạo và đối chiếu file nhãn hiện có, tôi ghi nhận ba **nghi ngờ** để kiểm tra lại bằng pipeline/người duyệt: `img_0001` có thể thiếu box cho 1 `person` ở giữa ảnh; `img_0007` có thể còn thiếu box `car` dù file nhãn đã có 6 box `car`; `img_0004` có file nhãn rỗng trong khi có xe con bị che/cắt ở mép phải, nên có thể thiếu box `car`. Đây chỉ là quan sát bằng mắt ở Bước 1, chưa đủ bằng chứng để xác nhận lỗi và không được dùng thay cho số liệu từ `submission/reports/`.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

**Thiết lập thí nghiệm:** Tôi sử dụng YOLO26n (`yolo26n.pt`) trên Google Colab với GPU T4, train 20 epoch cho mỗi lần chạy, gồm 2 seed (0 và 1) trên mỗi biến thể. Hai biến thể sử dụng cùng model khởi tạo, siêu tham số, tập validation (`gold_val`, 40 ảnh) và tập test (100 ảnh), chỉ khác dữ liệu training: **raw 224 ảnh** và **clean 202 ảnh**. Bộ clean hiện vẫn ở trạng thái **HOLD**, được sử dụng để thử nghiệm, chưa phải dataset Release.

| Biến thể | Số ảnh train | Số seed | mAP50 (TB ± SD) | mAP50-95 (TB ± SD) | Precision (TB ± SD) | Recall (TB ± SD) |
|---|---:|---:|---:|---:|---:|---:|
| Raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| Clean | 202 | 2 | 0.701 ± 0.025 | 0.487 ± 0.008 | 0.759 ± 0.003 | 0.625 ± 0.019 |

**Phân tích kết quả:** Chênh lệch mAP50 (clean − raw) là **−0.025**, tức clean thấp hơn raw 2,5 điểm phần trăm trong thí nghiệm này. Raw cũng có trung bình mAP50-95, precision và recall cao hơn. Tuy nhiên, độ chênh mAP50 tương đương độ lệch chuẩn giữa hai seed của clean (0.025), trong khi raw có SD được làm tròn thành 0.000. Với chỉ 2 seed và 100 ảnh test, chưa đủ bằng chứng khẳng định chênh lệch này ổn định hoặc raw chắc chắn tốt hơn trong các lần chạy khác.

**Giả thuyết giải thích và cách kiểm chứng:**

1. **Số lượng dữ liệu train giảm:** Clean chỉ có 202 ảnh so với 224 ảnh raw, có thể làm giảm sự đa dạng dữ liệu học. Cách kiểm: thử train trên một tập raw được chọn với cùng số lượng ảnh, giữ nguyên tham số và seed, rồi so sánh.
2. **Clean chưa được duyệt hoàn toàn:** Pipeline đang HOLD vì còn 38/202 ảnh có cảnh báo chưa được review. Các vấn đề như thiếu nhãn, nhầm lớp hoặc box lỏng vẫn có thể ảnh hưởng đến mô hình. Cách kiểm: hoàn tất human review, tạo bộ dữ liệu đạt Release và train lại với cùng điều kiện.
3. **Nguy cơ rò rỉ dữ liệu trong raw:** Intake đã phát hiện 5 trường hợp `LEAK_TEST` trong lần chạy cuối. Việc raw chứa ảnh trùng kho đánh giá có thể làm sai lệch kết quả đo. Cách kiểm: kiểm tra sự trùng lặp và đánh giá trên một tập test độc lập; không sử dụng test để sửa nhãn, điều chỉnh ngưỡng hay lựa chọn mô hình.

**Kết luận:** Thí nghiệm hiện tại chưa chứng minh clean cải thiện hiệu năng so với raw. Dù raw có điểm trung bình cao hơn, khác biệt vẫn cần được kiểm chứng với thêm seed và dữ liệu đánh giá độc lập. Việc AutoQC giúp phát hiện và giảm lỗi dữ liệu không đồng nghĩa với việc chắc chắn làm tăng mAP ở mọi thí nghiệm.

**Bằng chứng:** [Bảng tổng hợp raw vs clean](results/comparison.md) · [Biểu đồ so sánh](results/comparison.png) · [Kết quả chi tiết theo seed](results/comparison.json).

## 6. Quyết định và ghi chú AI
**Quyết định cuối:** **chưa Release; giữ HOLD**. Cần xử lý/duyệt tiếp các ảnh cảnh báo chưa được duyệt, ưu tiên 38 ảnh đang tính vào gate. Để xuống dưới 10%, số ảnh WARN chưa duyệt phải còn tối đa 20/202, tức cần giải quyết ít nhất 18/38 ảnh hiện tại (thận trọng hơn là duyệt hết), sau đó chạy lại pipeline, xác nhận 0 ERROR và gate Release. `clean_v1` hiện chỉ dùng như bản nháp/thí nghiệm; Kết quả training Colab đã được bổ sung tại mục 5 và không thay thế điều kiện QC để Release dataset.
**Ghi chú AI:** Tôi dùng Codex để hỗ trợ xây dựng, kiểm tra bốn module theo docstring/config/test, phân tích log và diễn đạt báo cáo và hướng dẫn làm bài. Tôi kiểm lại bằng test riêng từng module, toàn bộ **79 test**, đối chiếu CSV/JSON sinh tự động và xem ảnh raw; mọi con số trong báo cáo phải truy được về artifact. **TODO cá nhân trước khi nộp:** bổ sung một trường hợp AI trả lời/code sai cụ thể và cách tôi phát hiện, vì hiện chưa ghi lại tình huống này nên không được phép bịa.
**Một lần AI đưa ra khuyến nghị chưa phù hợp:** Ban đầu, ChatGPT đề xuất chọn `duplicates.phash_dist = 16` vì F1 trên tập calibration đạt 0.91, cao hơn các ngưỡng khác. Tuy nhiên, khuyến nghị này chưa đánh giá đầy đủ nguy cơ false positive trên dữ liệu raw. Tôi yêu cầu Codex tạo contact sheet đối chiếu 7 cặp ảnh bị đánh dấu gần trùng và trực tiếp kiểm tra, phát hiện hai cặp khác nội dung tại pHash distance = 16 (`img_0011`–`img_0008` và `img_0177`–`img_0113`). Tôi điều chỉnh ngưỡng xuống 12, chạy lại pipeline và xác nhận số ảnh bị loại giảm từ 31 xuống 22. Bài học là không chấp nhận đề xuất AI chỉ dựa trên một chỉ số calibration mà phải kiểm chứng bằng dữ liệu thực tế.
*(Thưởng +2, tùy chọn)* CVAT: chưa thực hiện; không khai báo điểm thưởng.
