from __future__ import annotations
# === Puja Booking — 100 Hardcoded Pandits (₹500–₹1000), Proximity + Time + Day Availability, Text+Voice ===

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Literal
import re, os, json, math
from datetime import datetime, timedelta, date, time as dtime
from zoneinfo import ZoneInfo

import dateparser
from pydantic import BaseModel, Field
import gradio as gr
from openai import OpenAI
from rapidfuzz import process, fuzz

# ---- OpenAI key from env (set in HF: Settings → Variables and secrets) ----
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it in your Space: Settings → Variables and secrets.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

TZ = "Asia/Kolkata"
IST = ZoneInfo(TZ)

# ---------- Puja Catalog ----------
PUJA_CATALOG = [
    "Satyanarayan Katha","Griha Pravesh","Mundan","Rudra Abhishek",
    "Ganesh Puja","Navgrah Shanti","Durga Puja","Lakshmi Puja",
    "Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja","Hanuman Puja",
    "Sundarkand Path","Katha & Havan","Vastu Shanti","Narayan Nagbali",
    "Saraswati Puja","Chandi Path","Navratri Puja","Sat Chandi Yagya"
]

# ---------- Puja Samagri ----------
PUJA_SAMAGRI: Dict[str, List[str]] = {
    "Satyanarayan Katha": ["Kalash with coconut & mango leaves","Panchamrit","Haldi-Kumkum","Rice (Akshat)","Diya & Ghee","Flowers","Fruits & Sweets","Banana leaves","Tulsi leaves","Red cloth"],
    "Griha Pravesh": ["Kalash & Coconut","Mango leaves","Ganga Jal","Turmeric & Kumkum","Rice","Dhoop/Incense","Camphor","Flowers","Havan samagri","Wheat flour (swastik)"],
    "Mundan": ["New blade/razor","Holy water","Cotton","Haldi paste","Flowers","Coconut","Rice","Camphor","Cloth","Mirror (optional)"],
    "Rudra Abhishek": ["Milk","Curd","Honey","Ghee","Sugar","Bilva leaves","Water","Black sesame","Roli & Rice"],
    "Ganesh Puja": ["Ganesh idol/photo","Durva grass","Modak/Laddu","Red cloth","Haldi-Kumkum","Rice","Incense","Camphor","Flowers","Fruits"],
    "Navgrah Shanti": ["Navgrah yantra","Nine grains","Flowers","Multi-color cloth","Til (sesame)","Havan samagri","Ghee","Fruits","Sweets"],
    "Durga Puja": ["Durga idol/photo","Red cloth","Sindoor","Flowers","Fruits","Sweets","Incense","Camphor","Havan samagri","Kalash"],
    "Lakshmi Puja": ["Lakshmi idol/photo","Lotus flowers","Kumkum","Akshat","Coins","Kalash & Coconut","Diya & Ghee","Fruits","Sweets"],
    "Mahamrityunjaya Jaap": ["Shiv yantra","Bilva leaves","Panchamrit","Water","Black sesame","Camphor","Incense","Flowers"],
    "Kaal Sarp Dosh Puja": ["Abhishek dravya","Naag-Nagin idols (optional)","Kalash","Black sesame","Flowers","Havan samagri","Camphor"],
    "Hanuman Puja": ["Hanuman idol/photo","Sindoor","Jasmine oil","Betel leaves","Flowers","Fruits","Sweets","Incense","Camphor"],
    "Sundarkand Path": ["Ramayan/Sundarkand book","Diya & Ghee","Incense","Camphor","Flowers","Fruits","Sweets","Asan (mat)"],
    "Katha & Havan": ["Katha granth","Kalash","Coconut","Havan kund","Havan samagri","Ghee","Camphor","Spoons & Pot","Darbha (Kusha) grass"],
    "Vastu Shanti": ["Navgrah yantra","Havan samagri","Kalash","Coconut","Haldi-Kumkum","Rice","Flowers","Fruits"],
    "Narayan Nagbali": ["Sankalp items","Pind daan samagri","Kusha grass","Black sesame","White clothes","Flowers","Havan samagri"],
    "Saraswati Puja": ["Saraswati idol/photo","White cloth","Books/Instruments","Flowers","Fruits","Sweets","Incense","Camphor"],
    "Chandi Path": ["Chandi text","Kalash","Coconut","Red cloth","Sindoor","Flowers","Fruits","Havan samagri"],
    "Navratri Puja": ["Kalash","Coconut","Red cloth","Akshat","Sindoor","Flowers","Fruits","Nava Dhanya","Diyas"],
    "Sat Chandi Yagya": ["Chandi yantra","Havan kund","Havan samagri (large)","Ghee (extra)","Sruva/wooden spoons","Darbha grass","Fruits","Sweets","Cloths"]
}

