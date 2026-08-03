# -*- coding: utf-8 -*-
"""农历模块(零依赖):公历 → 农历 / 干支 / 节气 / 传统节日。

实现说明:
- 农历:内置 1900-2100 年农历数据表(16 进制编码每月大小月与闰月),经典算法;
- 干支:按农历年/月/日推算天干地支;
- 节气:通用近似公式(1900-2100 年多数日期准确);
- 节日:农历月日匹配传统节日(春节/端午/中秋等)。

用法:
    from lunar import get_today_lunar
    info = get_today_lunar()   # 或 get_lunar_info(datetime.date)
    # info = {"lunar": "农历六月初十", "ganzhi": "丙午年 甲午月 庚寅日", "term": "小暑", "festival": ""}
"""

import datetime

# ============ 农历数据表(1900-2100)============
# 每年一个 16 进制整数:低 12 位表示 1-12 月大小(1=30天,0=29天);
# bit16-18 表示闰月月份(0=无闰月);bit19 表示闰月是否大月
LUNAR_INFO = [
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,  # 1900-1909
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,  # 1910-1919
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,  # 1920-1929
    0x06566, 0x0d4a0, 0x0ea50, 0x16a95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,  # 1930-1939
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,  # 1940-1949
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,  # 1950-1959
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,  # 1960-1969
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,  # 1970-1979
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,  # 1980-1989
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x05ac0, 0x0ab60, 0x096d5, 0x092e0,  # 1990-1999
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,  # 2000-2009
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,  # 2010-2019
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,  # 2020-2029
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,  # 2030-2039
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,  # 2040-2049
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06aa0, 0x1a6c4, 0x0aae0,  # 2050-2059
    0x092e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,  # 2060-2069
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,  # 2070-2079
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,  # 2080-2089
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,  # 2090-2099
    0x0d520,                                                                                       # 2100
]

# ============ 名称表 ============
CN_MONTH = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
CN_DAY = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
          "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
TERMS = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
         "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
         "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]

# 节气分钟偏移表(以 1900-01-06 02:05 小寒为基准,经典 sxwnl 算法)
S_TERM_INFO = [0, 21208, 42467, 63836, 85337, 107014, 128867, 150921, 173149, 195551,
               218072, 240693, 263343, 285989, 308563, 331033, 353350, 375494, 397447,
               419210, 440795, 462224, 483532, 504758]

# 农历节日:月 → {日: 节日名}
LUNAR_FESTIVALS = {
    1: {1: "春节", 15: "元宵节"},
    2: {2: "龙抬头"},
    5: {5: "端午节"},
    7: {7: "七夕节", 15: "中元节"},
    8: {15: "中秋节"},
    9: {9: "重阳节"},
    12: {8: "腊八节", 23: "北方小年", 24: "南方小年", 30: "除夕"},
}


def _lunar_mon_days(year: int, month: int) -> int:
    """农历 year 年第 month 月的天数(30 或 29)。"""
    return 30 if LUNAR_INFO[year - 1900] & (0x10000 >> month) else 29


def _leap_month(year: int) -> int:
    """农历 year 年的闰月月份(0=无闰月)。"""
    return LUNAR_INFO[year - 1900] & 0xF


def _leap_days(year: int) -> int:
    """闰月天数:无闰月返回 0;有闰月返回 30 或 29(看 bit16)。"""
    if _leap_month(year) == 0:
        return 0
    return 30 if LUNAR_INFO[year - 1900] & 0x10000 else 29


def lunar_from_solar(date: datetime.date) -> tuple:
    """公历 → (农历年, 农历月, 农历日, 是否闰月)。"""
    # 基准:1900-01-31 = 农历 1900 年正月初一
    base = datetime.date(1900, 1, 31)
    offset = (date - base).days
    if offset < 0 or offset > 73586:
        raise ValueError("仅支持 1900-2100 年")
    lunar_year = 1900
    while lunar_year < 2100:
        days_of_year = 0
        for m in range(1, 13):
            days_of_year += _lunar_mon_days(lunar_year, m)
        days_of_year += _leap_days(lunar_year)
        if offset < days_of_year:
            break
        offset -= days_of_year
        lunar_year += 1
    leap = _leap_month(lunar_year)
    is_leap = False
    lunar_month = 1
    days = _lunar_mon_days(lunar_year, 1)
    while True:
        if offset < days:
            break
        offset -= days
        if leap == lunar_month and not is_leap:
            is_leap = True
            days = _leap_days(lunar_year)  # 月号不变,处理闰月
        else:
            is_leap = False  # 离开闰月块,恢复普通月
            lunar_month += 1
            if lunar_month > 12:
                break
            days = _lunar_mon_days(lunar_year, lunar_month)
    return lunar_year, lunar_month, offset + 1, is_leap


def lunar_date_str(date: datetime.date) -> str:
    """如「六月初十」;闰月加『闰』。"""
    y, m, d, is_leap = lunar_from_solar(date)
    prefix = "闰" if is_leap else ""
    return f"农历{prefix}{CN_MONTH[m - 1]}月{CN_DAY[d - 1]}"


def ganzhi(date: datetime.date) -> str:
    """干支纪年·月·日(简版:年按农历年,月日按公历近似)。"""
    y, m, d, _ = lunar_from_solar(date)
    year_gan = TIAN_GAN[(y - 4) % 10]
    year_zhi = DI_ZHI[(y - 4) % 12]
    # 月干支:按农历月近似(正月起丙寅)
    month_gan = TIAN_GAN[(y * 12 + m + 2) % 10]
    month_zhi = DI_ZHI[(m + 2) % 12]
    # 日干支:基准 1900-01-31(甲午日)推算
    base = datetime.date(1900, 1, 31)
    offset = (date - base).days
    day_gan = TIAN_GAN[(offset + 30) % 10]  # 1900-01-31 为甲午日,甲=0
    day_zhi = DI_ZHI[(offset + 6) % 12]     # 午=6
    return f"{year_gan}{year_zhi}年 {month_gan}{month_zhi}月 {day_gan}{day_zhi}日"


def solar_term(date: datetime.date) -> str:
    """当天是节气则返回节气名,否则空串(经典 sTermInfo 算法,1900-2100 准确)。"""
    y = date.year
    base = datetime.datetime(1900, 1, 6, 2, 5)  # 1900 年小寒
    for n in range(24):
        t = base + datetime.timedelta(minutes=S_TERM_INFO[n] + (y - 1900) * 525948.766)
        if t.year == y and t.month == date.month and t.day == date.day:
            return TERMS[n]
    return ""


def festival(date: datetime.date) -> str:
    """当天是农历节日则返回节日名,否则空串。"""
    y, m, d, is_leap = lunar_from_solar(date)
    if is_leap:
        return ""
    return LUNAR_FESTIVALS.get(m, {}).get(d, "")


def get_lunar_info(date: datetime.date) -> dict:
    """综合农历信息:日期/干支/节气/节日。"""
    return {
        "lunar": lunar_date_str(date),
        "ganzhi": ganzhi(date),
        "term": solar_term(date),
        "festival": festival(date),
    }


def get_today_lunar() -> dict:
    return get_lunar_info(datetime.date.today())


if __name__ == "__main__":
    import sys
    for s in sys.argv[1:] or [str(datetime.date.today())]:
        d = datetime.date.fromisoformat(s)
        info = get_lunar_info(d)
        parts = [info["lunar"], info["ganzhi"]]
        if info["term"]:
            parts.append(f"节气:{info['term']}")
        if info["festival"]:
            parts.append(f"节日:{info['festival']}")
        print(f"{s} → {' · '.join(parts)}")