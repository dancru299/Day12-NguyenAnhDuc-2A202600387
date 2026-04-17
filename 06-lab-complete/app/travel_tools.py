"""
Travel Tools — Mock data cho TravelBuddy Agent.
Được tích hợp từ Lab 4 (Day 3) vào production stack Day 12.
"""
from langchain_core.tools import tool

# ============================================================
# MOCK DATA
# ============================================================

FLIGHTS_DB = {
    ("Hà Nội", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "07:20", "price": 1450000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "14:00", "arrival": "15:20", "price": 2800000, "class": "business"},
        {"airline": "VietJet Air", "departure": "08:30", "arrival": "09:50", "price": 890000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "11:00", "arrival": "12:20", "price": 1200000, "class": "economy"},
    ],
    ("Hà Nội", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "07:00", "arrival": "09:15", "price": 2100000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "10:00", "arrival": "12:15", "price": 1350000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "16:00", "arrival": "18:15", "price": 1100000, "class": "economy"},
    ],
    ("Hà Nội", "Hồ Chí Minh"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "08:10", "price": 1600000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "07:30", "arrival": "09:40", "price": 950000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "12:00", "arrival": "14:10", "price": 1300000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "18:00", "arrival": "20:10", "price": 3200000, "class": "business"},
    ],
    ("Hồ Chí Minh", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "09:00", "arrival": "10:20", "price": 1300000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "13:00", "arrival": "14:20", "price": 780000, "class": "economy"},
    ],
    ("Hồ Chí Minh", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "08:00", "arrival": "09:00", "price": 1100000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "15:00", "arrival": "16:00", "price": 650000, "class": "economy"},
    ],
}

HOTELS_DB = {
    "Đà Nẵng": [
        {"name": "Mường Thanh Luxury", "stars": 5, "price_per_night": 1800000, "area": "Mỹ Khê", "rating": 4.5},
        {"name": "Sala Danang Beach", "stars": 4, "price_per_night": 1200000, "area": "Mỹ Khê", "rating": 4.3},
        {"name": "Fivitel Danang", "stars": 3, "price_per_night": 650000, "area": "Sơn Trà", "rating": 4.1},
        {"name": "Memory Hostel", "stars": 2, "price_per_night": 250000, "area": "Hải Châu", "rating": 4.6},
        {"name": "Christina's Homestay", "stars": 2, "price_per_night": 350000, "area": "An Thượng", "rating": 4.7},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Resort", "stars": 5, "price_per_night": 3500000, "area": "Bãi Dài", "rating": 4.4},
        {"name": "Sol by Meliá", "stars": 4, "price_per_night": 1500000, "area": "Bãi Trường", "rating": 4.2},
        {"name": "Lahana Resort", "stars": 3, "price_per_night": 800000, "area": "Dương Đông", "rating": 4.0},
        {"name": "9Station Hostel", "stars": 2, "price_per_night": 200000, "area": "Dương Đông", "rating": 4.5},
    ],
    "Hồ Chí Minh": [
        {"name": "Rex Hotel", "stars": 5, "price_per_night": 2800000, "area": "Quận 1", "rating": 4.3},
        {"name": "Liberty Central", "stars": 4, "price_per_night": 1400000, "area": "Quận 1", "rating": 4.1},
        {"name": "Cochin Zen Hotel", "stars": 3, "price_per_night": 550000, "area": "Quận 3", "rating": 4.4},
        {"name": "The Common Room", "stars": 2, "price_per_night": 180000, "area": "Quận 1", "rating": 4.6},
    ],
}


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", ".") + "đ"


@tool
def search_flights(origin: str, destination: str) -> str:
    """Tìm danh sách chuyến bay giữa hai địa điểm dựa trên dữ liệu mẫu."""
    flights = FLIGHTS_DB.get((origin, destination))
    if not flights:
        flights = FLIGHTS_DB.get((destination, origin))
    if not flights:
        return f"Không tìm thấy chuyến bay từ {origin} đến {destination}."
    result = f"Các chuyến bay từ {origin} đến {destination}:\n"
    for f in flights:
        result += (
            f"- {f['airline']} | {f['departure']} → {f['arrival']} | "
            f"{format_price(f['price'])} | {f['class']}\n"
        )
    return result


@tool
def search_hotels(city: str, max_price_per_night: int = 99999999) -> str:
    """Tìm khách sạn theo thành phố và lọc theo giá tối đa mỗi đêm."""
    hotels = HOTELS_DB.get(city)
    if not hotels:
        return f"Không tìm thấy khách sạn tại {city}."
    filtered = [h for h in hotels if h["price_per_night"] <= max_price_per_night]
    if not filtered:
        return f"Không tìm thấy khách sạn tại {city} với giá dưới {format_price(max_price_per_night)}/đêm."
    filtered.sort(key=lambda x: x["rating"], reverse=True)
    result = f"Khách sạn tại {city}:\n"
    for h in filtered:
        result += (
            f"- {h['name']} | {h['stars']}⭐ | "
            f"{format_price(h['price_per_night'])}/đêm | "
            f"{h['area']} | rating {h['rating']}\n"
        )
    return result


@tool
def calculate_budget(total_budget: int, expenses: str, nights: int = 1) -> str:
    """Tính tổng ngân sách chuyến đi.
    expenses format: 'tên:số_tiền,tên:số_tiền' (VD: 'vé_máy_bay:890000,khách_sạn:650000')
    nights: số đêm ở - sẽ tự động nhân với các mục có từ 'khách_sạn' trong tên.
    """
    try:
        items = expenses.split(",")
        expense_dict = {}
        for item in items:
            name, value = item.split(":")
            name = name.strip()
            amount = int(value.strip())
            if nights > 1 and "khách" in name.lower():
                amount = amount * nights
                name = f"{name} ({nights} đêm)"
            expense_dict[name] = amount
        total_expense = sum(expense_dict.values())
        remaining = total_budget - total_expense
        result = "Bảng chi phí:\n"
        for k, v in expense_dict.items():
            result += f"- {k}: {format_price(v)}\n"
        result += "---\n"
        result += f"Tổng chi: {format_price(total_expense)}\n"
        result += f"Ngân sách: {format_price(total_budget)}\n"
        result += f"Còn lại: {format_price(remaining)}\n"
        if remaining < 0:
            result += f"⚠️ Vượt ngân sách {format_price(abs(remaining))}!"
        return result
    except Exception:
        return "Lỗi: format expenses không hợp lệ. Ví dụ đúng: 'vé_máy_bay:890000,khách_sạn:650000'"