# ---------- Extra Puja Instructions ----------
PUJA_INSTRUCTIONS: Dict[str, Dict[str, str]] = {
    "Satyanarayan Katha": {"prep":"Clean puja area; keep kalash ready.","duration":"~1.5–2 hours","dress":"Traditional/ethnic, light colors preferred.","notes":"Family members may keep light fast; distribute prasad to all."},
    "Griha Pravesh": {"prep":"Home must be cleaned; threshold decorated with rangoli.","duration":"~2–3 hours","dress":"Traditional; head covered during sankalp.","notes":"Enter house right foot first while carrying kalash."},
    "Mundan": {"prep":"Child’s hair wetted; razor sterilized.","duration":"~45–60 mins","dress":"Comfortable; towel/cloth handy.","notes":"Do in auspicious muhurat; protect scalp from sun after."},
    "Rudra Abhishek": {"prep":"Abhishek dravya & bilva leaves ready.","duration":"~1–1.5 hours","dress":"Traditional/clean clothes.","notes":"Avoid non-veg & alcohol before/after puja."},
    "Ganesh Puja": {"prep":"Place Ganesh on clean red cloth.","duration":"~60–90 mins","dress":"Traditional.","notes":"Offer 21 durva & modaks if possible."},
    "Navgrah Shanti": {"prep":"Nine grains arranged in yantra.","duration":"~2 hours","dress":"Traditional.","notes":"Pandit will guide on specific graha daan."},
    "Durga Puja": {"prep":"Kalash sthapana; red chunri ready.","duration":"~2–3 hours","dress":"Red/bright shades traditional.","notes":"Kumkum tilak and sindoor offered."},
    "Lakshmi Puja": {"prep":"De-clutter wealth area; place coins.","duration":"~60–90 mins","dress":"Clean/bright traditional.","notes":"Keep account books/locker keys near idol."},
    "Mahamrityunjaya Jaap": {"prep":"Silent & clean environment.","duration":"~1.5–3 hours","dress":"Traditional, simple.","notes":"Best performed on Mondays/Pradosh."},
    "Kaal Sarp Dosh Puja": {"prep":"Sankalp details ready.","duration":"~2 hours","dress":"Traditional (prefer white).","notes":"Follow pandit’s guidance strictly."},
    "Hanuman Puja": {"prep":"Apply sindoor and oil as per vidhi.","duration":"~45–75 mins","dress":"Traditional.","notes":"Chant Hanuman Chalisa collectively."},
    "Sundarkand Path": {"prep":"Arrange path copies for participants.","duration":"~2–3 hours","dress":"Traditional.","notes":"Light snacks & water for participants."},
    "Katha & Havan": {"prep":"Open ventilated area for havan.","duration":"~1.5–2 hours","dress":"Traditional; cotton preferred.","notes":"Keep water & fire safety in place."},
    "Vastu Shanti": {"prep":"House map & owner details handy.","duration":"~2 hours","dress":"Traditional.","notes":"Ideal before/after renovation or shifting."},
    "Narayan Nagbali": {"prep":"Special sankalp; consult pandit.","duration":"~1–2 days (elaborate)","dress":"White traditional.","notes":"Typically at specified tirtha; local simplified version possible."},
    "Saraswati Puja": {"prep":"Keep books/instruments near idol.","duration":"~60–90 mins","dress":"White/yellow traditional.","notes":"Good day for students to start studies."},
    "Chandi Path": {"prep":"Quiet place; text copies arranged.","duration":"~2–3 hours","dress":"Traditional.","notes":"Can be done with homa as per need."},
    "Navratri Puja": {"prep":"Kalash sthapana day 1.","duration":"Daily ~45–60 mins","dress":"Traditional.","notes":"Observe simple satvik diet."},
    "Sat Chandi Yagya": {"prep":"Large havan setup.","duration":"~4–6 hours","dress":"Traditional.","notes":"Requires extended samagri & arrangements."}
}

# ---------- Pandit model (with weekday availability) ----------
@dataclass
class Pandit:
    id: int
    name: str
    specializations: List[str]
    base_fee: int
    city: str
    languages: List[str]
    rating: float
    experience_years: int
    service_mode: str
    phone: str
    time_windows: List[Tuple[str,str,str]]  # (label, start, end)
    days: List[str]  # e.g., ["Mon","Wed","Fri"]

def fee_for(i:int)->int:
    return [500,600,700,800,900,1000][(i-1)%6]
DAY_CYCLES = [
    ["Mon","Wed","Fri"],
    ["Tue","Thu","Sat"],
    ["Sat","Sun"],
    ["Mon","Tue","Thu"],
    ["Wed","Fri","Sun"],
    ["Mon","Sat"],
]

