"""Simulări asincrone cu cache în memorie (docs/API.md §2.5).

Cheia este SHA-256 al cererii canonice.

Aceeași cerere (după completarea pasului seriei) are același identificator și aceeași simulare.
Cache-ul este în memorie și se pierde la repornirea procesului; nu este un depozit persistent.
Accesul la SPICE este serializat de `SPICE_LOCK`; lucrătorii calculează în fire separate.
"""

import hashlib
import json
import logging
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from lunarhorizon.api.data import DataRegistry
from lunarhorizon.api.problems import from_error, internal_problem
from lunarhorizon.api.settings import Settings
from lunarhorizon.astro.kernels import LoadedProfile
from lunarhorizon.astro.timeconv import require_in_coverage, utc_to_et
from lunarhorizon.contracts.service import Problem
from lunarhorizon.contracts.simulation import (
    Progress,
    SimulationAccepted,
    SimulationRequest,
    SimulationResult,
    SimulationState,
    SimulationStatus,
)
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError
from lunarhorizon.simulation.idealized import SiteInput, simulate_idealized
from lunarhorizon.simulation.service import prepare_request

LOGGER = logging.getLogger(__name__)


def request_key(request: SimulationRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class _Job:
    id: str
    status: SimulationState
    stage: str = "în așteptare"
    completed_fraction: float = 0.0
    result: SimulationResult | None = None
    error: Problem | None = None


class SimulationService:
    def __init__(self, settings: Settings, registry: DataRegistry) -> None:
        self._settings = settings
        self._registry = registry
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, _Job] = OrderedDict()
        self._executor = ThreadPoolExecutor(
            max_workers=settings.max_workers, thread_name_prefix="simulation"
        )

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    # --- trimiterea cererii ----------------------------------------------------------------

    def submit(self, request: SimulationRequest) -> SimulationAccepted:
        """Validează sincron (erorile devin răspunsuri HTTP) și pornește sau regăsește simularea."""
        prepared, sites = prepare_request(
            request,
            self._registry.catalog(),
            self._settings.max_interval_days,
            self._settings.max_series_points,
        )
        profile = self._registry.profile_for_frame(prepared.frame_id)
        for moment in (prepared.start_utc, prepared.end_utc):
            require_in_coverage(utc_to_et(moment, profile), profile)
        job_id = f"sim-{request_key(prepared)[:32]}"
        with self._lock:
            existing = self._jobs.get(job_id)
            if existing is not None and existing.status != "failed":
                self._jobs.move_to_end(job_id)
                return SimulationAccepted(id=job_id, status=existing.status, cache_hit=True)
            self._jobs[job_id] = _Job(id=job_id, status="queued")
            self._jobs.move_to_end(job_id)
            self._evict()
        self._executor.submit(self._run, job_id, prepared, sites, profile)
        return SimulationAccepted(id=job_id, status="queued", cache_hit=False)

    def _evict(self) -> None:
        finished = [key for key, job in self._jobs.items() if job.status in ("done", "failed")]
        while len(finished) > self._settings.cache_size:
            del self._jobs[finished.pop(0)]

    # --- execuție --------------------------------------------------------------------------

    def _update(self, job_id: str, **changes: object) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                for name, value in changes.items():
                    setattr(job, name, value)

    def _run(
        self,
        job_id: str,
        request: SimulationRequest,
        sites: list[SiteInput],
        profile: LoadedProfile,
    ) -> None:
        self._update(job_id, status="running", stage="pornire")

        def progress(stage: str, fraction: float) -> None:
            self._update(job_id, stage=stage, completed_fraction=min(max(fraction, 0.0), 1.0))

        try:
            result = simulate_idealized(request, sites, profile, progress)
        except LunarHorizonError as error:
            self._update(job_id, status="failed", stage="eșuat", error=from_error(error))
        except Exception:
            LOGGER.exception("simularea %s a eșuat", job_id)
            self._update(job_id, status="failed", stage="eșuat", error=internal_problem())
        else:
            self._update(
                job_id, status="done", stage="terminat", completed_fraction=1.0, result=result
            )

    # --- citire ----------------------------------------------------------------------------

    def status(self, job_id: str) -> SimulationStatus:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise LunarHorizonError(
                    ErrorCode.SIMULATION_NOT_FOUND, f"simularea {job_id!r} nu există"
                )
            progress = (
                Progress(stage=job.stage, completed_fraction=job.completed_fraction)
                if job.status in ("queued", "running")
                else None
            )
            return SimulationStatus(
                id=job.id, status=job.status, progress=progress, error=job.error, result=job.result
            )
