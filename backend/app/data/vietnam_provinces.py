"""Current provincial-level units grouped into broad cinema-search regions."""

REGION_PROVINCES = {
    "Miền Bắc": (
        "Thành phố Hà Nội",
        "Thành phố Hải Phòng",
        "Quảng Ninh",
        "Bắc Ninh",
        "Hưng Yên",
        "Ninh Bình",
        "Phú Thọ",
        "Thái Nguyên",
        "Tuyên Quang",
        "Lào Cai",
        "Cao Bằng",
        "Lạng Sơn",
        "Lai Châu",
        "Điện Biên",
        "Sơn La",
    ),
    "Miền Trung": (
        "Thanh Hóa",
        "Nghệ An",
        "Hà Tĩnh",
        "Quảng Trị",
        "Thành phố Huế",
        "Thành phố Đà Nẵng",
        "Quảng Ngãi",
        "Gia Lai",
        "Đắk Lắk",
        "Khánh Hòa",
        "Lâm Đồng",
    ),
    "Miền Nam": (
        "Thành phố Hồ Chí Minh",
        "Đồng Nai",
        "Tây Ninh",
        "Đồng Tháp",
        "Vĩnh Long",
        "An Giang",
        "Thành phố Cần Thơ",
        "Cà Mau",
    ),
}

PROVINCE_ALIASES = {
    "hà nội": "Thành phố Hà Nội",
    "tp hà nội": "Thành phố Hà Nội",
    "thành phố hà nội": "Thành phố Hà Nội",
    "hải phòng": "Thành phố Hải Phòng",
    "tp hải phòng": "Thành phố Hải Phòng",
    "thành phố hải phòng": "Thành phố Hải Phòng",
    "huế": "Thành phố Huế",
    "thành phố huế": "Thành phố Huế",
    "đà nẵng": "Thành phố Đà Nẵng",
    "tp đà nẵng": "Thành phố Đà Nẵng",
    "thành phố đà nẵng": "Thành phố Đà Nẵng",
    "tp.hcm": "Thành phố Hồ Chí Minh",
    "tp hcm": "Thành phố Hồ Chí Minh",
    "tp. hồ chí minh": "Thành phố Hồ Chí Minh",
    "tp hồ chí minh": "Thành phố Hồ Chí Minh",
    "hồ chí minh": "Thành phố Hồ Chí Minh",
    "thành phố hồ chí minh": "Thành phố Hồ Chí Minh",
    "cần thơ": "Thành phố Cần Thơ",
    "tp cần thơ": "Thành phố Cần Thơ",
    "thành phố cần thơ": "Thành phố Cần Thơ",
    "bình định": "Gia Lai",
    "phú yên": "Đắk Lắk",
    "kon tum": "Quảng Ngãi",
    "quảng nam": "Thành phố Đà Nẵng",
    "thừa thiên huế": "Thành phố Huế",
    "quảng bình": "Quảng Trị",
    "ninh thuận": "Khánh Hòa",
    "bình thuận": "Lâm Đồng",
    "đắk nông": "Lâm Đồng",
    "bình dương": "Thành phố Hồ Chí Minh",
    "bà rịa - vũng tàu": "Thành phố Hồ Chí Minh",
    "bà rịa-vũng tàu": "Thành phố Hồ Chí Minh",
    "bà rịa vũng tàu": "Thành phố Hồ Chí Minh",
    "bình phước": "Đồng Nai",
    "long an": "Tây Ninh",
    "tiền giang": "Đồng Tháp",
    "bến tre": "Vĩnh Long",
    "trà vinh": "Vĩnh Long",
    "kiên giang": "An Giang",
    "hậu giang": "Thành phố Cần Thơ",
    "sóc trăng": "Thành phố Cần Thơ",
    "bạc liêu": "Cà Mau",
    "bắc giang": "Bắc Ninh",
    "bắc kạn": "Thái Nguyên",
    "hà giang": "Tuyên Quang",
    "hòa bình": "Phú Thọ",
    "vĩnh phúc": "Phú Thọ",
    "yên bái": "Lào Cai",
    "hải dương": "Thành phố Hải Phòng",
    "thái bình": "Hưng Yên",
    "hà nam": "Ninh Bình",
    "nam định": "Ninh Bình",
    "biên hòa": "Đồng Nai",
    "bà rịa": "Thành phố Hồ Chí Minh",
    "bảo lộc": "Lâm Đồng",
    "đà lạt": "Lâm Đồng",
    "hạ long": "Quảng Ninh",
    "long xuyên": "An Giang",
    "nha trang": "Khánh Hòa",
    "phan thiết": "Lâm Đồng",
    "quy nhơn": "Gia Lai",
    "rạch giá": "An Giang",
    "thủ dầu một": "Thành phố Hồ Chí Minh",
    "vị thanh (hậu giang)": "Thành phố Cần Thơ",
    "vinh": "Nghệ An",
    "việt trì": "Phú Thọ",
    "vũng tàu": "Thành phố Hồ Chí Minh",
    "thừa thiên - huế": "Thành phố Huế",
}
PROVINCE_ALIASES.update({
    province.casefold(): province
    for provinces in REGION_PROVINCES.values()
    for province in provinces
})


def normalize_province(value):
    return PROVINCE_ALIASES.get(" ".join(value.casefold().split()))


def region_for_province(province):
    return next(
        (region for region, provinces in REGION_PROVINCES.items() if province in provinces),
        None,
    )


def province_catalog():
    return [
        {"name": province, "region": region}
        for region, provinces in REGION_PROVINCES.items()
        for province in provinces
    ]