# ---------- 100 Hardcoded Pandits ----------
PANDITS: List[Pandit] = [
    Pandit(1,"Pandit Chatterjee 1",["Satyanarayan Katha","Lakshmi Puja","Vastu Shanti"],900,"Kolkata",
           ["Sanskrit","Hindi","Bengali"],4.7,14,"onsite","+919812300001",
           [("morning","08:30","10:30"),("evening","17:30","19:30")], DAY_CYCLES[0]),
    Pandit(2,"Pandit Mukherjee 2",["Durga Puja","Chandi Path","Navratri Puja"],800,"Howrah",
           ["Hindi","English","Bengali"],4.6,12,"either","+919812300002",
           [("afternoon","12:30","14:30"),("evening","18:00","20:00")], DAY_CYCLES[1]),
    Pandit(3,"Pandit Banerjee 3",["Rudra Abhishek","Mahamrityunjaya Jaap","Ganesh Puja"],700,"Siliguri",
           ["Sanskrit","Hindi","English"],4.5,9,"online","+919812300003",
           [("morning","09:00","11:00")], DAY_CYCLES[2]),
    Pandit(4,"Pandit Sarkar 4",["Griha Pravesh","Vastu Shanti","Lakshmi Puja"],600,"Durgapur",
           ["Hindi","Bengali"],4.4,8,"onsite","+919812300004",
           [("afternoon","13:00","15:00"),("evening","17:30","19:00")], DAY_CYCLES[3]),
    Pandit(5,"Pandit Ghosh 5",["Hanuman Puja","Sundarkand Path","Katha & Havan"],1000,"Asansol",
           ["Sanskrit","Bengali"],4.8,18,"either","+919812300005",
           [("evening","17:00","20:00")], DAY_CYCLES[4]),
    Pandit(6,"Pandit Bhattacharya 6",["Satyanarayan Katha","Ganesh Puja","Lakshmi Puja"],500,"Kharagpur",
           ["Hindi","English","Bengali"],4.3,7,"onsite","+919812300006",
           [("morning","08:30","10:30"),("afternoon","12:00","14:00")], DAY_CYCLES[5]),
    Pandit(7,"Pandit Das 7",["Navgrah Shanti","Kaal Sarp Dosh Puja","Rudra Abhishek"],900,"Bardhaman",
           ["Sanskrit","Hindi","Bengali"],4.6,11,"either","+919812300007",
           [("afternoon","12:00","16:00")], DAY_CYCLES[0]),
    Pandit(8,"Pandit Saha 8",["Lakshmi Puja","Saraswati Puja","Chandi Path"],800,"Haldia",
           ["Hindi","Bengali"],4.5,10,"online","+919812300008",
           [("morning","09:00","10:30"),("evening","18:00","19:30")], DAY_CYCLES[1]),
    Pandit(9,"Pandit Sharma 9",["Vastu Shanti","Griha Pravesh","Katha & Havan"],700,"Kalyani",
           ["Sanskrit","Hindi","English"],4.2,6,"onsite","+919812300009",
           [("afternoon","12:30","14:30")], DAY_CYCLES[2]),
    Pandit(10,"Pandit Chatterjee 10",["Durga Puja","Navratri Puja","Chandi Path"],1000,"Bidhannagar",
           ["Hindi","Bengali"],4.7,15,"either","+919812300010",
           [("evening","17:00","20:00")], DAY_CYCLES[3]),
    Pandit(11,"Pandit Mukherjee 11",["Sat Chandi Yagya","Durga Puja","Lakshmi Puja"],1000,"Salt Lake",
           ["Sanskrit","Bengali"],4.8,20,"onsite","+919812300011",
           [("morning","08:00","10:00")], DAY_CYCLES[4]),
    Pandit(12,"Pandit Banerjee 12",["Ganesh Puja","Satyanarayan Katha","Saraswati Puja"],600,"Hooghly",
           ["Hindi","English","Bengali"],4.4,9,"either","+919812300012",
           [("afternoon","12:00","15:00")], DAY_CYCLES[5]),
    Pandit(13,"Pandit Sarkar 13",["Hanuman Puja","Sundarkand Path","Mahamrityunjaya Jaap"],700,"Behala",
           ["Sanskrit","Hindi","Bengali"],4.6,13,"onsite","+919812300013",
           [("evening","17:30","19:30")], DAY_CYCLES[0]),
    Pandit(14,"Pandit Ghosh 14",["Kaal Sarp Dosh Puja","Navgrah Shanti","Rudra Abhishek"],600,"Barasat",
           ["Hindi","Bengali"],4.5,10,"online","+919812300014",
           [("morning","09:00","11:00")], DAY_CYCLES[1]),
    Pandit(15,"Pandit Bhattacharya 15",["Vastu Shanti","Griha Pravesh","Katha & Havan"],500,"Bally",
           ["Sanskrit","Hindi","English"],4.3,7,"onsite","+919812300015",
           [("afternoon","12:30","14:30"),("evening","18:00","19:30")], DAY_CYCLES[2]),
    Pandit(16,"Pandit Das 16",["Saraswati Puja","Lakshmi Puja","Satyanarayan Katha"],900,"Serampore",
           ["Hindi","English","Bengali"],4.7,16,"either","+919812300016",
           [("morning","08:30","10:30")], DAY_CYCLES[3]),
    Pandit(17,"Pandit Saha 17",["Chandi Path","Navratri Puja","Durga Puja"],700,"Krishnanagar",
           ["Sanskrit","Bengali"],4.4,8,"online","+919812300017",
           [("evening","17:00","19:00")], DAY_CYCLES[4]),
    Pandit(18,"Pandit Sharma 18",["Ganesh Puja","Rudra Abhishek","Mahamrityunjaya Jaap"],600,"Siliguri",
           ["Hindi","English","Bengali"],4.2,6,"onsite","+919812300018",
           [("afternoon","12:00","15:00")], DAY_CYCLES[5]),
    Pandit(19,"Pandit Chatterjee 19",["Satyanarayan Katha","Lakshmi Puja","Vastu Shanti"],1000,"Kolkata",
           ["Sanskrit","Hindi","Bengali"],4.9,21,"either","+919812300019",
           [("morning","08:00","10:00"),("evening","18:00","19:30")], DAY_CYCLES[0]),
    Pandit(20,"Pandit Mukherjee 20",["Griha Pravesh","Vastu Shanti","Katha & Havan"],800,"Howrah",
           ["Hindi","English","Bengali"],4.5,11,"onsite","+919812300020",
           [("afternoon","13:00","15:00")], DAY_CYCLES[1]),
]

