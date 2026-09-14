import colorsys
import json
import os
import re
import urllib.parse
from playwright.sync_api import sync_playwright

# ============================================================
# 1. CẤU HÌNH ĐƯỜNG DẪN THƯ MỤC & FILE ĐẦU VÀO
# ============================================================
INPUT_FILE = "./kanji_list.txt"
JSON_COLOR_PATH = "./kanji_colors.json"

# Đường dẫn thư mục theo đúng cấu trúc Vault của bạn
MD_OUTPUT_DIR = "./📁 01_漢字/📁 常用漢字"
SVG_OUTPUT_DIR = "./📁 01_漢字/📁 筆順・画像"

os.makedirs(MD_OUTPUT_DIR, exist_ok=True)
os.makedirs(SVG_OUTPUT_DIR, exist_ok=True)

# Bật tính năng bỏ qua chữ đã cào xong (giúp chạy tiếp nếu bị ngắt quãng)
SKIP_EXISTING = True

# Số thứ tự bắt đầu (N5 bắt đầu từ 1, sau này N4 có thể đổi thành 80)
START_ORDER = 1


# ============================================================
# 2. CÁC HÀM TIỆN ÍCH DỮ LIỆU
# ============================================================
def load_kanji_list():
    """Đọc file kanji_list.txt và tách thành các đoạn độc lập (ngăn cách bởi dòng trống)."""
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Không tìm thấy file {INPUT_FILE}!")
        return []
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Tách các đoạn bằng 1 hoặc nhiều dòng trống Enter
    raw_blocks = re.split(r"\n\s*\n+", content.strip())
    
    kanji_groups = []
    for block in raw_blocks:
        # Lọc lấy danh sách chữ Hán của từng đoạn
        chars = re.findall(r"[\u4e00-\u9faf]", block)
        if chars:
            kanji_groups.append(chars)

    return kanji_groups


