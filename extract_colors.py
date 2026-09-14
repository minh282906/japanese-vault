import os
import re
import json

# ============================================================
# CẤU HÌNH ĐƯỜNG DẪN ĐẾN THƯ MỤC SPECTRUM CỦA BẠN
# ============================================================
SPECTRUM_DIR = r"D:\日本\日本語\storage\colorized-kanji-spectrum"

# ============================================================
# HÀM LẤY DANH SÁCH MÀU CỦA 1 CHỮ HÁN CỤ THỂ
# ============================================================
def get_colors_of_kanji(kanji_char):
    # 1. Tìm theo mã Hex 5 số (ví dụ: 065e5.svg)
    hex_code = f"{ord(kanji_char):05x}"
    target_file = os.path.join(SPECTRUM_DIR, f"{hex_code}.svg")
    
    # 2. Nếu không có, tìm theo tên chữ tiếng Nhật (phòng trường hợp bạn đã đổi tên)
    if not os.path.exists(target_file):
        target_file = os.path.join(SPECTRUM_DIR, f"{kanji_char}.svg")
        
    if not os.path.exists(target_file):
        print(f"❌ Không tìm thấy file màu cho chữ: {kanji_char} (Mã Hex: {hex_code})")
        return []

    # 3. Đọc nội dung file và bốc tách mã màu stroke: #xxxxxx
    with open(target_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Chỉ tìm trong các thẻ path của nét vẽ (id="kvg:...-s...")
    stroke_paths = re.findall(r'<path[^>]+id="kvg:[0-9a-fA-F]+-s\d+"[^>]*>', content)
    colors = []
    for p in stroke_paths:
        m = re.search(r'stroke:\s*(#[0-9a-fA-F]{6})', p)
        if m:
            colors.append(m.group(1))

    return colors

# ============================================================
# HÀM QUÉT TOÀN BỘ VÀ XUẤT RA FILE JSON TỪ ĐIỂN MÀU
# ============================================================
def export_all_colors_to_json(output_json="kanji_colors.json"):
    print(f"--> Đang quét thư mục: {SPECTRUM_DIR}...")
    color_dict = {}
    
    for fname in os.listdir(SPECTRUM_DIR):
        if not fname.endswith(".svg"):
            continue
            
        # Bỏ qua các file biến thể có đuôi như -Kaisho, -Insatsu
        base = fname[:-4]
        if not re.match(r'^[0-9a-fA-F]{5}$', base):
            continue
            
        try:
            char = chr(int(base, 16))
        except ValueError:
            continue
            
        filepath = os.path.join(SPECTRUM_DIR, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        stroke_paths = re.findall(r'<path[^>]+id="kvg:[0-9a-fA-F]+-s\d+"[^>]*>', content)
        colors = []
        for p in stroke_paths:
            m = re.search(r'stroke:\s*(#[0-9a-fA-F]{6})', p)
            if m:
                colors.append(m.group(1))
                
        if colors:
            color_dict[char] = colors

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(color_dict, f, ensure_ascii=False, indent=2)
        
    print(f"✅ ĐÃ XUẤT THÀNH CÔNG TỪ ĐIỂN MÀU: {output_json} ({len(color_dict)} chữ Hán)")

# ============================================================
# CHẠY THỬ NGHIỆM
# ============================================================
if __name__ == "__main__":
    # Test thử 3 chữ mẫu:
    test_chars = ["日", "休", "聞"]
    for c in test_chars:
        c_list = get_colors_of_kanji(c)
        print(f"🎨 Chữ '{c}' ({len(c_list)} nét): {c_list}")
        
    # Tạo luôn file từ điển màu json để sẵn sàng dùng cho bước sau:
    print("-" * 50)
    export_all_colors_to_json()