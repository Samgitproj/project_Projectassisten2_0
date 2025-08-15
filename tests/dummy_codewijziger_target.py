# [SECTION: IMPORTS]
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any, Optional
# [END: SECTION: IMPORTS]


# [SECTION: CONSTANTS]
APP_NAME: str = "CodeWijzigerDummy"
DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "features": {
        "enable_logging": True,
        "simulate_network": True,
        "retry_attempts": 2,
    },
}
CONFIG_FILE: str = "dummy_config.json"
# [END: SECTION: CONSTANTS]


# [SECTION: LOGGING]
logger = logging.getLogger(APP_NAME)
if not logger.handlers:
    _h = logging.StreamHandler()
    _fmt = logging.Formatter("[%(levelname)s] %(message)s")
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
logger.setLevel(logging.INFO)
# [END: SECTION: LOGGING]


# [CLASS: Timer]
class Timer:
    """Eenvoudige context manager om tijden te meten."""

    def __init__(self, label: str = "elapsed"):
        self.label = label
        self.start: Optional[float] = None
        self.elapsed: Optional[float] = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.elapsed = time.perf_counter() - (self.start or time.perf_counter())
        logger.info(f"{self.label}: {self.elapsed:.4f}s")


# [END: CLASS: Timer]


# [CLASS: Greeter]
class Greeter:
    """Voorbeeldklasse met instance-, class- en staticmethod."""

    def __init__(self, name: str):
        self.name = name

    def greet(self) -> str:
        return f"Hallo, {self.name}!"

    @classmethod
    def default(cls) -> "Greeter":
        return cls("Wereld")

    @staticmethod
    def shout(text: str) -> str:
        return text.upper()


# [END: CLASS: Greeter]


# [SECTION: UTILS]
def slugify(text: str) -> str:
    """Maak een eenvoudige slug."""
    text = re.sub(r"[^a-zA-Z0-9\-]+", "-", text.strip().lower())
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "n-a"


def chunked(it: Iterable[Any], size: int) -> Iterator[List[Any]]:
    """Itereer in chunks (voor diffs handig)."""
    buf: List[Any] = []
    for item in it:
        buf.append(item)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf


