"""Scan task executed by the RQ worker."""

import os
import re
import logging
import shutil
import subprocess
import tempfile

import httpx

logger = logging.getLogger(__name__)

WEB_API_URL = os.environ.get("WEB_API_URL", "http://web:8080/api/v1")
SCANNER_API_TOKEN = os.environ.get("SCANNER_API_TOKEN", "changeme")

# Regex for nmap verbose "Discovered open port" lines
# Example: "Discovered open port 80/tcp on 192.168.1.1"
_DISCOVERED_RE = re.compile(
    r"Discovered open port (\d+)/(tcp|udp) on (.+)"
)


def _api_headers() -> dict:
    return {"Authorization": f"Bearer {SCANNER_API_TOKEN}"}


def _update_job(job_id: str, payload: dict) -> None:
    """Post a status/results update back to the web API."""
    url = f"{WEB_API_URL}/internal/scans/{job_id}/results"
    resp = httpx.put(url, json=payload, headers=_api_headers(), timeout=30)
    resp.raise_for_status()


def _push_partial(job_id: str, results: list[dict]) -> None:
    """Push partial results (discovered ports) to the web API."""
    url = f"{WEB_API_URL}/internal/scans/{job_id}/partial"
    resp = httpx.post(url, json={"results": results}, headers=_api_headers(), timeout=30)
    resp.raise_for_status()


def _find_nmap() -> str:
    """Find the nmap binary path."""
    path = shutil.which("nmap")
    if not path:
        raise FileNotFoundError("nmap not found in PATH")
    return path


def _parse_xml_results(xml_path: str) -> tuple[list[dict], str]:
    """Parse the nmap XML output file for full results with service/version info."""
    import xml.etree.ElementTree as ET

    results = []
    raw_xml = ""

    try:
        with open(xml_path, "r", errors="replace") as f:
            raw_xml = f.read()
    except FileNotFoundError:
        return results, raw_xml

    if not raw_xml.strip():
        return results, raw_xml

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return results, raw_xml

    for host_el in root.findall("host"):
        addr_el = host_el.find("address")
        if addr_el is None:
            continue
        host = addr_el.get("addr", "")

        ports_el = host_el.find("ports")
        if ports_el is None:
            continue

        for port_el in ports_el.findall("port"):
            protocol = port_el.get("protocol", "tcp")
            port_num = int(port_el.get("portid", 0))

            state_el = port_el.find("state")
            state = state_el.get("state", "unknown") if state_el is not None else "unknown"

            service_el = port_el.find("service")
            service = None
            version = None
            if service_el is not None:
                service = service_el.get("name") or None
                ver_parts = []
                if service_el.get("product"):
                    ver_parts.append(service_el.get("product"))
                if service_el.get("version"):
                    ver_parts.append(service_el.get("version"))
                if service_el.get("extrainfo"):
                    ver_parts.append(service_el.get("extrainfo"))
                if ver_parts:
                    version = " ".join(ver_parts)

            results.append({
                "host": host,
                "port": port_num,
                "protocol": protocol,
                "state": state,
                "service": service,
                "version": version,
            })

    return results, raw_xml


def run_scan(job_id: str, target: str, nmap_args: str) -> None:
    """Run an nmap scan and report results back to the web API."""
    logger.info("Starting scan %s: target=%s args=%s", job_id, target, nmap_args)

    # Mark job as running
    _update_job(job_id, {"status": "running"})

    xml_file = None
    try:
        # Create temp file for XML output
        fd, xml_path = tempfile.mkstemp(suffix=".xml", prefix=f"nmap-{job_id}-")
        os.close(fd)
        xml_file = xml_path

        # Build nmap command: add -v for verbose discovery output, -oX for XML
        nmap_bin = _find_nmap()
        cmd = [nmap_bin] + nmap_args.split() + ["-v", "-oX", xml_path, target]
        logger.info("Running: %s", " ".join(cmd))

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Buffer for batching partial results
        partial_batch = []
        seen_ports = set()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            match = _DISCOVERED_RE.search(line)
            if match:
                port_num = int(match.group(1))
                protocol = match.group(2)
                host = match.group(3).strip()
                port_key = (host, port_num, protocol)

                if port_key not in seen_ports:
                    seen_ports.add(port_key)
                    partial_batch.append({
                        "host": host,
                        "port": port_num,
                        "protocol": protocol,
                        "state": "open",
                    })

                    # Push every discovery immediately
                    try:
                        _push_partial(job_id, partial_batch)
                        partial_batch = []
                    except Exception:
                        logger.warning("Failed to push partial results for %s", job_id)

        proc.wait()

        # Push any remaining partial results
        if partial_batch:
            try:
                _push_partial(job_id, partial_batch)
            except Exception:
                logger.warning("Failed to push final partial results for %s", job_id)

        if proc.returncode not in (0, 1):
            # nmap returns 1 for some non-fatal issues; anything else is a real error
            raise RuntimeError(f"nmap exited with code {proc.returncode}")

        # Parse full XML for complete results with service/version
        results, raw_xml = _parse_xml_results(xml_path)

        _update_job(job_id, {
            "status": "completed",
            "raw_xml": raw_xml,
            "results": results,
        })

        logger.info("Scan %s completed: %d results", job_id, len(results))

    except Exception as e:
        logger.exception("Scan %s failed", job_id)
        _update_job(job_id, {
            "status": "failed",
            "error_message": str(e),
        })
    finally:
        if xml_file and os.path.exists(xml_file):
            os.unlink(xml_file)
