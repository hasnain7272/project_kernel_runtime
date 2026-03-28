# agents Architecture Documentation

*Generated on: 2026-03-28T15:12:48.031846*

---

#### growth_swarm\__init__.py *(1 lines)*

> **Imports**: `from gtm_swarm_controller import gtm_swarm`

---

#### growth_swarm\gtm_swarm_controller.py *(95 lines)*

> **Imports**: `import asyncio`, `from typing import List`, `from typing import Dict`, `from typing import Any`, `from project_kernel_runtime.memory.state_hub import state_hub`

> **Constants**: `gtm_swarm`=GtmSwarmController()

> **Classes**:
  - **GtmSwarmController** (lines 10-92)
    - `__init__(self, orchestrator)` (lines 11-14)

---

#### sre_swarm.py *(141 lines)*

> **Imports**: `import asyncio`, `import logging`, `import time`, `from collections import defaultdict`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **CircuitBreaker** – *Circuit breaker pattern for fault tolerance.* (lines 20-49)
    - `__init__(self, failure_threshold, recovery_time)` (lines 23-28)
    - `record_failure(self)` (lines 30-35)
    - `record_success(self)` (lines 37-39)
    - `can_execute(self)` (lines 41-49)
  - **SREMonitor** – *Autonomous SRE self-healing monitor.* (lines 52-141)
    - `__init__(self, orchestrator)` (lines 55-60)
    - `_classify_error(self, error_message)` – *Classify error by type.* (lines 91-106)
    - `get_health_score(self)` – *Calculate system health score (0-1).* (lines 125-132)
    - `get_status(self)` (lines 134-141)

---

#### vision_swarm.py *(74 lines)*

> **Imports**: `import logging`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `import playwright`, `from playwright.async_api import async_playwright`

> **Constants**: `logger`=logging.getLogger(__name__), `vision_swarm`=VisionSwarm()

> **Classes**:
  - **VisionSwarm** – *Multimodal vision capabilities for the agent.* (lines 16-70)
    - `__init__(self)` (lines 19-22)
    - `_check_dependencies(self)` (lines 24-29)

---

#### watchdog.py *(96 lines)*

> **Imports**: `import asyncio`, `import logging`, `import time`, `from typing import Any`, `from typing import Dict`, `from typing import List`, `from typing import Optional`, `import psutil`

> **Constants**: `logger`=logging.getLogger(__name__)

> **Classes**:
  - **WatchdogAgent** – *System health watchdog with metric monitoring and auto-restart.* (lines 18-96)
    - `__init__(self, analytics, orchestrator)` (lines 21-31)
    - `collect_metrics(self)` – *Collect system metrics using psutil.* (lines 51-68)
    - `_check_thresholds(self, metrics)` – *Check metrics against thresholds and create alerts.* (lines 70-87)
    - `get_status(self)` (lines 89-96)

---

