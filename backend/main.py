import json
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

EMPTY_FEATURE_COLLECTION = {"type": "FeatureCollection", "features": []}

app = FastAPI(title="Zijingang WebGIS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StudyRoomRecommendationRequest(BaseModel):
    query: str


def get_charger_site_url() -> str:
    return os.getenv(
        "ZJU_CHARGER_SITE_URL",
        os.getenv("CHARGER_URL", "https://charger.philfan.cn/"),
    )


def read_geojson(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        return EMPTY_FEATURE_COLLECTION

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return EMPTY_FEATURE_COLLECTION

    if data.get("type") != "FeatureCollection" or not isinstance(
        data.get("features"), list
    ):
        return EMPTY_FEATURE_COLLECTION

    return data


def truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def safe_properties(feature: dict) -> dict:
    properties = feature.get("properties")
    return properties if isinstance(properties, dict) else {}


def summarize_study_room(feature: dict) -> dict:
    properties = safe_properties(feature)
    return {
        "id": properties.get("id"),
        "name": properties.get("name"),
        "building": properties.get("building"),
        "floor": properties.get("floor"),
        "room": properties.get("room"),
        "type": properties.get("type"),
        "open_time": properties.get("open_time"),
        "close_time": properties.get("close_time"),
        "seat_available": properties.get("seat_available"),
        "has_power": properties.get("has_power"),
        "noise_level": properties.get("noise_level"),
        "power_outlet_level": properties.get("power_outlet_level"),
        "group_study": properties.get("group_study"),
        "overnight_available": properties.get("overnight_available"),
        "nearby_facilities": properties.get("nearby_facilities"),
        "tags": properties.get("tags"),
        "description": properties.get("description"),
    }


def normalize_recommendation(item: dict[str, Any]) -> dict:
    return {
        "study_room_id": item.get("study_room_id") or item.get("id"),
        "name": item.get("name") or "未知自习室",
        "reason": item.get("reason") or "AI 未返回明确理由。",
        "matched_needs": item.get("matched_needs") or [],
        "notes": item.get("notes") or "推荐仅基于当前数据，实际可用情况请以现场为准。",
    }


def charger_unavailable(message: str) -> dict:
    return {
        "ok": False,
        "configured": False,
        "message": message,
        "fallback_url": get_charger_site_url(),
        "stations": [],
    }


def collect_station_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("stations", "data", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = collect_station_items(value)
            if nested:
                return nested

    return []


def first_value(source: dict, keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_zijingang_charger_station(item: dict) -> bool:
    campus_id = first_value(item, ("campus_id", "campus"), None)
    campus_name = str(first_value(item, ("campus_name", "campus_name_cn", "area"), ""))
    return str(campus_id) == "2" or campus_name == "紫金港校区"


def normalize_charger_station(item: dict) -> dict:
    total_ports = first_value(
        item,
        ("total_ports", "total", "total_count", "pile_total", "count", "total_num"),
        0,
    )
    available_ports = first_value(
        item,
        ("available_ports", "available", "free", "idle", "free_count", "available_num"),
        0,
    )

    return {
        "id": str(first_value(item, ("hash_id", "id", "station_id", "name"), "unknown")),
        "name": first_value(item, ("name", "station_name", "title"), "未知站点"),
        "provider": first_value(item, ("provider", "operator", "brand"), "unknown"),
        "campus": first_value(item, ("campus_name", "campus", "campus_id", "area"), "unknown"),
        "status": first_value(item, ("status", "state"), "unknown"),
        "total_ports": total_ports,
        "available_ports": available_ports,
        "occupied_ports": first_value(
            item,
            ("occupied_ports", "occupied", "busy", "used", "used_count"),
            None,
        ),
        "fault_ports": first_value(
            item,
            ("fault_ports", "fault", "broken", "error", "offline_count"),
            None,
        ),
        "updated_at": first_value(
            item,
            ("updated_at", "update_time", "last_update", "time"),
            "unknown",
        ),
        "longitude": first_value(item, ("longitude", "lng", "lon"), None),
        "latitude": first_value(item, ("latitude", "lat"), None),
        "devids": first_value(item, ("devids", "device_ids"), []),
        "raw": item,
    }


def normalize_charger_station(item: dict) -> dict:
    total_ports = to_int(first_value(
        item,
        ("total_ports", "total", "total_count", "pile_total", "count", "total_num"),
        0,
    ))
    available_ports = to_int(first_value(
        item,
        ("available_ports", "available", "free", "idle", "free_count", "available_num"),
        0,
    ))
    used_ports = to_int(first_value(
        item,
        ("used_ports", "used", "occupied_ports", "occupied", "busy", "used_count"),
        0,
    ))
    error_ports = to_int(first_value(
        item,
        ("error_ports", "error", "fault_ports", "fault", "broken", "offline_count"),
        0,
    ))
    campus_id = first_value(item, ("campus_id", "campus"), None)
    campus_name = first_value(item, ("campus_name", "campus_name_cn", "area"), "unknown")

    return {
        "id": str(first_value(item, ("hash_id", "id", "station_id", "name"), "unknown")),
        "name": first_value(item, ("name", "station_name", "title"), "未知站点"),
        "provider": first_value(item, ("provider", "operator", "brand"), "unknown"),
        "campus": campus_name,
        "campus_id": campus_id,
        "campus_name": campus_name,
        "status": first_value(item, ("status", "state"), "unknown"),
        "total_ports": total_ports,
        "available_ports": available_ports,
        "used_ports": used_ports,
        "occupied_ports": used_ports,
        "error_ports": error_ports,
        "fault_ports": error_ports,
        "has_available_ports": available_ports > 0,
        "updated_at": first_value(
            item,
            ("updated_at", "update_time", "last_update", "time"),
            "unknown",
        ),
        "longitude": to_float(first_value(item, ("longitude", "lng", "lon"), None)),
        "latitude": to_float(first_value(item, ("latitude", "lat"), None)),
        "devids": first_value(item, ("devids", "device_ids"), []),
    }


async def fetch_zju_charger_stations() -> dict:
    base_url = os.getenv("ZJU_CHARGER_API_BASE_URL", "").strip().rstrip("/")
    path = os.getenv("ZJU_CHARGER_STATIONS_PATH", "/api/status").strip()
    timeout_raw = os.getenv("ZJU_CHARGER_API_TIMEOUT", "8").strip()

    if not base_url:
        return charger_unavailable("未配置 ZJU_CHARGER_API_BASE_URL，当前使用 ZJU-Charger 外链兜底。")

    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 8.0

    url = f"{base_url}/{path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return {
            "ok": False,
            "configured": True,
            "message": "ZJU-Charger API 暂不可用，当前使用外链兜底。",
            "fallback_url": get_charger_site_url(),
            "stations": [],
        }

    station_items = collect_station_items(payload)
    stations = [
        normalize_charger_station(item)
        for item in station_items
        if is_zijingang_charger_station(item)
    ]

    return {
        "ok": True,
        "configured": True,
        "message": "已通过 ZJU-Charger API 获取充电桩站点数据。",
        "fallback_url": get_charger_site_url(),
        "source_url": url,
        "stations": stations,
    }


def keyword_score(query: str, room: dict) -> tuple[int, list[str]]:
    text = query.lower()
    score = 0
    matched_needs: list[str] = []

    seat_available = room.get("seat_available")
    if isinstance(seat_available, (int, float)) and seat_available > 0:
        score += 3
        matched_needs.append("有可用座位")

    if any(word in text for word in ["安静", "quiet", "复习", "专注"]):
        if room.get("noise_level") == "quiet" or room.get("type") == "quiet":
            score += 4
            matched_needs.append("安静")

    if any(word in text for word in ["讨论", "小组", "group", "合作"]):
        if room.get("group_study") is True or room.get("type") == "discussion":
            score += 4
            matched_needs.append("适合小组讨论")

    if any(word in text for word in ["通宵", "晚上", "夜间", "熬夜", "overnight"]):
        if room.get("overnight_available") is True or room.get("type") == "overnight":
            score += 4
            matched_needs.append("夜间可用")

    if any(word in text for word in ["插座", "电源", "充电", "power"]):
        if room.get("has_power") is True or room.get("power_outlet_level") == "many":
            score += 4
            matched_needs.append("电源条件较好")

    return score, matched_needs


def fallback_recommend(query: str, rooms: list[dict]) -> list[dict]:
    scored = []
    for room in rooms:
        score, matched_needs = keyword_score(query, room)
        scored.append((score, room, matched_needs))

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].get("seat_available")
            if isinstance(item[1].get("seat_available"), (int, float))
            else 0,
        ),
        reverse=True,
    )

    recommendations = []
    for score, room, matched_needs in scored[:3]:
        recommendations.append(
            {
                "study_room_id": room.get("id"),
                "name": room.get("name") or "未知自习室",
                "reason": "根据当前自习室数据和关键词规则推荐。"
                if score > 0
                else "当前需求没有明显匹配项，按可用座位等基础信息推荐。",
                "matched_needs": matched_needs,
                "notes": "当前为本地规则兜底推荐；配置 AI API Key 后可使用大模型推荐。",
            }
        )

    return recommendations