def retry(
    attempts: int = 2, delay: float = 0.1
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: simpele retry."""

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            last_exc = None
            for i in range(max(1, attempts)):
                try:
                    return fn(*args, **kwargs)
                except Exception as ex:  # noqa: BLE001 (expres breed voor dummy)
                    last_exc = ex
                    time.sleep(delay)
            raise last_exc  # type: ignore[misc]

        return wrapper

    return deco


# [END: SECTION: UTILS]


# [FUNC: load_config]
def load_config(path: Path) -> Dict[str, Any]:
    """
    Laadt JSON-config. Bestaat het bestand niet, dan wordt DEFAULT_CONFIG weggeschreven en retour.
    Let op: in deze docstring staan woorden als [FUNC: demo] maar niet als marker-regel.
    """
    try:
        if not path.exists():
            path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
            return DEFAULT_CONFIG.copy()
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        logger.warning(f"Config onleesbaar ({ex}); overschrijven met default.")
        path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()


# [END: FUNC: load_config]


# [FUNC: save_config]
def save_config(path: Path, data: Dict[str, Any]) -> None:
    """Bewaar JSON-config naar schijf."""
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# [END: FUNC: save_config]


# [FUNC: parse_kv_lines]
def parse_kv_lines(lines: Iterable[str]) -> Dict[str, str]:
    """
    Parse regels van de vorm KEY=VALUE (spaties ok). Lege of commentregels (#) worden genegeerd.
    """
    result: Dict[str, str] = {}
    pat = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
    for raw in lines:
        line = raw.rstrip("\n")
        if not line or line.lstrip().startswith("#"):
            continue
        m = pat.match(line)
        if m:
            k, v = m.group(1), m.group(2)
            result[k] = v
    return result


# [END: FUNC: parse_kv_lines]


# [FUNC: process_items]
def process_items(items: Iterable[int]) -> List[int]:
    """Voorbeeld met comprehensions en kleine varianten."""
    base = [x * 2 for x in items]
    # variatie: set/dict comp
    _ = {x: x**2 for x in base}
    __ = {x**2 for x in base}
    return [x for x in base if x % 3 != 0]


# [END: FUNC: process_items]


# [FUNC: simulated_network_call]
@retry(attempts=2, delay=0.05)
def simulated_network_call(endpoint: str) -> Dict[str, Any]:
    """
    Simuleer netwerk: faalt 1e keer bij een specifiek endpoint, slaagt daarna.
    Gebruik voor diff-tests met decorator, exceptions en return-waarden.
    """
    if (
        "fail-once" in endpoint
        and getattr(simulated_network_call, "_flag", False) is False
    ):
        setattr(simulated_network_call, "_flag", True)
        raise RuntimeError("Simulated temporary failure")
    # Geen echte netwerkcall: we geven alleen data terug
    return {"endpoint": endpoint, "ok": True, "ts": time.time()}


# [END: FUNC: simulated_network_call]


# [FUNC: dangerous_op]
def dangerous_op(path: Path) -> str:
    """
    Voorbeeld try/except/finally met file I/O + unicode.
    """
    fh = None
    try:
        fh = path.open("w", encoding="utf-8")
        fh.write("Áéîöú — unicode test line\n")
        raise ValueError("Dummy fout ná eerste write")
    except ValueError as ex:
        logger.error(f"dangerous_op error: {ex}")
        return "error"
    finally:
        if fh:
            fh.close()


# [END: FUNC: dangerous_op]


# [SECTION: DATA MODELS]
@dataclass
class Item:
    id: int
    name: str
    tags: List[str]

    def serialize(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "tags": self.tags}


# [END: SECTION: DATA MODELS]


# [SECTION: EXTENSION_POINTS]
# Hier kun je met de codewijziger later nieuwe functies/klassen toevoegen
# vóór onderstaande END-marker. Laat dit blok bestaan zodat ADD-tests makkelijk zijn.

# Voorbeeld (bewust leeg gelaten):
# [FUNC: placeholder_new_feature]
# def placeholder_new_feature():
#     """Wordt later met ADD vervangen."""
#     pass
# [END: FUNC: placeholder_new_feature]
# [SECTION: DEMO_ADDED_CONSTANTS]
APP_BUILD = "1.0.0"
APP_AUTHOR = "Test User"
# [END: SECTION: DEMO_ADDED_CONSTANTS]
# [END: SECTION: EXTENSION_POINTS]


# [FUNC: demo_run]
def demo_run(base_dir: Path) -> Dict[str, Any]:
    """
    Kleine demo die verschillende onderdelen gebruikt, voor integrale tests.
    """
    with Timer("demo_run"):
        cfg_path = base_dir / CONFIG_FILE
        cfg = load_config(cfg_path)
        cfg["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        save_config(cfg_path, cfg)

        g = Greeter.default()
        greeting = g.greet()
        shouted = Greeter.shout(greeting)

        kv = parse_kv_lines(["A=1", "B=  x", "# comment", "BAD LINE", "C=3"])
        processed = process_items(range(1, 10))
        net = simulated_network_call("https://example/fail-once")

        result = {
            "slug": slugify(" Hello World! "),
            "cfg_path": str(cfg_path),
            "greeting": greeting,
            "shouted": shouted,
            "kv": kv,
            "processed": processed,
            "net": net,
        }
        return result


# [END: FUNC: demo_run]


# [SECTION: MAIN]
if __name__ == "__main__":
    # [CHANGE: 2025-08-15] Eenvoudige main-run voor snelle tests
    base = Path(__file__).resolve().parent
    out = demo_run(base)
    print(json.dumps(out, indent=2, ensure_ascii=False))
# [END: SECTION: MAIN]