EXTRA = [
    (21, "Purulia", ["Rudra Abhishek","Ganesh Puja","Navgrah Shanti"]),
    (22, "Midnapore", ["Durga Puja","Lakshmi Puja","Mahamrityunjaya Jaap"]),
    (23, "Kolkata", ["Kaal Sarp Dosh Puja","Hanuman Puja","Sundarkand Path"]),
    (24, "Howrah", ["Katha & Havan","Vastu Shanti","Narayan Nagbali"]),
    (25, "Siliguri", ["Saraswati Puja","Chandi Path","Navratri Puja"]),
    (26, "Durgapur", ["Sat Chandi Yagya","Satyanarayan Katha","Griha Pravesh"]),
    (27, "Asansol", ["Mundan","Rudra Abhishek","Ganesh Puja"]),
    (28, "Kharagpur", ["Navgrah Shanti","Durga Puja","Lakshmi Puja"]),
    (29, "Bardhaman", ["Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja","Hanuman Puja"]),
    (30, "Haldia", ["Sundarkand Path","Katha & Havan","Vastu Shanti"]),
    (31, "Kalyani", ["Narayan Nagbali","Saraswati Puja","Chandi Path"]),
    (32, "Bidhannagar", ["Navratri Puja","Sat Chandi Yagya","Satyanarayan Katha"]),
    (33, "Salt Lake", ["Griha Pravesh","Mundan","Rudra Abhishek"]),
    (34, "Hooghly", ["Ganesh Puja","Navgrah Shanti","Durga Puja"]),
    (35, "Behala", ["Lakshmi Puja","Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja"]),
    (36, "Barasat", ["Hanuman Puja","Sundarkand Path","Katha & Havan"]),
    (37, "Bally", ["Vastu Shanti","Narayan Nagbali","Saraswati Puja"]),
    (38, "Serampore", ["Chandi Path","Navratri Puja","Sat Chandi Yagya"]),
    (39, "Krishnanagar", ["Satyanarayan Katha","Griha Pravesh","Mundan"]),
    (40, "Jalpaiguri", ["Rudra Abhishek","Ganesh Puja","Navgrah Shanti"]),
    (41, "Malda", ["Durga Puja","Lakshmi Puja","Mahamrityunjaya Jaap"]),
    (42, "Murshidabad", ["Kaal Sarp Dosh Puja","Hanuman Puja","Sundarkand Path"]),
    (43, "Bankura", ["Katha & Havan","Vastu Shanti","Narayan Nagbali"]),
    (44, "Purulia", ["Saraswati Puja","Chandi Path","Navratri Puja"]),
    (45, "Midnapore", ["Sat Chandi Yagya","Satyanarayan Katha","Griha Pravesh"]),
    (46, "Kolkata", ["Mundan","Rudra Abhishek","Ganesh Puja"]),
    (47, "Howrah", ["Navgrah Shanti","Durga Puja","Lakshmi Puja"]),
    (48, "Siliguri", ["Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja","Hanuman Puja"]),
    (49, "Durgapur", ["Sundarkand Path","Katha & Havan","Vastu Shanti"]),
    (50, "Asansol", ["Narayan Nagbali","Saraswati Puja","Chandi Path"]),
    (51, "Kharagpur", ["Satyanarayan Katha","Lakshmi Puja","Vastu Shanti"]),
    (52, "Bardhaman", ["Durga Puja","Chandi Path","Navratri Puja"]),
    (53, "Haldia", ["Rudra Abhishek","Mahamrityunjaya Jaap","Ganesh Puja"]),
    (54, "Kalyani", ["Griha Pravesh","Vastu Shanti","Lakshmi Puja"]),
    (55, "Bidhannagar", ["Hanuman Puja","Sundarkand Path","Katha & Havan"]),
    (56, "Salt Lake", ["Kaal Sarp Dosh Puja","Navgrah Shanti","Rudra Abhishek"]),
    (57, "Hooghly", ["Saraswati Puja","Lakshmi Puja","Satyanarayan Katha"]),
    (58, "Behala", ["Navratri Puja","Durga Puja","Chandi Path"]),
    (59, "Barasat", ["Mundan","Griha Pravesh","Vastu Shanti"]),
    (60, "Bally", ["Ganesh Puja","Navgrah Shanti","Rudra Abhishek"]),
    (61, "Serampore", ["Sat Chandi Yagya","Chandi Path","Navratri Puja"]),
    (62, "Krishnanagar", ["Sundarkand Path","Katha & Havan","Vastu Shanti"]),
    (63, "Jalpaiguri", ["Narayan Nagbali","Saraswati Puja","Chandi Path"]),
    (64, "Malda", ["Satyanarayan Katha","Griha Pravesh","Mundan"]),
    (65, "Murshidabad", ["Rudra Abhishek","Ganesh Puja","Navgrah Shanti"]),
    (66, "Bankura", ["Durga Puja","Lakshmi Puja","Mahamrityunjaya Jaap"]),
    (67, "Purulia", ["Kaal Sarp Dosh Puja","Hanuman Puja","Sundarkand Path"]),
    (68, "Midnapore", ["Katha & Havan","Vastu Shanti","Narayan Nagbali"]),
    (69, "Kolkata", ["Saraswati Puja","Chandi Path","Navratri Puja"]),
    (70, "Howrah", ["Sat Chandi Yagya","Satyanarayan Katha","Griha Pravesh"]),
    (71, "Siliguri", ["Mundan","Rudra Abhishek","Ganesh Puja"]),
    (72, "Durgapur", ["Navgrah Shanti","Durga Puja","Lakshmi Puja"]),
    (73, "Asansol", ["Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja","Hanuman Puja"]),
    (74, "Kharagpur", ["Sundarkand Path","Katha & Havan","Vastu Shanti"]),
    (75, "Bardhaman", ["Narayan Nagbali","Saraswati Puja","Chandi Path"]),
    (76, "Haldia", ["Navratri Puja","Sat Chandi Yagya","Satyanarayan Katha"]),
    (77, "Kalyani", ["Griha Pravesh","Mundan","Rudra Abhishek"]),
    (78, "Bidhannagar", ["Ganesh Puja","Navgrah Shanti","Durga Puja"]),
    (79, "Salt Lake", ["Lakshmi Puja","Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja"]),
    (80, "Hooghly", ["Hanuman Puja","Sundarkand Path","Katha & Havan"]),
    (81, "Behala", ["Vastu Shanti","Narayan Nagbali","Saraswati Puja"]),
    (82, "Barasat", ["Chandi Path","Navratri Puja","Sat Chandi Yagya"]),
    (83, "Bally", ["Satyanarayan Katha","Griha Pravesh","Mundan"]),
    (84, "Serampore", ["Rudra Abhishek","Ganesh Puja","Navgrah Shanti"]),
    (85, "Krishnanagar", ["Durga Puja","Lakshmi Puja","Mahamrityunjaya Jaap"]),
    (86, "Jalpaiguri", ["Kaal Sarp Dosh Puja","Hanuman Puja","Sundarkand Path"]),
    (87, "Malda", ["Katha & Havan","Vastu Shanti","Narayan Nagbali"]),
    (88, "Murshidabad", ["Saraswati Puja","Chandi Path","Navratri Puja"]),
    (89, "Bankura", ["Sat Chandi Yagya","Satyanarayan Katha","Griha Pravesh"]),
    (90, "Purulia", ["Mundan","Rudra Abhishek","Ganesh Puja"]),
    (91, "Midnapore", ["Navgrah Shanti","Durga Puja","Lakshmi Puja"]),
    (92, "Kolkata", ["Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja","Hanuman Puja"]),
    (93, "Howrah", ["Sundarkand Path","Katha & Havan","Vastu Shanti"]),
    (94, "Siliguri", ["Narayan Nagbali","Saraswati Puja","Chandi Path"]),
    (95, "Durgapur", ["Navratri Puja","Sat Chandi Yagya","Satyanarayan Katha"]),
    (96, "Asansol", ["Griha Pravesh","Mundan","Rudra Abhishek"]),
    (97, "Kharagpur", ["Ganesh Puja","Navgrah Shanti","Durga Puja"]),
    (98, "Bardhaman", ["Lakshmi Puja","Mahamrityunjaya Jaap","Kaal Sarp Dosh Puja"]),
    (99, "Haldia", ["Hanuman Puja","Sundarkand Path","Katha & Havan"]),
    (100,"Kalyani", ["Vastu Shanti","Narayan Nagbali","Saraswati Puja"]),
]

