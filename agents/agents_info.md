# agents Module Information

This file provides an ultra-dense context mapping for agentic AI ingestion.


## File: `sre_swarm.py`
Imports: asyncio, logging, time, collections.{defaultdict}, typing.{Any,Dict,List,Optional}
Class `CircuitBreaker` (L20-49):
  > Docs: Circuit breaker pattern for fault tolerance.
  - `def __init__(self, failure_threshold, recovery_time)` (L23-28)
  - `def record_failure(self)` (L30-35)
  - `def record_success(self)` (L37-39)
  - `def can_execute(self)` (L41-49)
Class `SREMonitor` (L52-141):
  > Docs: Autonomous SRE self-healing monitor.
  - `def __init__(self, orchestrator)` (L55-60)
  - `async def monitor_and_heal(self, task_id, error_message)` (L62-89) - Classify error and attempt self-healing.
  - `def _classify_error(self, error_message)` (L91-106) - Classify error by type.
  - `async def _heal(self, error_type, task_id, error_msg)` (L108-123) - Attempt self-healing based on error type.
  - `def get_health_score(self)` (L125-132) - Calculate system health score (0-1).
  - `def get_status(self)` (L134-141)

## File: `vision_swarm.py`
Imports: logging, typing.{Any,Dict,List,Optional}
Class `VisionSwarm` (L16-70):
  > Docs: Multimodal vision capabilities for the agent.
  - `def __init__(self)` (L19-22)
  - `def _check_dependencies(self)` (L24-29)
  - `async def capture_screenshot(self, url, output_path)` (L31-50) - Capture a screenshot via Playwright.
  - `async def capture_and_detect(self, viewport_id, description)` (L52-61) - Capture and analyze an image.
  - `async def analyze_image(self, image_path, query)` (L63-70) - Analyze an image using multimodal LLM.

## File: `watchdog.py`
Imports: asyncio, logging, time, typing.{Any,Dict,List,Optional}
Class `WatchdogAgent` (L18-96):
  > Docs: System health watchdog with metric monitoring and auto-restart.
  - `def __init__(self, analytics, orchestrator)` (L21-31)
  - `async def start_monitoring(self)` (L33-46) - Start periodic health monitoring.
  - `async def stop_monitoring(self)` (L48-49)
  - `def collect_metrics(self)` (L51-68) - Collect system metrics using psutil.
  - `def _check_thresholds(self, metrics)` (L70-87) - Check metrics against thresholds and create alerts.
  - `def get_status(self)` (L89-96)

## File: `growth_swarm\gtm_swarm_controller.py`
Imports: asyncio, typing.{List,Dict,Any}, project_kernel_runtime.memory.state_hub.{state_hub}
Class `GtmSwarmController` (L10-92):
  - `def __init__(self, orchestrator)` (L11-14)
  - `async def initialize(self, orchestrator)` (L16-21) - Initializes the GTM Swarm with an orchestrator reference.
  - `async def start_campaign(self, name, target_niche)` (L23-33) - Triggers a high-velocity growth campaign.
  - `async def _generate_viral_asset(self, campaign_name, niche, lead)` (L35-55)
  - `async def _scout_leads(self, campaign_name, niche)` (L57-75)
  - `async def _perform_outreach(self, campaign_name, lead)` (L77-86) - Autonomous Outreach with Governance.
  - `async def _monitor_growth_loop(self)` (L88-92) - Background loop to maintain growth velocity.