"""Stările în timp și evenimentele unui criteriu de vizibilitate (E10; SPEC_FIZICA §8).

Intrarea este o funcție `evaluate(t)` (t în secunde de la începutul intervalului) care întoarce
valoarea criteriului (g pentru Soare, marja pentru Pământ), rezoluția ε și starea `visible` /
`hidden` / `unknown` (cu motiv). Algoritmul:

1. eșantionare pe o grilă cu pasul `step_s`;
2. între două eșantioane cu stări diferite, granițele se rafinează prin bisecție până la
   `tolerance_s`;
3. între două eșantioane cu aceeași stare cunoscută, intervalul se subdivide dacă criteriul *ar
   putea* atinge banda |v| ≤ ε între ele (estimare Lipschitz din pantele vecine, cu factor de
   siguranță), până la `min_step_s`: lipsa schimbării de semn la capete nu exclude un eveniment
   între ele;
4. evenimentele se citesc din succesiunea stărilor: `visible → [near] → hidden` este o dispariție,
   `hidden → [near] → visible` o apariție, iar `visible → near → visible` / `hidden → near → hidden`
   un contact tangent. Momentul este rădăcina criteriului (bisecție), iar fereastra este intervalul
   în care starea nu poate fi decisă. La granițele zonelor fără date nu se creează evenimente.

Toleranța numerică (`tolerance_s`) descrie precizia rădăcinii pentru modelul folosit; incertitudinea
fizică (DEM, efemeride) se evaluează separat (VALIDARE).
"""

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Literal

TimelineState = Literal["visible", "hidden", "unknown"]
TransitionKind = Literal["appearance", "disappearance", "tangent_contact"]
NEAR: Final = "near_threshold"
LIPSCHITZ_SAFETY: Final = 2.0


@dataclass(frozen=True)
class Sample:
    t: float
    value: float | None
    eps: float
    state: TimelineState
    reason: str | None

    @property
    def key(self) -> tuple[TimelineState, str | None]:
        return self.state, self.reason


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    state: TimelineState
    reason: str | None


@dataclass(frozen=True)
class Transition:
    kind: TransitionKind
    time: float
    window_start: float
    window_end: float


@dataclass(frozen=True)
class ScanResult:
    segments: list[Segment]
    transitions: list[Transition]
    evaluations: int


class _Scanner:
    def __init__(
        self,
        evaluate: Callable[[float], Sample],
        tolerance_s: float,
        min_step_s: float,
    ) -> None:
        self._evaluate = evaluate
        self.tolerance = tolerance_s
        self.min_step = min_step_s
        self.count = 0

    def sample(self, t: float) -> Sample:
        self.count += 1
        return self._evaluate(t)

    def boundaries(self, a: Sample, b: Sample) -> list[Sample]:
        """Schimbările de stare din (a, b]; fiecare element este primul eșantion al stării noi."""
        found: list[Sample] = []
        left = a
        while left.key != b.key:
            lo, hi = left, b
            while hi.t - lo.t > self.tolerance:
                mid = self.sample((lo.t + hi.t) / 2.0)
                if mid.key == lo.key:
                    lo = mid
                else:
                    hi = mid
            found.append(hi)
            left = hi
            if hi is b:
                break
        return found

    def suspicious(self, a: Sample, b: Sample, slope: float) -> bool:
        """Criteriul ar putea atinge banda |v| ≤ ε între a și b (estimare Lipschitz)."""
        if a.value is None or b.value is None or a.state == "unknown":
            return False
        gap = min(abs(a.value) - a.eps, abs(b.value) - b.eps)
        return gap <= slope * (b.t - a.t) / 2.0

    def refine_pair(self, a: Sample, b: Sample, slope: float) -> list[Sample]:
        """Eșantioanele noi, în ordine, care descriu corect stările din (a, b)."""
        if a.key != b.key:
            return self.boundaries(a, b)
        if b.t - a.t <= self.min_step or not self.suspicious(a, b, slope):
            return []
        mid = self.sample((a.t + b.t) / 2.0)
        local = slope
        if a.value is not None and mid.value is not None and b.value is not None:
            local = max(
                slope,
                LIPSCHITZ_SAFETY * abs(mid.value - a.value) / (mid.t - a.t),
                LIPSCHITZ_SAFETY * abs(b.value - mid.value) / (b.t - mid.t),
            )
        left = self.refine_pair(a, mid, local)
        right = self.refine_pair(mid, b, local)
        if mid.key == a.key and not left and not right:
            return []
        return [*left, mid, *right]

    def root(self, lo: Sample, hi: Sample) -> float:
        """Rădăcina criteriului între două eșantioane cu semne opuse (bisecție)."""
        assert lo.value is not None and hi.value is not None
        sign = lo.value > 0
        while hi.t - lo.t > self.tolerance:
            mid = self.sample((lo.t + hi.t) / 2.0)
            if mid.value is None:
                break
            if (mid.value > 0) == sign:
                lo = mid
            else:
                hi = mid
        return (lo.t + hi.t) / 2.0

    def extremum(self, start: float, end: float, maximum: bool) -> float:
        """Extremul criteriului în fereastră (căutare ternară); folosit la contactele tangente."""
        lo, hi = start, end
        while hi - lo > self.tolerance:
            m1, m2 = lo + (hi - lo) / 3.0, hi - (hi - lo) / 3.0
            v1, v2 = self.sample(m1).value, self.sample(m2).value
            if v1 is None or v2 is None:
                break
            if (v1 < v2) == maximum:
                lo = m1
            else:
                hi = m2
        return (lo + hi) / 2.0