def build_ai_messages(query: str, rooms: list[dict]) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "你是浙江大学紫金港校区自习室推荐助手。"
                "你只能基于提供的自习室候选数据推荐，不要编造不存在的自习室。"
                "不要提供路线规划或校园导航建议。"
                "请严格返回 JSON，对象包含 recommendations 数组。"
                "每个推荐项包含 study_room_id、name、reason、matched_needs、notes。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_query": query,
                    "candidate_study_rooms": rooms,
                    "output_language": "zh-CN",
                    "max_recommendations": 3,
                },
                ensure_ascii=False,
            ),
        },
    ]


async def call_deepseek(query: str, rooms: list[dict]) -> list[dict]:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")

    payload = {
        "model": model,
        "messages": build_ai_messages(query, rooms),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    recommendations = parsed.get("recommendations")
    if not isinstance(recommendations, list):
        raise ValueError("AI response does not contain recommendations")

    return [normalize_recommendation(item) for item in recommendations[:3]]


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "project": "zijingang-webgis"}


@app.get("/api/study-rooms")
def study_rooms() -> dict:
    return read_geojson("study_rooms.geojson")


@app.get("/api/pois")
def pois() -> dict:
    return read_geojson("campus_pois.geojson")


@app.get("/api/buildings")
def buildings() -> dict:
    return read_geojson("buildings.geojson")


