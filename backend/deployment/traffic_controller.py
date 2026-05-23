"""流量控制器模块 - 支持按比例、用户和地区进行流量分流"""

import hashlib
import ipaddress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


class TrafficStrategy(Enum):
    """流量分流策略"""

    PERCENTAGE = "percentage"
    USER_HASH = "user_hash"
    REGION = "region"
    WEIGHTED = "weighted"


@dataclass
class TrafficWeight:
    """流量权重配置"""

    version_id: str
    weight: float
    min_weight: float = 0.0
    max_weight: float = 100.0
    description: str = ""


@dataclass
class CanaryConfig:
    """灰度发布配置"""

    canary_id: str
    primary_version_id: str
    canary_version_id: str
    strategy: TrafficStrategy
    weights: List[TrafficWeight] = field(default_factory=list)
    user_ids: List[str] = field(default_factory=list)
    ip_ranges: List[str] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "canary_id": self.canary_id,
            "primary_version_id": self.primary_version_id,
            "canary_version_id": self.canary_version_id,
            "strategy": self.strategy.value,
            "weights": [
                {
                    "version_id": w.version_id,
                    "weight": w.weight,
                    "min_weight": w.min_weight,
                    "max_weight": w.max_weight,
                    "description": w.description,
                }
                for w in self.weights
            ],
            "user_ids": self.user_ids,
            "ip_ranges": self.ip_ranges,
            "regions": self.regions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TrafficController:
    """流量控制器"""

    def __init__(self):
        self._canary_configs: Dict[str, CanaryConfig] = {}
        self._traffic_stats: Dict[str, Dict[str, int]] = {}

    def create_canary_config(
        self,
        primary_version_id: str,
        canary_version_id: str,
        strategy: TrafficStrategy,
        weights: Optional[List[Dict[str, Any]]] = None,
        user_ids: Optional[List[str]] = None,
        ip_ranges: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
    ) -> CanaryConfig:
        """创建灰度配置"""
        canary_id = self._generate_canary_id()

        weight_objs = []
        if weights:
            for w in weights:
                weight_objs.append(
                    TrafficWeight(
                        version_id=w["version_id"],
                        weight=w.get("weight", 0),
                        min_weight=w.get("min_weight", 0),
                        max_weight=w.get("max_weight", 100),
                        description=w.get("description", ""),
                    )
                )

        config = CanaryConfig(
            canary_id=canary_id,
            primary_version_id=primary_version_id,
            canary_version_id=canary_version_id,
            strategy=strategy,
            weights=weight_objs,
            user_ids=user_ids or [],
            ip_ranges=ip_ranges or [],
            regions=regions or [],
        )

        self._canary_configs[canary_id] = config
        self._traffic_stats[canary_id] = {primary_version_id: 0, canary_version_id: 0}

        logger.info(f"创建灰度配置: {canary_id}")
        return config

    def get_canary_config(self, canary_id: str) -> Optional[CanaryConfig]:
        """获取灰度配置"""
        return self._canary_configs.get(canary_id)

    def list_canary_configs(self) -> List[CanaryConfig]:
        """列出所有灰度配置"""
        return list(self._canary_configs.values())

    def update_canary_config(
        self,
        canary_id: str,
        strategy: Optional[TrafficStrategy] = None,
        weights: Optional[List[Dict[str, Any]]] = None,
        user_ids: Optional[List[str]] = None,
        ip_ranges: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
        is_active: Optional[bool] = None,
    ) -> bool:
        """更新灰度配置"""
        if canary_id not in self._canary_configs:
            return False

        config = self._canary_configs[canary_id]

        if strategy:
            config.strategy = strategy

        if weights:
            config.weights = [
                TrafficWeight(
                    version_id=w["version_id"],
                    weight=w.get("weight", 0),
                    min_weight=w.get("min_weight", 0),
                    max_weight=w.get("max_weight", 100),
                    description=w.get("description", ""),
                )
                for w in weights
            ]

        if user_ids is not None:
            config.user_ids = user_ids

        if ip_ranges is not None:
            config.ip_ranges = ip_ranges

        if regions is not None:
            config.regions = regions

        if is_active is not None:
            config.is_active = is_active

        config.updated_at = datetime.now()

        logger.info(f"更新灰度配置: {canary_id}")
        return True

    def delete_canary_config(self, canary_id: str) -> bool:
        """删除灰度配置"""
        if canary_id in self._canary_configs:
            del self._canary_configs[canary_id]
            if canary_id in self._traffic_stats:
                del self._traffic_stats[canary_id]
            logger.info(f"删除灰度配置: {canary_id}")
            return True
        return False

    def route_request(
        self,
        canary_id: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """路由请求到指定版本"""
        if canary_id not in self._canary_configs:
            raise ValueError(f"灰度配置不存在: {canary_id}")

        config = self._canary_configs[canary_id]

        if not config.is_active:
            return config.primary_version_id

        if user_id and user_id in config.user_ids:
            self._record_traffic(canary_id, config.canary_version_id)
            return config.canary_version_id

        if ip_address:
            if self._is_ip_in_ranges(ip_address, config.ip_ranges):
                self._record_traffic(canary_id, config.canary_version_id)
                return config.canary_version_id

            region = self._get_ip_region(ip_address)
            if region in config.regions:
                self._record_traffic(canary_id, config.canary_version_id)
                return config.canary_version_id

        if config.strategy == TrafficStrategy.PERCENTAGE:
            return self._route_by_percentage(canary_id, config, user_id, session_id)
        elif config.strategy == TrafficStrategy.USER_HASH:
            return self._route_by_user_hash(canary_id, config, user_id, session_id)
        elif config.strategy == TrafficStrategy.REGION:
            return self._route_by_region(canary_id, config, ip_address)
        elif config.strategy == TrafficStrategy.WEIGHTED:
            return self._route_by_weight(canary_id, config, user_id, session_id)
        else:
            return config.primary_version_id

    def _route_by_percentage(
        self,
        canary_id: str,
        config: CanaryConfig,
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> str:
        """按百分比分流"""
        canary_weight = 0
        for weight in config.weights:
            if weight.version_id == config.canary_version_id:
                canary_weight = weight.weight
                break

        if canary_weight == 0:
            return config.primary_version_id

        identifier = user_id or session_id or "anonymous"
        hash_value = self._calculate_hash(identifier)
        percentage = hash_value % 100

        if percentage < canary_weight:
            self._record_traffic(canary_id, config.canary_version_id)
            return config.canary_version_id
        else:
            self._record_traffic(canary_id, config.primary_version_id)
            return config.primary_version_id

    def _route_by_user_hash(
        self,
        canary_id: str,
        config: CanaryConfig,
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> str:
        """按用户ID哈希分流"""
        identifier = user_id or session_id
        if not identifier:
            return config.primary_version_id

        hash_value = self._calculate_hash(identifier)
        canary_weight = self._get_canary_weight(config)

        if hash_value % 100 < canary_weight:
            self._record_traffic(canary_id, config.canary_version_id)
            return config.canary_version_id
        else:
            self._record_traffic(canary_id, config.primary_version_id)
            return config.primary_version_id

    def _route_by_region(
        self,
        canary_id: str,
        config: CanaryConfig,
        ip_address: Optional[str],
    ) -> str:
        """按地区分流"""
        if not ip_address:
            return config.primary_version_id

        region = self._get_ip_region(ip_address)

        if region in config.regions:
            self._record_traffic(canary_id, config.canary_version_id)
            return config.canary_version_id
        else:
            self._record_traffic(canary_id, config.primary_version_id)
            return config.primary_version_id

    def _route_by_weight(
        self,
        canary_id: str,
        config: CanaryConfig,
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> str:
        """按权重分流"""
        identifier = user_id or session_id or "anonymous"
        hash_value = self._calculate_hash(identifier)
        percentage = hash_value % 100

        cumulative = 0
        for weight in config.weights:
            cumulative += weight.weight
            if percentage < cumulative:
                self._record_traffic(canary_id, weight.version_id)
                return weight.version_id

        self._record_traffic(canary_id, config.primary_version_id)
        return config.primary_version_id

    def _is_ip_in_ranges(self, ip_address: str, ip_ranges: List[str]) -> bool:
        """检查IP是否在指定范围内"""
        try:
            ip = ipaddress.ip_address(ip_address)
            for ip_range in ip_ranges:
                network = ipaddress.ip_network(ip_range, strict=False)
                if ip in network:
                    return True
        except ValueError:
            logger.warning(f"无效的IP地址: {ip_address}")
        return False

    def _get_ip_region(self, ip_address: str) -> str:
        """根据IP获取地区"""
        try:
            ip = ipaddress.ip_address(ip_address)

            if ip.is_private:
                return "private"

            if isinstance(ip, ipaddress.IPv4Address):
                first_octet = int(str(ip).split(".")[0])

                if first_octet < 64:
                    return "north_america"
                elif first_octet < 128:
                    return "europe"
                elif first_octet < 192:
                    return "asia"
                else:
                    return "other"

            return "other"

        except ValueError:
            logger.warning(f"无效的IP地址: {ip_address}")
            return "unknown"

    def _get_canary_weight(self, config: CanaryConfig) -> float:
        """获取灰度版本权重"""
        for weight in config.weights:
            if weight.version_id == config.canary_version_id:
                return weight.weight
        return 10.0

    def _calculate_hash(self, identifier: str) -> int:
        """计算哈希值"""
        hash_bytes = hashlib.md5(identifier.encode(), usedforsecurity=False).digest()
        return int.from_bytes(hash_bytes[:4], byteorder="big")

    def _record_traffic(self, canary_id: str, version_id: str):
        """记录流量"""
        if canary_id in self._traffic_stats:
            if version_id in self._traffic_stats[canary_id]:
                self._traffic_stats[canary_id][version_id] += 1
            else:
                self._traffic_stats[canary_id][version_id] = 1

    def get_traffic_stats(self, canary_id: str) -> Dict[str, Any]:
        """获取流量统计"""
        if canary_id not in self._canary_configs:
            return {}

        config = self._canary_configs[canary_id]
        stats = self._traffic_stats.get(canary_id, {})

        total = sum(stats.values()) if stats else 0

        return {
            "canary_id": canary_id,
            "total_requests": total,
            "versions": {
                version_id: {
                    "requests": count,
                    "percentage": round((count / total * 100), 2) if total > 0 else 0,
                }
                for version_id, count in stats.items()
            },
            "is_active": config.is_active,
        }

    def adjust_weights(
        self,
        canary_id: str,
        canary_weight: float,
        smooth: bool = True,
    ) -> bool:
        """调整灰度权重"""
        if canary_id not in self._canary_configs:
            return False

        if not 0 <= canary_weight <= 100:
            raise ValueError("权重必须在 0-100 之间")

        config = self._canary_configs[canary_id]

        primary_weight = 100 - canary_weight

        config.weights = [
            TrafficWeight(
                version_id=config.primary_version_id,
                weight=primary_weight,
                description="主版本",
            ),
            TrafficWeight(
                version_id=config.canary_version_id,
                weight=canary_weight,
                description="灰度版本",
            ),
        ]

        config.updated_at = datetime.now()

        logger.info(f"调整灰度权重: {canary_id} -> canary={canary_weight}%, primary={primary_weight}%")
        return True

    def _generate_canary_id(self) -> str:
        """生成灰度配置ID"""
        import time
        hash_input = f"canary_{time.time()}"
        return hashlib.md5(hash_input.encode(), usedforsecurity=False).hexdigest()[:16]


_traffic_controller = TrafficController()


def get_traffic_controller() -> TrafficController:
    """获取流量控制器实例"""
    return _traffic_controller
