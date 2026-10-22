"""AI: gợi ý ghế đẹp. GIAI ĐOẠN KHUNG: chấm điểm theo vị trí (chưa dùng mô hình học máy).

Ý tưởng: ghế đẹp là ghế gần trục giữa phòng và ở khoảng giữa phòng (50% độ sâu) từ màn hình.
Với 2 người, tìm 2 ghế LIỀN KỀ cùng hàng.
"""


class SeatRecommendationService:
    def recommend(self, seats: list[dict], count: int = 2) -> dict:
        """seats: [{id, row, number, label, booked}] của cả phòng. Trả về nhóm ghế tốt nhất."""
        count = max(1, min(int(count), 4))
        rows: dict[str, list[dict]] = {}
        for s in seats:
            rows.setdefault(s["row"], []).append(s)
        row_names = sorted(rows)
        max_col = max(s["number"] for s in seats)
        center = (max_col + 1) / 2
        ideal_row = 0.5 * (len(row_names) - 1)

        best, best_score = None, float("-inf")
        for r_idx, name in enumerate(row_names):
            line = sorted(rows[name], key=lambda s: s["number"])
            for i in range(len(line) - count + 1):
                block = line[i:i + count]
                contiguous = all(block[k + 1]["number"] - block[k]["number"] == 1 for k in range(count - 1))
                if not contiguous or any(s["booked"] for s in block):
                    continue
                mid = sum(s["number"] for s in block) / count
                score = -abs(mid - center) - 1.5 * abs(r_idx - ideal_row)
                if score > best_score:
                    best, best_score = block, score

        if not best:
            return {"source": "mock-rule-based", "seat_ids": [], "labels": [],
                    "message": f"Không còn {count} ghế liền kề phù hợp. Bạn hãy chọn thủ công nhé."}
        labels = [s["label"] for s in best]
        return {"source": "mock-rule-based", "seat_ids": [s["id"] for s in best], "labels": labels,
                "message": f"Gợi ý ghế {', '.join(labels)}: vị trí trung tâm, tầm nhìn đẹp."}