# Build 21..100 entries
for pid, city, specs in EXTRA:
    PANDITS.append(
        Pandit(
            pid,
            f"Pandit {city} {pid}",
            specs,
            fee_for(pid),
            city,
            ["Hindi","Bengali"] if city not in ["Siliguri","Kolkata","Bidhannagar","Salt Lake","Kalyani"] else ["Hindi","English","Bengali"],
            4.0 + ((pid % 10) / 10.0),              # 4.0 .. 4.9
            4 + (pid % 10),                         # 4..13 yrs
            "either" if pid % 5 in (0,2) else ("online" if pid % 3 == 0 else "onsite"),
            f"+9198123000{pid:02d}",
            [("morning","08:00","10:00")] if pid % 2 else [("afternoon","12:00","14:30"),("evening","17:30","19:00")],
            DAY_CYCLES[(pid-1) % len(DAY_CYCLES)]
        )
    )

# ---------- City Coordinates ----------
CITY_COORDS = {
    "Kolkata": (22.5726, 88.3639),    "Howrah": (22.5958, 88.2636),
    "Siliguri": (26.7271, 88.3953),   "Durgapur": (23.5204, 87.3119),
    "Asansol": (23.6739, 86.9524),    "Kharagpur": (22.3460, 87.2319),
    "Bardhaman": (23.2324, 87.8615),  "Haldia": (22.0667, 88.0698),
    "Kalyani": (22.9868, 88.4345),    "Bidhannagar": (22.5726, 88.4333),
    "Salt Lake": (22.6070, 88.4273),  "Hooghly": (22.9089, 88.3966),
    "Behala": (22.5010, 88.2950),     "Barasat": (22.7229, 88.4800),
    "Bally": (22.6500, 88.3400),      "Serampore": (22.7528, 88.3426),
    "Krishnanagar": (23.4058, 88.4900),"Jalpaiguri": (26.5435, 88.7200),
    "Malda": (25.0108, 88.1411),      "Murshidabad": (24.1750, 88.2800),
    "Bankura": (23.2324, 87.0750),    "Purulia": (23.3300, 86.3650),
    "Midnapore": (22.4300, 87.3200),
}

# ---------- Time Windows & parsing ----------
WINDOW_MAP = {
    "morning": (dtime(8,0), dtime(11,0)),
    "afternoon": (dtime(12,0), dtime(16,0)),
    "evening": (dtime(17,0), dtime(20,0)),
    "night": (dtime(20,0), dtime(22,0))
}
WINDOW_ALIASES = {
    "morning": ["morning","subah","early","am"],
    "afternoon": ["afternoon","dopahar"],
    "evening": ["evening","shaam","eve","pm"],
    "night": ["night","raat","late night"]
}
def _to_minutes(hhmm: str) -> int:
    hh, mm = map(int, hhmm.split(":")); return hh*60 + mm

def detect_window_and_time(text: str) -> Tuple[Optional[str], Optional[int]]:
    t = text.lower()
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t)
    if m:
        hh = int(m.group(1)); mm = int(m.group(2) or 0); mer = m.group(3)
        if mer:
            if mer.lower()=="pm" and hh<12: hh+=12
            if mer.lower()=="am" and hh==12: hh=0
        user_mins = hh*60 + mm
        best_label, best_delta = None, 10**9
        for label,(s,e) in WINDOW_MAP.items():
            mid = ((s.hour*60 + s.minute) + (e.hour*60 + e.minute))//2
            d = abs(user_mins - mid)
            if d < best_delta: best_label, best_delta = label, d
        return best_label, user_mins
    for label, aliases in WINDOW_ALIASES.items():
        for a in aliases:
            if re.search(rf"\b{re.escape(a)}\b", t):
                return label, None
    return None, None

# ---------- Date Parsing (IST; robust weekdays) ----------
WEEKDAY_IDX = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,"friday":4,"saturday":5,"sunday":6}
WEEKDAY_TOKEN = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
def _next_weekday(base_d: date, idx: int)->date:
    delta=(idx-base_d.weekday())%7
    if delta==0: delta=7
    return base_d+timedelta(days=delta)
def _this_or_next_weekday(base_d: date, idx: int)->date:
    delta=(idx-base_d.weekday())%7
    if delta==0: delta=7
    return base_d+timedelta(days=delta)

def parse_date(text: str) -> Optional[date]:
    t = text.lower().strip()
    base_dt = datetime.now(IST); base_d = base_dt.date()
    if re.search(r"\bday after tomorrow\b", t): return base_d+timedelta(days=2)
    if re.search(r"\btomorrow\b", t): return base_d+timedelta(days=1)
    if re.search(r"\btoday\b", t): return base_d
    m = re.search(r"\b(next|this|coming)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", t)
    if m:
        qual, wd = m.group(1), m.group(2); idx=WEEKDAY_IDX[wd]
        if qual=="next": return _next_weekday(base_d, idx)+timedelta(days=7)
        else: return _this_or_next_weekday(base_d, idx)
    m2 = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", t)
    if m2: return _next_weekday(base_d, WEEKDAY_IDX[m2.group(1)])
    dp = dateparser.parse(text, settings={
        "RELATIVE_BASE": base_dt, "PREFER_DATES_FROM":"future", "TIMEZONE": TZ,
        "RETURN_AS_TIMEZONE_AWARE": False, "PREFER_DAY_OF_MONTH":"first"
    }, languages=["en","hi"])
    if dp:
        d = dp.date()
        return d if d>=base_d else _next_weekday(base_d, base_d.weekday())
    return None

# ---------- Fuzzy puja + city ----------
def fuzzy_match_puja(text: str)->Tuple[str,float]:
    best, score, _ = process.extractOne(text, PUJA_CATALOG, scorer=fuzz.WRatio)
    return best, score/100.0

