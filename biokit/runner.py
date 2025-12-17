from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from . import __version__
from .config import ConfigError, load_config, validate_config
from .plugins import ManifestError, Plugin


def generate_run_id() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}-{uuid4().hex[:8]}"


def compute_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_environment() -> Dict[str, Any]:
    packages = {}
    for name in ("typer", "PyYAML"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = "unknown"

    return {
        "python_version": platform.python_version(),
        "packages": packages,
        "biokit_version": __version__,
    }


def prepare_run_dir(plugin_name: str, run_id: str, base_dir: Path | None = None) -> Path:
    root = base_dir or Path(__file__).resolve().parent.parent / "results"
    run_dir = root / plugin_name / run_id
    for sub in ("logs", "reports", "tables"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    return run_dir


def collect_input_hashes(config: Dict[str, Any]) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    input_block = config.get("input", {})

    for key in ("counts_path", "sample_sheet", "gene_list_path"):
        if key in input_block:
            path = Path(input_block[key])
            hashes[key] = compute_file_hash(path)
    return hashes


def write_metadata(run_dir: Path, metadata_record: Dict[str, Any]) -> None:
    metadata_path = run_dir / "metadata.json"
    with metadata_path.open("w", encoding="utf-8") as handle:
        json.dump(metadata_record, handle, indent=2)


def write_log(run_dir: Path, content: str, *, append: bool = False) -> None:
    log_path = run_dir / "logs" / "run.log"
    mode = "a" if append else "w"
    with log_path.open(mode, encoding="utf-8") as handle:
        handle.write(content)


def _invoke_plugin_entrypoint(plugin: Plugin, run_dir: Path, config_json: Path) -> Dict[str, Any]:
    entrypoint = plugin.entrypoint
    if not entrypoint:
        return {"status": "skipped", "reason": "No entrypoint defined"}

    script_path = plugin.path / entrypoint
    if not script_path.exists():
        raise ManifestError(f"Entrypoint {script_path} declared in manifest but not found")

    cmd: list[str]
    if script_path.suffix.lower() == ".r":
        cmd = ["Rscript", str(script_path), str(config_json), str(run_dir)]
    elif script_path.suffix.lower() == ".py":
        cmd = ["python", str(script_path), str(config_json), str(run_dir)]
    else:
        return {"status": "skipped", "reason": f"Unsupported entrypoint type: {script_path.suffix}"}

    result = subprocess.run(cmd, capture_output=True, text=True)
    write_log(
        run_dir,
        f"\n\n[plugin entrypoint] Command: {' '.join(cmd)}\nReturn code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n",
        append=True,
    )

    status = "ok" if result.returncode == 0 else "error"
    payload: Dict[str, Any] = {"status": status, "returncode": result.returncode}
    if result.stdout:
        payload["stdout_preview"] = result.stdout[:2000]
    if result.stderr:
        payload["stderr_preview"] = result.stderr[:2000]
    return payload


def execute(plugin: Plugin, config_path: Path) -> Path:
    raw_config = load_config(config_path)
    config = validate_config(raw_config, plugin)

    run_id = generate_run_id()
    run_dir = prepare_run_dir(plugin.name, run_id)

    input_hashes = collect_input_hashes(config)
    config_json_path = run_dir / "config_resolved.json"
    with config_json_path.open("w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)

    metadata_record = {
        "plugin": {
            "name": plugin.name,
            "version": plugin.version,
            "description": plugin.description,
            "inputs": plugin.inputs,
        },
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "config": config,
        "input_hashes": input_hashes,
        "environment": snapshot_environment(),
    }

    entrypoint_status = _invoke_plugin_entrypoint(plugin, run_dir, config_json_path)
    metadata_record["entrypoint"] = entrypoint_status

    # Pick up optional R metadata if produced by the plugin
    r_metadata_path = run_dir / "metadata_r.json"
    if r_metadata_path.exists():
        try:
            metadata_record["r_session"] = json.loads(r_metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata_record["r_session"] = "unparseable metadata_r.json"
    else:
        metadata_record["r_session"] = "not provided"

    write_metadata(run_dir, metadata_record)

    if entrypoint_status.get("status") != "ok":
        reason = metadata_record.get("entrypoint", {}).get("reason")
        message = reason or metadata_record.get("entrypoint", {}).get(
            "stderr_preview", "Run completed without plugin entrypoint execution."
        )
        write_log(run_dir, str(message))

    # If plugin did not produce outputs, lay down placeholders to keep the contract.
    for path, text in [
        (run_dir / "tables" / "README.txt", "Tables generated by plugin. Replace with actual outputs."),
        (run_dir / "reports" / "README.txt", "Reports generated by plugin. Replace with actual outputs."),
    ]:
        if not path.exists():
            path.write_text(text, encoding="utf-8")

    return run_dir