def load_kanji_colors():
    """Đọc bảng màu từ file kanji_colors.json."""
    if os.path.exists(JSON_COLOR_PATH):
        try:
            with open(JSON_COLOR_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Không đọc được file {JSON_COLOR_PATH}: {e}")
    return {}


def get_fallback_color(idx, total):
    """Màu Spectrum dự phòng chuẩn KanjiVG nếu JSON thiếu chữ đó."""
    h = idx / max(1, total)
    r, g, b = colorsys.hsv_to_rgb(h, 0.95, 0.75)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


# ============================================================
# 3. DỰNG FILE SVG CHUẨN ĐẶC TẢ ĐỘC QUYỀN
# ============================================================
def build_svg(kanji_char, strokes):
    timeline = []
    paths = []
    badges = []

    for s in strokes:
        idx = s["idx"]
        len_val = f"{s['length']:.4f}"

        timeline.append(
            f"#{kanji_char}-bg{idx}  {{ animation-delay: {s['bg_delay']:.2f}s; }}"
        )
        timeline.append(
            f"#{kanji_char}-s{idx}   {{ stroke-dasharray: {len_val}; stroke-dashoffset: {len_val}; animation: drawStroke {s['duration']:.2f}s ease-out {s['stroke_delay']:.2f}s forwards; }}"
        )

        paths.append(
            f'<path id="{kanji_char}-s{idx}"  class="stroke" stroke="{s["color"]}" d="{s["d"]}"/>'
        )

        if idx < 10:
            badges.append(
                f'<g id="{kanji_char}-bg{idx}"  class="badge-group"><circle cx="{s["x"]}" cy="{s["y"]}" r="3.5" fill="{s["color"]}"/><text class="num-single" x="{s["x"]}" y="{s["y"]}" dx="0" dy="-0.5">{idx}</text></g>'
            )
        else:
            badges.append(
                f'<g id="{kanji_char}-bg{idx}" class="badge-group"><circle cx="{s["x"]}" cy="{s["y"]}" r="3.5" fill="{s["color"]}"/><text class="num-double" x="{s["x"]}" y="{s["y"]}" dx="-0.4" dy="-0.475">{idx}</text></g>'
            )

    timeline_str = "\n".join(timeline)
    paths_str = "\n".join(paths)
    badges_str = "\n".join(badges)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg height="100%" version="1.1" width="100%" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 110 110" style="background:#181a1f; border-radius:16px;">
<style type="text/css"><![CDATA[
/* ============================================================
   BẢNG THÔNG SỐ ĐIỀU CHỈNH ({kanji_char})
   ============================================================ */

/* 1. HIỆU ỨNG VẼ NÉT & HIỆN SỐ */
@keyframes drawStroke {{
    0%   {{ opacity: 1; }}
    100% {{ stroke-dashoffset: 0; opacity: 1; }}
}}

@keyframes softFade {{
    from {{ opacity: 0; }}
    to   {{ opacity: 1; }}
}}

/* 2. ĐƯỜNG LƯỚI CHỮ THẬP NỀN (Màu xám tối, nét đứt 4-2) */
.grid-cross {{
    stroke: #2d333b;
    stroke-width: 0.6;
    stroke-dasharray: 4, 2;
}}

/* 3. NÉT VẼ BÚT THUẬN:
   - stroke-width: Độ dày nét bút (2.8 là chuẩn thanh mảnh)
   - opacity: 0 để triệt tiêu lỗi chấm đầu nét lúc chưa vẽ */
.stroke {{
    stroke-width: 2.8 !important;
    stroke-linecap: round !important;
    stroke-linejoin: round !important;
    fill: none;
    opacity: 0;
}}

/* 4. HIỆU ỨNG HIỆN QUẢ BÓNG */
.badge-group {{
    opacity: 0;
    animation: softFade 0.2s ease-out forwards;
}}

/* 5. ĐỊNH DẠNG SỐ MỘT CHỮ SỐ (1-9) */
.num-single {{
    font-family: "Segoe UI", -apple-system, sans-serif, "Arial Narrow", "Roboto Condensed";
    font-size: 7.6px !important;        /* Cỡ chữ */
    font-weight: 375 !important;        /* Độ mảnh */
    font-style: normal !important;
    fill: #ffffff !important;
    text-anchor: middle;
    dominant-baseline: central;
}}

/* 5. ĐỊNH DẠNG SỐ HAI CHỮ SỐ (10 TRỞ LÊN) */
.num-double {{
    font-family: "Segoe UI", -apple-system, sans-serif, "Arial Narrow", "Roboto Condensed";
    font-size: 6.5px !important;        /* Giảm cỡ chữ để trông gọn hơn so với số một chữ số */
    font-weight: 375 !important;        /* Tăng nhẹ nét mực để độ dày phù hợp hơn */
    font-style: normal !important;
    letter-spacing: -0.35px !important;
    fill: #ffffff !important;
    text-anchor: middle;
    dominant-baseline: central;
}}

/* ============================================================
   TIMELINE ĐIỀU KHIỂN THỜI GIAN:
   - #{kanji_char}-bg[i]: Thời gian quả bóng số nảy lên
   - #{kanji_char}-s[i]:  Độ dài nét vẽ và thời gian ngọn bút bắt đầu chạy
   ============================================================ */
{timeline_str}
]]>
</style>

<!-- LƯỚI CHỮ THẬP CỐ ĐỊNH -->
<path class="grid-cross" d="M55,0 L55,110" /><path class="grid-cross" d="M0,55 L110,55" />

<!-- {len(strokes)} ĐƯỜNG NÉT VẼ (QUY TẮC ID SCOPING: #{kanji_char}-s[i]) -->
{paths_str}

<!-- ============================================================
     BẢNG {len(strokes)} QUẢ BÓNG SỐ (ĐỒNG BỘ BÁN KÍNH r="3.5"):
     - circle: cx, cy là tâm quả bóng; r="3.5" là bán kính quả bóng
     - text:   x, y luôn đặt BẰNG ĐÚNG cx, cy của hình tròn
     - dx:     Cần gạt ngang (âm: kéo sang trái | dương: sang phải)
     - dy:     Cần gạt dọc   (âm: nhấc lên trên | dương: hạ xuống dưới)
     ============================================================ -->
{badges_str}
</svg>"""


# ============================================================
# 4. DỰNG FILE MARKDOWN GHI CHÚ
# ============================================================
def build_md(meta):
    jlpt_lower = meta["jlpt"].lower() if meta["jlpt"] else "n5"
    do_thong_dung_str = (
        f"{meta['do_thong_dung']}" if meta["do_thong_dung"] else '""'
    )

    return f"""---
kanji: {meta['kanji']}
han_viet: {meta['han_viet']}
jlpt: {meta['jlpt']}
so_net: {meta['so_net']}
bo_thu: ""
luc_thu: ""
on: {meta['on']}
kun: {meta['kun']}
nghia: {meta['nghia']}
tags:
  - kanji/{jlpt_lower}
  - luc-thu
order: {meta['order']}
do_thong_dung: {do_thong_dung_str}
---

```dataviewjs
await eval(await app.vault.adapter.read(`${{app.vault.configDir}}/scripts/kanji-view.js`));
```

---

### 1. Chiết tự & Nguồn gốc (Lục thư)

---

### 2. Từ vựng ghép quan trọng
"""


# ============================================================
# 5. HÀM CHỜ MAZII VẼ XONG 100% NÉT
# ============================================================
def wait_until_mazii_finishes(page, expected_strokes):
    """Đợi Mazii hoàn thành toàn bộ các nét vẽ."""
    for _ in range(40):  # Tối đa 20s
        count = page.evaluate("""() => {
            const svg = document.querySelector('svg.dmak-svg');
            if (!svg) return 0;
            return Array.from(svg.querySelectorAll('path')).filter(p => {
                const d = p.getAttribute('d') || '';
                return !d.startsWith('M55,0') && !d.startsWith('M0,55');
            }).length;
        }""")
        # Đã vẽ đủ số nét dự kiến
        if expected_strokes > 0 and count >= expected_strokes:
            return count
        page.wait_for_timeout(500)
    return count


# ============================================================
# 6. HÀM CÀO 1 CHỮ HÁN TỰ ĐỘNG
# ============================================================
def crawl_single_kanji(page, kanji_char, order_num, kanji_colors):
    md_file = os.path.join(MD_OUTPUT_DIR, f"{kanji_char}.md")
    svg_file = os.path.join(SVG_OUTPUT_DIR, f"{kanji_char}.svg")

    # Bỏ qua nếu cả 2 file đã tồn tại
    if SKIP_EXISTING and os.path.exists(md_file) and os.path.exists(svg_file):
        print(
            f"⏩ Bỏ qua '{kanji_char}' (Đã tồn tại file .md và .svg) -> Order: {order_num}"
        )
        return True

    encoded = urllib.parse.quote(kanji_char)
    url = f"https://mazii.net/vi-VN/search/kanji/javi/{encoded}"
    print(
        f"\n--> [{order_num}] Đang cào chữ: '{kanji_char}' từ Mazii..."
    )

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector(".kanji-main-infor", timeout=15000)

        # Lấy số nét dự kiến từ giao diện
        expected_strokes = page.evaluate("""() => {
            const titles = Array.from(document.querySelectorAll('.item-title, h2'));
            const strokeTitle = titles.find(t => t.textContent.includes('Số nét'));
            if (strokeTitle && strokeTitle.parentElement) {
                const info = strokeTitle.parentElement.querySelector('.item-infor');
                return info ? parseInt(info.textContent.trim(), 10) : 0;
            }
            return 0;
        }""")

        # Đợi vẽ xong toàn bộ nét
        wait_until_mazii_finishes(page, expected_strokes)
        page.wait_for_timeout(800)

    except Exception as e:
        print(f"❌ Không tải được trang Mazii cho chữ '{kanji_char}': {e}")
        return False

    # Bóc tách dữ liệu chuẩn xác
    data = page.evaluate("""() => {
        const root = document.querySelector('.kanji-main-infor');
        if (!root) return null;

        // 1. Hán Việt: Lấy toàn bộ chữ in hoa
        const hvElem = root.querySelector('.han-viet-word');
        let han_viet = "";
        if (hvElem) {
            han_viet = hvElem.textContent.replace(/[\\r\\n]+/g, ' ').trim().toUpperCase();
        }

        // 2. Kunyomi: Tách riêng từng thẻ .japanese-char
        const kunSpans = Array.from(root.querySelectorAll('.item-infor-kun .japanese-char'));
        const kun = kunSpans.map(s => s.textContent.trim()).filter(Boolean).join(', ');

        // 3. Onyomi: Bỏ dấu chấm phẩy thừa
        const onSpans = Array.from(root.querySelectorAll('.item-infor-on .japanese-char'));
        const on = onSpans.map(s => s.textContent.trim()).filter(t => t && t !== ';' && t !== ',').join(', ');

        // 4. Số nét, JLPT, Tần suất
        let so_net = 0;
        let jlpt = "N5";
        let do_thong_dung = "";

        const lineItems = Array.from(root.querySelectorAll('.line-item'));
        lineItems.forEach(item => {
            const title = item.querySelector('.item-title')?.textContent || "";
            const info = item.querySelector('.item-infor')?.textContent || "";

            if (title.includes("Số nét")) {
                so_net = parseInt(info.trim(), 10) || 0;
            } else if (title.includes("JLPT")) {
                jlpt = info.trim();
            } else if (title.includes("Tần suất")) {
                const match = info.match(/#?(\\d+)/);
                if (match) do_thong_dung = match[1];
            }
        });

        // 5. Nghĩa: Bỏ thẻ ví dụ và bỏ câu chứa tiếng Nhật
        const meanLis = Array.from(root.querySelectorAll('.item-infor-mean li'));
        const meanings = [];
        meanLis.forEach(li => {
            let text = "";
            for (const node of li.childNodes) {
                if (node.nodeType === Node.TEXT_NODE) {
                    const t = node.textContent.trim();
                    if (t && !t.startsWith("VD:") && !t.startsWith("::marker")) {
                        text = t;
                        break;
                    }
                }
            }
            if (!text) {
                text = li.textContent.replace('::marker', '').split(/VD:|VD\\s*:/i)[0].trim();
            }
            // Loại bỏ câu tiếng Nhật bị lọt vào
            if (text && !/[\\u3040-\\u30ff\\u4e00-\\u9faf]/.test(text) && !meanings.includes(text)) {
                meanings.push(text);
            }
        });
        const nghia = meanings.join(', ');

        // 6. SVG Paths & Độ dài 4 số thập phân
        const svg = root.querySelector('svg.dmak-svg');
        const paths = [];
        if (svg) {
            const allPaths = Array.from(svg.querySelectorAll('path')).filter(p => {
                const d = p.getAttribute('d') || '';
                return !d.startsWith('M55,0') && !d.startsWith('M0,55');
            });

            allPaths.forEach((p) => {
                const d = p.getAttribute('d');
                let length = 50.0;
                const styleStr = p.getAttribute('style') || '';
                const dashMatch = styleStr.match(/stroke-dasharray:\\s*([0-9.]+)/);
                if (dashMatch) {
                    length = parseFloat(dashMatch[1]);
                } else {
                    try { length = p.getTotalLength(); } catch(e) {}
                }

                const mMatch = d.match(/^[Mm]\\s*([0-9.]+)[,\\s]+([0-9.]+)/);
                const startX = mMatch ? parseFloat(mMatch[1]) : 55.0;
                const startY = mMatch ? parseFloat(mMatch[2]) : 55.0;

                paths.push({ d, length, startX, startY });
            });
        }

        return { han_viet, kun, on, so_net, jlpt, do_thong_dung, nghia, paths };
    }""")

    if not data or not data["paths"]:
        print(f"❌ Không trích xuất được nét vẽ của '{kanji_char}'!")
        return False

    # Lấy màu từ JSON hoặc Spectrum dự phòng
    preset_colors = kanji_colors.get(kanji_char, [])
    total_strokes = len(data["paths"])

    # Báo ngay lên màn hình nếu chữ bị thiếu trong file JSON màu
    if not preset_colors:
        print(f"⚠️ CẢNH BÁO: Chữ '{kanji_char}' CHƯA CÓ TRONG JSON -> Đang dùng màu Fallback!")
    elif len(preset_colors) < total_strokes:
        print(f"⚠️ CẢNH BÁO: Chữ '{kanji_char}' bị thiếu màu (chỉ có {len(preset_colors)}/{total_strokes} nét) -> Dùng Fallback cho nét thiếu!")

    strokes = []
    current_time = 0.05

    for idx, p in enumerate(data["paths"], start=1):
        color = (
            preset_colors[idx - 1]
            if idx - 1 < len(preset_colors)
            else get_fallback_color(idx - 1, total_strokes)
        )
        duration = round(min(0.55, max(0.22, p["length"] * 0.0055)), 2)

        strokes.append(
            {
                "idx": idx,
                "d": p["d"],
                "color": color,
                "length": round(p["length"], 4),
                "x": round(p["startX"], 2),
                "y": round(p["startY"], 2),
                "bg_delay": round(current_time, 2),
                "stroke_delay": round(current_time + 0.13, 2),
                "duration": duration,
            }
        )
        current_time += duration + 0.15

    # Chống đè bóng (< 7px)
    for j in range(len(strokes) - 1):
        for k in range(j + 1, len(strokes)):
            dist = (
                (strokes[j]["x"] - strokes[k]["x"]) ** 2
                + (strokes[j]["y"] - strokes[k]["y"]) ** 2
            ) ** 0.5
            if dist < 7.0:
                strokes[j]["y"] = round(strokes[j]["y"] - 3.5, 2)
                strokes[k]["y"] = round(strokes[k]["y"] + 3.5, 2)

    # Ghi file SVG
    svg_data = build_svg(kanji_char, strokes)
    with open(svg_file, "w", encoding="utf-8") as f:
        f.write(svg_data)

    # Ghi file MD
    meta = {
        "kanji": kanji_char,
        "han_viet": data["han_viet"],
        "jlpt": data["jlpt"] or "N5",
        "so_net": data["so_net"] or total_strokes,
        "on": data["on"],
        "kun": data["kun"],
        "nghia": data["nghia"],
        "order": order_num,
        "do_thong_dung": data["do_thong_dung"],
    }
    md_data = build_md(meta)
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_data)

    print(
        f"✅ Xong '{kanji_char}' ({meta['so_net']} nét) | HV: {meta['han_viet']} | Tần suất: {meta['do_thong_dung']} | On: {meta['on']} | Kun: {meta['kun']}"
    )
    return True


# ============================================================
# 7. ĐIỀU KHIỂN CHÍNH
# ============================================================
def main():
    kanji_list = load_kanji_list()
    if not kanji_list:
        return

    print(
        f"🚀 BẮT ĐẦU CÀO TỰ ĐỘNG {len(kanji_list)} CHỮ HÁN TỪ '{INPUT_FILE}'..."
    )
    print(f"📁 Thư mục xuất Markdown: {MD_OUTPUT_DIR}")
    print(f"📁 Thư mục xuất SVG     : {SVG_OUTPUT_DIR}")

    kanji_colors = load_kanji_colors()
    if kanji_colors:
        print(f"🎨 Đã nạp bảng màu JSON ({len(kanji_colors)} chữ).")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        success_count = 0
        # levels = ["N5", "N4", "N3", "N2", "N1"]
        # levels = ["N5", "N4", "N3"]
        levels = ["N2"]
        for block_idx, group in enumerate(kanji_list):
            lvl_name = levels[block_idx] if block_idx < len(levels) else f"Đoạn {block_idx + 1}"
            print(f"\n==================================================================")
            print(f"🎌 BẮT ĐẦU CÀO CẤP ĐỘ {lvl_name}: {len(group)} CHỮ (ORDER BẮT ĐẦU LẠI TỪ 1)")
            print(f"==================================================================")

            # Mỗi đoạn đều bắt đầu đếm order từ 1 độc lập
            for idx, char in enumerate(group, start=1):
                crawl_single_kanji(page, char, idx, kanji_colors)
                page.wait_for_timeout(300)

        browser.close()

    print(
        f"\n🎉 HOÀN THÀNH TOÀN BỘ! Đã xuất {success_count}/{len(kanji_list)} chữ Hán chuẩn xác vào hệ thống."
    )


if __name__ == "__main__":
    main()