CITY_SYNONYMS = {"saltlake":"Salt Lake","salt lake":"Salt Lake","bidhannagar":"Bidhannagar"}
ALL_CITIES = sorted({p.city for p in PANDITS})
def normalize_city_maybe(name: Optional[str]) -> Optional[str]:
    if not name: return None
    s = name.strip().lower()
    if s in CITY_SYNONYMS: return CITY_SYNONYMS[s]
    for c in ALL_CITIES:
        if c.lower()==s: return c
    t = name.lower()
    best_city, best_score = None, 0
    for c in ALL_CITIES:
        score = fuzz.partial_ratio(c.lower(), t)
        if score>best_score: best_city, best_score = c, score
    return best_city if best_score>=80 else None

def detect_city(user_text: str)->Optional[str]:
    for c in ALL_CITIES:
        if c.lower() in user_text.lower():
            return c
    return normalize_city_maybe(user_text)

# ---------- Distance ----------
def haversine_km(a: str, b: str) -> float:
    if a not in CITY_COORDS or b not in CITY_COORDS: return 9999.0
    lat1, lon1 = CITY_COORDS[a]; lat2, lon2 = CITY_COORDS[b]
    r=6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1); dl = math.radians(lon2-lon1)
    h = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2*r*math.asin(min(1, math.sqrt(h)))

def proximity_tier_km(dist: float) -> int:
    if dist==0: return 0
    if dist<=30: return 1
    if dist<=80: return 2
    return 3

# ---------- Request Schema ----------
class PujaRequest(BaseModel):
    puja_type: Optional[str] = Field(None)
    when_date: Optional[date] = Field(None)
    time_window: Optional[Literal["morning","afternoon","evening","night"]] = Field(None)
    time_specific_mins: Optional[int] = Field(None)
    city: Optional[str] = Field(None)
    budget_inr: Optional[int] = Field(None)
    language_pref: Optional[List[str]] = Field(default=None)
    notes: Optional[str] = None

def rule_based_extract(user_text: str):
    conf={}
    puja_guess, puja_conf = fuzzy_match_puja(user_text); conf["puja_type"]=puja_conf
    d = parse_date(user_text); conf["when_date"]=0.9 if d else 0.0
    w, tmins = detect_window_and_time(user_text); conf["time_window"]=0.9 if w else 0.0
    city = detect_city(user_text); conf["city"]=0.9 if city else 0.2
    budget=None
    m = re.search(r"(?:budget|under|upto|up to|around|~)\s*₹?\s*([0-9]{3,7})", user_text.lower())
    if not m: m = re.search(r"₹\s*([0-9]{3,7})", user_text)
    if m: budget=int(m.group(1))
    conf["budget_inr"]=0.9 if budget else 0.0
    langs=[]
    for L in ["Sanskrit","Hindi","English","Bengali"]:
        if re.search(rf"\b{L.lower()}\b", user_text.lower()):
            langs.append(L)
    conf["language_pref"]=0.8 if langs else 0.2
    req = PujaRequest(puja_type=puja_guess, when_date=d, time_window=w, time_specific_mins=tmins,
                      city=city, budget_inr=budget, language_pref=langs or None)
    return req, conf

def llm_extract(user_text: str):
    prompt = f"""
Extract structured booking info from Hinglish. Use only these puja types: {PUJA_CATALOG}.
Return STRICT JSON with:
puja_type, when_date (YYYY-MM-DD or null),
time_window (morning/afternoon/evening/night or null),
time_specific_mins (int minutes from midnight or null),
city, budget_inr, language_pref (subset of ["Sanskrit","Hindi","English","Bengali"]), notes, conf (0..1 map).
If a specific time like "5:30 pm" is given, compute minutes from midnight accordingly.
User: {user_text}
"""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini", temperature=0,
            messages=[{"role":"system","content":"Return STRICT JSON only, no prose."},
                      {"role":"user","content":prompt}]
        )
        txt = resp.choices[0].message.content.strip()
        data = json.loads(txt)
        d = date.fromisoformat(data["when_date"]) if data.get("when_date") else None
        req = PujaRequest(
            puja_type=data.get("puja_type"),
            when_date=d,
            time_window=data.get("time_window"),
            time_specific_mins=data.get("time_specific_mins"),
            city=normalize_city_maybe(data.get("city")),
            budget_inr=data.get("budget_inr"),
            language_pref=data.get("language_pref"),
            notes=data.get("notes")
        )
        conf = data.get("conf", {})
        if req.puja_type and req.puja_type not in PUJA_CATALOG:
            best, sc = fuzzy_match_puja(req.puja_type)
            req.puja_type, conf["puja_type"] = best, max(conf.get("puja_type",0), sc)
        if not req.city:
            req.city = normalize_city_maybe(user_text)
        return req, conf
    except Exception:
        return rule_based_extract(user_text)

# ---------- Allocation (Specialization → Proximity → Time → Weekday → Budget/Ratings/Exp) ----------
REQUIRE_TIME_STRICT = True

def has_window(p: Pandit, label: str)->bool:
    return any(w[0]==label for w in p.time_windows)

def time_distance_minutes(p: Pandit, label: Optional[str], specific_mins: Optional[int]) -> int:
    if not label: return 0
    if specific_mins is None: return 0
    w = next((w for w in p.time_windows if w[0]==label), None)
    if not w: return 10_000
    mid = (_to_minutes(w[1])+_to_minutes(w[2]))//2
    return abs(mid-specific_mins)

def _samagri_md(puja_type: Optional[str]) -> str:
    if not puja_type:
        return "> 📦 Puja samagri will appear here once we detect your puja type."
    items = PUJA_SAMAGRI.get(puja_type, [])
    title = f"### 📦 Puja Samagri for **{puja_type}**"
    if not items:
        return f"{title}\n_(No preset list found; pandit will share a checklist on confirmation.)_"
    return f"{title}\n" + "\n".join([f"- {x}" for x in items])