@app.get("/api/zjg-boundary")
def zjg_boundary() -> dict:
    return read_geojson("zjg.geojson")


@app.get("/api/config")
def config() -> dict:
    return {
        "charger_url": get_charger_site_url(),
        "charger_embed_mode": False,
        "ai_recommender_enabled": truthy_env("AI_RECOMMENDER_ENABLED")
        and bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
    }


@app.get("/api/chargers/status")
async def charger_status() -> dict:
    base_url = os.getenv("ZJU_CHARGER_API_BASE_URL", "").strip()
    return {
        "ok": True,
        "api_configured": bool(base_url),
        "api_base_url": base_url or None,
        "stations_path": os.getenv("ZJU_CHARGER_STATIONS_PATH", "/api/status"),
        "fallback_url": get_charger_site_url(),
        "message": "ZJU-Charger API 已配置。"
        if base_url
        else "ZJU-Charger API 尚未配置，前端应显示外链兜底。",
    }


@app.get("/api/chargers/stations")
async def charger_stations() -> dict:
    return await fetch_zju_charger_stations()


def geoserver_base_url() -> str:
    return os.getenv("GEOSERVER_URL", "http://127.0.0.1:8080/geoserver").rstrip("/")


def geoserver_workspace() -> str:
    return os.getenv("GEOSERVER_WORKSPACE", "webgis")


@app.get("/api/geoserver/status")
async def geoserver_status() -> dict:
    """检测 GeoServer 是否可达（使用公开 WFS 端点，无需认证）。"""
    base = geoserver_base_url()
    workspace = geoserver_workspace()
    # 用 WFS GetCapabilities 探测，不需要登录
    url = f"{base}/{workspace}/ows?service=WFS&version=1.0.0&request=GetCapabilities"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()
        return {
            "ok": True,
            "reachable": True,
            "message": "GeoServer 连接正常。",
            "base_url": base,
        }
    except Exception:
        return {
            "ok": False,
            "reachable": False,
            "message": "GeoServer 暂不可用，请确认服务已启动。",
            "base_url": base,
        }


@app.get("/api/geoserver/wfs")
async def geoserver_wfs(layer: str = "campus_pois") -> dict:
    """代理 GeoServer WFS GetFeature 请求，返回 GeoJSON。"""
    base = geoserver_base_url()
    workspace = geoserver_workspace()
    url = (
        f"{base}/{workspace}/ows"
        f"?service=WFS&version=1.0.0&request=GetFeature"
        f"&typeName={workspace}:{layer}"
        f"&outputFormat=application/json"
    )
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        features = data.get("features")
        if not isinstance(features, list):
            return {"type": "FeatureCollection", "features": []}
        return {"type": "FeatureCollection", "features": features}
    except Exception:
        return {"type": "FeatureCollection", "features": []}


@app.post("/api/ai/recommend-study-room")
async def recommend_study_room(request: StudyRoomRecommendationRequest) -> dict:
    query = request.query.strip()
    study_room_data = read_geojson("study_rooms.geojson")
    rooms = [summarize_study_room(feature) for feature in study_room_data["features"]]

    if not rooms:
        return {
            "ok": False,
            "mode": "empty",
            "message": "暂无自习室数据，无法推荐。",
            "query": query,
            "recommendations": [],
        }

    if not query:
        return {
            "ok": False,
            "mode": "invalid",
            "message": "请输入你的学习需求。",
            "query": query,
            "recommendations": [],
        }

    ai_enabled = truthy_env("AI_RECOMMENDER_ENABLED")
    has_api_key = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())

    if ai_enabled and has_api_key:
        try:
            recommendations = await call_deepseek(query, rooms)
            return {
                "ok": True,
                "mode": "ai",
                "message": "已根据你的需求生成 AI 推荐。",
                "query": query,
                "recommendations": recommendations,
            }
        except Exception:
            recommendations = fallback_recommend(query, rooms)
            return {
                "ok": True,
                "mode": "fallback",
                "message": "AI 服务暂不可用，当前使用本地规则兜底推荐。",
                "query": query,
                "recommendations": recommendations,
            }

    recommendations = fallback_recommend(query, rooms)
    return {
        "ok": True,
        "mode": "fallback",
        "message": "未配置 AI API Key，当前使用本地规则兜底推荐。",
        "query": query,
        "recommendations": recommendations,
    }