def scan(
    evaluate: Callable[[float], Sample],
    duration_s: float,
    step_s: float,
    tolerance_s: float = 1e-3,
    min_step_s: float = 1.0,
) -> ScanResult:
    """Segmentele de stare (partiție a [0, duration_s]) și tranzițiile criteriului."""
    scanner = _Scanner(evaluate, tolerance_s, min_step_s)
    count = max(1, int(duration_s // step_s))
    times = [k * step_s for k in range(count + 1) if k * step_s < duration_s] + [duration_s]
    grid = [scanner.sample(t) for t in times]
    slopes: list[float] = []
    for a, b in itertools.pairwise(grid):
        if a.value is not None and b.value is not None and b.t > a.t:
            slopes.append(abs(b.value - a.value) / (b.t - a.t))
        else:
            slopes.append(0.0)
    samples: list[Sample] = [grid[0]]
    for index, (a, b) in enumerate(itertools.pairwise(grid)):
        neighbourhood = slopes[max(0, index - 1) : index + 2]
        slope = LIPSCHITZ_SAFETY * max(neighbourhood)
        samples.extend(scanner.refine_pair(a, b, slope))
        samples.append(b)

    segments: list[Segment] = []
    start = samples[0]
    first_of_state = samples[0]
    for current in samples[1:]:
        if current.key != first_of_state.key:
            segments.append(
                Segment(start.t, current.t, first_of_state.state, first_of_state.reason)
            )
            start = current
            first_of_state = current
    segments.append(Segment(start.t, duration_s, first_of_state.state, first_of_state.reason))
    segments = [s for s in segments if s.end > s.start]
    merged: list[Segment] = []
    for segment in segments:
        if merged and (merged[-1].state, merged[-1].reason) == (segment.state, segment.reason):
            merged[-1] = Segment(merged[-1].start, segment.end, segment.state, segment.reason)
        else:
            merged.append(segment)

    transitions = _transitions(merged, samples, scanner)
    return ScanResult(merged, transitions, scanner.count)


def _sample_near(samples: list[Sample], t: float) -> Sample:
    return min(samples, key=lambda s: abs(s.t - t))


def _transitions(
    segments: list[Segment], samples: list[Sample], scanner: _Scanner
) -> list[Transition]:
    found: list[Transition] = []
    for index, segment in enumerate(segments):
        known = segment.state in ("visible", "hidden")
        if known and index + 1 < len(segments):
            following = segments[index + 1]
            if following.state in ("visible", "hidden") and following.state != segment.state:
                # Trecere directă (fereastra nedecidabilă este sub toleranță).
                kind: TransitionKind = (
                    "disappearance" if segment.state == "visible" else "appearance"
                )
                found.append(
                    Transition(
                        kind, following.start, following.start - scanner.tolerance, following.start
                    )
                )
            continue
        if segment.state != "unknown" or segment.reason != NEAR:
            continue
        if index == 0 or index + 1 >= len(segments):
            continue  # fereastră trunchiată la capătul intervalului: fără eveniment
        before, after = segments[index - 1], segments[index + 1]
        if before.state == "unknown" or after.state == "unknown":
            continue  # lângă o zonă fără date: fără eveniment
        if before.state != after.state:
            lo = scanner.sample(segment.start - scanner.tolerance / 2.0)
            hi = scanner.sample(segment.end)
            if lo.value is None or hi.value is None or (lo.value > 0) == (hi.value > 0):
                time = (segment.start + segment.end) / 2.0
            else:
                time = scanner.root(lo, hi)
            kind = "disappearance" if before.state == "visible" else "appearance"
            found.append(Transition(kind, time, segment.start, segment.end))
        else:
            # Atinge banda nedecidabilă și revine: contact (aproape) tangent, nu vizibilitate.
            time = scanner.extremum(segment.start, segment.end, maximum=before.state == "hidden")
            found.append(Transition("tangent_contact", time, segment.start, segment.end))
    return found