def _instructions_md(puja_type: Optional[str]) -> str:
    if not puja_type: return "> 📋 Puja instructions will appear after we detect the puja type."
    info = PUJA_INSTRUCTIONS.get(puja_type)
    if not info:
        return f"### 📋 Instructions for **{puja_type}**\n_(Pandit will brief you on custom vidhi.)_"
    return (
        f"### 📋 Instructions for **{puja_type}**\n"
        f"- **Preparation:** {info['prep']}\n"
        f"- **Duration:** {info['duration']}\n"
        f"- **Dress code:** {info['dress']}\n"
        f"- **Notes:** {info['notes']}"
    )

def perform_search(user_text: str, forced_time: Optional[str]=None):
    try: req, _ = llm_extract(user_text)
    except Exception: req, _ = rule_based_extract(user_text)

    samagri_md = _samagri_md(req.puja_type)
    guide_md = _instructions_md(req.puja_type)

    if (not req.time_window) and (not forced_time):
        parsed = {"puja_type":req.puja_type,"when_date":str(req.when_date) if req.when_date else None,
                  "time_window":None,"city":req.city or "(WB city assumed later)","budget_inr":req.budget_inr}
        status = "⏰ Please select a time window (morning / afternoon / evening / night) to continue."
        return (status, json.dumps(parsed, indent=2), "(no results)", "",
                gr.update(choices=[], value=None), "", gr.update(visible=True), gr.update(visible=True),
                samagri_md, guide_md)

    if forced_time: req.time_window = forced_time
    if not req.city: req.city = "Kolkata"

    weekday_token = None
    if req.when_date:
        weekday_token = WEEKDAY_TOKEN[req.when_date.weekday()]  # "Mon".."Sun"

    candidates: List[Tuple[Pandit,int,int,float]] = []  # (pandit, tier, tdist, dist_km)
    for p in PANDITS:
        if req.puja_type and (req.puja_type not in p.specializations): continue
        if REQUIRE_TIME_STRICT and req.time_window and (not has_window(p, req.time_window)): continue
        if weekday_token and (weekday_token not in p.days): continue
        dist = 0.0 if p.city==req.city else haversine_km(req.city, p.city)
        tier = 0 if p.city==req.city else proximity_tier_km(dist)
        tdist = time_distance_minutes(p, req.time_window, req.time_specific_mins)
        candidates.append((p, tier, tdist, dist))

    if not candidates:
        status = f"❌ No options for **{req.puja_type}** in **{req.city}** ({req.time_window or 'N/A'})" + (f" on **{weekday_token}**" if weekday_token else "")
        parsed = {"puja_type":req.puja_type,"when_date":str(req.when_date) if req.when_date else None,
                  "time_window":req.time_window,"city":req.city,"budget_inr":req.budget_inr}
        return (status, json.dumps(parsed, indent=2), "No matches.", "",
                gr.update(choices=[], value=None), "", gr.update(visible=True), gr.update(visible=True),
                samagri_md, guide_md)

    # Sort: proximity tier → distance → time Δ → |budget gap| → rating desc → exp desc → fee asc
    user_budget = req.budget_inr
    def _key(t):
        p, tier, tdist, dist = t
        gap = abs((p.base_fee - (user_budget or p.base_fee)))
        return (tier, dist, tdist, gap, -p.rating, -p.experience_years, p.base_fee)
    ranked = sorted(candidates, key=_key)

    headers = ["ID","Name","City","Mode","Windows","Days","Fee","★","Exp","Dist(km)","Tier","TimeΔ"]
    rows, opts, exps = [], [], []
    for (p, tier, tdist, dist) in ranked[:12]:
        rows.append([p.id, p.name, p.city, p.service_mode,
                     "; ".join([f"{w[0]} {w[1]}-{w[2]}" for w in p.time_windows]),
                     ",".join(p.days), f"₹{p.base_fee}", p.rating, p.experience_years, f"{dist:.1f}", tier, tdist])
        opts.append(str(p.id))
        exps.append(f"• {p.name}: {p.city}, {','.join(p.days)}, tier {tier}, {dist:.1f} km, Δ {tdist} min, ₹{p.base_fee}, {p.rating}★.")

    table_md = "| " + " | ".join(headers) + " |\n" + "| " + " | ".join(["---"]*len(headers)) + " |\n"
    for r in rows: table_md += "| " + " | ".join(map(str, r)) + " |\n"

    parsed = {"puja_type":req.puja_type,"when_date":str(req.when_date) if req.when_date else None,
              "time_window":req.time_window,"city":req.city,"budget_inr":req.budget_inr}
    selection_update = gr.update(choices=opts, value=(opts[0] if opts else None))
    status = "✅ Ranked by specialization → proximity → time → weekday availability → budget/ratings/experience."
    explanations = "\n".join(exps[:6])

    state_payload = {
        "req": parsed,
        "ranked": [
            {"id": p.id, "name": p.name, "fee": p.base_fee, "phone": p.phone, "city": p.city,
             "windows": p.time_windows, "rating": p.rating, "langs": p.languages, "mode": p.service_mode}
            for (p, _, _, _) in ranked[:12]
        ]
    }
    hidden_state = json.dumps(state_payload)

    return (status, json.dumps(parsed, indent=2), table_md, explanations, selection_update, hidden_state,
            gr.update(visible=False), gr.update(visible=False), samagri_md, guide_md)

# ---------- Voice (STT) ----------
TRANSCRIBE_MODELS = ["gpt-4o-transcribe", "whisper-1"]
def _extract_text_from_transcribe(resp) -> str:
    if isinstance(resp, str): return resp.strip()
    for attr in ("text","output_text","transcript","result"):
        if hasattr(resp, attr):
            v = getattr(resp, attr)
            if isinstance(v, str): return v.strip()
    try:
        d = resp.to_dict() if hasattr(resp,"to_dict") else (resp.model_dump() if hasattr(resp,"model_dump") else None)
        if d:
            for k in ("text","output_text","transcript","result"):
                if k in d and isinstance(d[k], str): return d[k].strip()
    except Exception: pass
    return ""

