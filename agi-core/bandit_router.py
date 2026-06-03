"""
bandit_router.py — Thompson Sampling 模型路由器

Why: 静态路由表无法适应模型性能变化，Thompson Sampling 在线学习最优分配
What: 每个 (task_type, model) pair 维护 Beta 分布 → 采样选择 → 反馈更新
Test: python3 bandit_router.py select "code_gen" → 返回最优模型

算法: Thompson Sampling
  - 每个 arm (model) 有 Beta(α, β) 分布
  - α = 成功次数 + 1, β = 失败次数 + 1
  - 每次选择: 采样所有 arm 的 θ ~ Beta(α, β)，选 θ 最大的
  - 反馈: 成功 → α+=1, 失败 → β+=1
"""

import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# 可用模型列表（从 LiteLLM 网关）
MODELS = [
    "glm-5.1", "glm-5-turbo", "glm-4.7",
    "step-3.5-flash-2603-plan", "step-router-v1",
    "deepseek-v3", "qwen3-235b",
]

# 任务类型 → 候选模型子集（缩小搜索空间）
TASK_MODEL_MAP = {
    "code_gen": ["glm-5.1", "step-3.5-flash-2603-plan", "deepseek-v3"],
    "code_review": ["glm-5.1", "step-3.5-flash-2603-plan"],
    "arch_design": ["glm-5.1", "deepseek-v3"],
    "chat": ["glm-5-turbo", "glm-4.7", "step-router-v1"],
    "analysis": ["glm-5.1", "glm-5-turbo", "deepseek-v3"],
    "ops": ["step-router-v1", "glm-4.7"],
    "default": MODELS,
}

STATE_FILE = Path.home() / ".local/state/bandit_router.json"


@dataclass
class ArmState:
    """单个 arm (model) 的 Beta 分布参数。"""
    alpha: float = 1.0   # 成功次数 + 1 (prior)
    beta: float = 1.0    # 失败次数 + 1 (prior)
    last_used: float = 0.0
    total_uses: int = 0

    def sample(self) -> float:
        """Thompson Sampling: 从 Beta(α, β) 采样。"""
        return random.betavariate(self.alpha, self.beta)

    def update(self, success: bool) -> None:
        """反馈更新: 成功→α++, 失败→β++。"""
        if success:
            self.alpha += 1
        else:
            self.beta += 1
        self.total_uses += 1
        self.last_used = time.time()


@dataclass
class RouterState:
    """路由器全局状态: task_type → model → ArmState。"""
    arms: dict[str, dict[str, ArmState]] = field(default_factory=dict)
    total_requests: int = 0
    total_success: int = 0

    def get_arm(self, task_type: str, model: str) -> ArmState:
        """获取或创建 arm。"""
        if task_type not in self.arms:
            self.arms[task_type] = {}
        if model not in self.arms[task_type]:
            self.arms[task_type][model] = ArmState()
        return self.arms[task_type][model]

    def select(self, task_type: str) -> str:
        """Thompson Sampling 选择最优模型。"""
        candidates = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["default"])
        best_model = None
        best_sample = -1

        for model in candidates:
            arm = self.get_arm(task_type, model)
            sample = arm.sample()
            if sample > best_sample:
                best_sample = sample
                best_model = model

        self.total_requests += 1
        arm = self.get_arm(task_type, best_model)
        arm.last_used = time.time()
        arm.total_uses += 1
        return best_model

    def feedback(self, task_type: str, model: str, success: bool) -> None:
        """记录反馈，更新 Beta 分布。"""
        arm = self.get_arm(task_type, model)
        arm.update(success)
        if success:
            self.total_success += 1

    def success_rate(self) -> float:
        """全局成功率。"""
        if self.total_requests == 0:
            return 0.0
        return self.total_success / self.total_requests

    def to_dict(self) -> dict:
        """序列化状态。"""
        return {
            "arms": {
                tt: {
                    m: {"a": a.alpha, "b": a.beta, "uses": a.total_uses, "last": a.last_used}
                    for m, a in models.items()
                }
                for tt, models in self.arms.items()
            },
            "total_requests": self.total_requests,
            "total_success": self.total_success,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RouterState":
        """反序列化状态。"""
        state = cls()
        state.total_requests = data.get("total_requests", 0)
        state.total_success = data.get("total_success", 0)
        for tt, models in data.get("arms", {}).items():
            state.arms[tt] = {}
            for m, v in models.items():
                arm = ArmState(alpha=v["a"], beta=v["b"], total_uses=v.get("uses", 0), last_used=v.get("last", 0))
                state.arms[tt][m] = arm
        return state


# ── 全局路由器实例 ──────────────────────────────────────────────────────────

_router: Optional[RouterState] = None


def get_router() -> RouterState:
    """获取全局路由器（懒加载 + 持久化）。"""
    global _router
    if _router is None:
        _router = _load_state()
    return _router


def _load_state() -> RouterState:
    """从文件加载状态。"""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return RouterState.from_dict(data)
    except Exception:
        pass
    return RouterState()


def _save_state() -> None:
    """持久化状态到文件。"""
    global _router
    if _router:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(_router.to_dict(), indent=2))
        except Exception:
            pass


# ── 公共 API ──────────────────────────────────────────────────────────────────

def select_model(task_type: str = "default") -> str:
    """选择模型（Thompson Sampling）。"""
    router = get_router()
    model = router.select(task_type)
    _save_state()
    return model


def record_feedback(task_type: str, model: str, success: bool) -> None:
    """记录模型选择结果。"""
    router = get_router()
    router.feedback(task_type, model, success)
    _save_state()


def get_stats() -> dict:
    """获取路由器统计。"""
    router = get_router()
    stats = {
        "total_requests": router.total_requests,
        "success_rate": round(router.success_rate(), 3),
        "task_types": {},
    }
    for tt, models in router.arms.items():
        best_model = max(models.items(), key=lambda x: x[1].alpha / (x[1].alpha + x[1].beta))
        stats["task_types"][tt] = {
            "best_model": best_model[0],
            "confidence": round(best_model[1].alpha / (best_model[1].alpha + best_model[1].beta), 3),
            "total_uses": sum(m.total_uses for m in models.values()),
        }
    return stats


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python3 bandit_router.py select <task_type> | feedback <task_type> <model> <0|1> | stats")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "select":
        tt = sys.argv[2] if len(sys.argv) > 2 else "default"
        model = select_model(tt)
        print(json.dumps({"task_type": tt, "selected_model": model}, ensure_ascii=False))

    elif cmd == "feedback":
        tt = sys.argv[2] if len(sys.argv) > 2 else "default"
        model = sys.argv[3] if len(sys.argv) > 3 else "glm-5.1"
        success = sys.argv[4] == "1" if len(sys.argv) > 4 else True
        record_feedback(tt, model, success)
        print(json.dumps({"task_type": tt, "model": model, "success": success}, ensure_ascii=False))

    elif cmd == "stats":
        print(json.dumps(get_stats(), ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {cmd}", file=sys.stderr)
        sys.exit(1)