def transcribe_audio(filepath: str) -> str:
    if not filepath: return ""
    for model in TRANSCRIBE_MODELS:
        try:
            with open(filepath, "rb") as f:
                resp = openai_client.audio.transcriptions.create(
                    model=model, file=f, response_format="text", temperature=0
                )
            txt = _extract_text_from_transcribe(resp)
            if txt: return txt
        except Exception: continue
    return ""

def voice_find(audio_path: str):
    transcript = transcribe_audio(audio_path)
    if not transcript or len(transcript.strip())<3:
        msg = "🎙️ Please re-record clearly with puja, city and time (e.g., 'Satyanarayan Katha in Howrah, evening next Monday')."
        return (msg, "{}", "(no results)", "",
                gr.update(choices=[], value=None), "", gr.update(visible=False), gr.update(visible=False),
                _samagri_md(None), "> 📋 Puja instructions will appear after we detect the puja type.")
    status, parsed_json, table_md, explanations, selection_update, hidden_state, time_dd_vis, time_btn_vis, samagri_md, guide_md = \
        perform_search(transcript, forced_time=None)
    return (status, parsed_json, table_md, explanations, selection_update, hidden_state, time_dd_vis, time_btn_vis, samagri_md, guide_md)

# ---------- Confirm booking ----------
def confirm_booking(selected_id, payment_method, state_json):
    if not state_json: return "Please search options first.", ""
    try: state = json.loads(state_json)
    except Exception: return "Internal state decode error. Please try again.", ""
    ranked = state.get("ranked", [])
    if not ranked: return "No options to confirm. Please search again.", ""
    if not selected_id: return "Select a Pandit ID first.", ""
    chosen = next((r for r in ranked if str(r["id"])==str(selected_id)), None)
    if not chosen: return "Selected ID not in current options. Please pick again.", ""
    if payment_method.lower() not in {"upi","netbanking","cash"}:
        return "Choose payment method (UPI / NetBanking / Cash).", ""
    req = state.get("req", {})
    when_text = req.get("when_date") or "your chosen date"
    tw = req.get("time_window") or "your time window"
    puja = req.get("puja_type") or "Requested Puja"
    pay_msg = f"Payment method: {payment_method.upper()}."
    if payment_method.lower() in {"upi","netbanking"}:
        pay_msg += " (Demo: payment link assumed successful ✅)"
    confirm = (
        f"🎉 Appointment confirmed for **{puja}** on **{when_text}**, **{tw}** window.\n"
        f"👨‍🦳 Pandit: **{chosen['name']}** — Phone: **{chosen['phone']}**\n"
        f"City: {chosen['city']} • Fee: ₹{chosen['fee']}\n\n{pay_msg}"
    )
    return "✅ Booking Confirmed!", confirm

# ---------- UI ----------
def toggle_mode(mode):
    show_text = (mode == "Text"); show_voice = (mode == "Voice")
    return (gr.update(visible=show_text), gr.update(visible=show_voice))

def text_find_wrapper(txt):
    return (*perform_search(txt, forced_time=None),)

def set_time_wrapper(txt, picked):
    if picked:
        return (*perform_search(txt, forced_time=picked),)
    else:
        return ("⏰ Please pick a time window from the dropdown.", "{}", "> Waiting for time selection…", "",
                gr.update(choices=[], value=None), "", gr.update(visible=True), gr.update(visible=True),
                _samagri_md(None), "> 📋 Puja instructions will appear after we detect the puja type.")

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("## 🕉️ Puja Booking (West Bengal)\nSpecialization + Proximity + Time + Day availability. Text & Voice supported.")

    mode = gr.Radio(choices=["Text","Voice"], value="Text", label="Choose input mode")

    text_row = gr.Row(visible=True)
    with text_row:
        user_text = gr.Textbox(label="Your Message",
            placeholder="E.g., Satyanarayan Katha in Howrah, next Monday evening, budget 900.",
            lines=3)
        find_btn = gr.Button("🔎 Find Options")

    voice_row = gr.Row(visible=False)
    with voice_row:
        mic = gr.Audio(sources=["microphone"], type="filepath", label="Speak your request")
        voice_btn = gr.Button("🎤 Transcribe & Find")

    status = gr.Markdown("")
    with gr.Row():
        time_selector = gr.Dropdown(choices=["morning","afternoon","evening","night"],
                                    label="Select Time Window", visible=False)
        set_time_btn = gr.Button("⏱️ Use Selected Time", visible=False)
    parsed_box = gr.Code(label="🧠 Parsed Request (JSON)", interactive=False)
    table_md = gr.Markdown(value="(Matching options will appear here)")
    explanations = gr.Markdown(value="")
    samagri_md = gr.Markdown(value="> 📦 Puja samagri will appear here once we detect your puja type.")
    guide_md = gr.Markdown(value="> 📋 Puja instructions will appear after we detect the puja type.")
    with gr.Row():
        selection = gr.Dropdown(label="Select Pandit ID", choices=[])
        payment = gr.Radio(["UPI","NetBanking","Cash"], label="Payment Method", value="UPI")
    confirm_btn = gr.Button("✅ Confirm Booking")
    confirm_status = gr.Markdown()
    confirmation = gr.Markdown()
    hidden_state = gr.State(value="")

    mode.change(toggle_mode, inputs=[mode], outputs=[text_row, voice_row])
    find_btn.click(
        text_find_wrapper,
        inputs=[user_text],
        outputs=[status, parsed_box, table_md, explanations, selection, hidden_state, time_selector, set_time_btn, samagri_md, guide_md]
    )
    voice_btn.click(
        voice_find,
        inputs=[mic],
        outputs=[status, parsed_box, table_md, explanations, selection, hidden_state, time_selector, set_time_btn, samagri_md, guide_md]
    )
    set_time_btn.click(
        set_time_wrapper,
        inputs=[user_text, time_selector],
        outputs=[status, parsed_box, table_md, explanations, selection, hidden_state, time_selector, set_time_btn, samagri_md, guide_md]
    )
    confirm_btn.click(confirm_booking, inputs=[selection, payment, hidden_state],
                      outputs=[confirm_status, confirmation])

if __name__ == "__main__":
    demo.queue().launch()
