"""Scan task executed by the RQ worker."""

import os
import logging

import httpx
import nmap

logger = logging.getLogger(__name__)

WEB_API_URL = os.environ.get("WEB_API_URL", "http://web:8080/api/v1")
SCANNER_API_TOKEN = os.environ.get("SCANNER_API_TOKEN", "changeme")


def _api_headers() -> dict:
    return {"Authorization": f"Bearer {SCANNER_API_TOKEN}"}


def _update_job(job_id: str, payload: dict) -> None:
    """Post a status/results update back to the web API."""
    url = f"{WEB_API_URL}/internal/scans/{job_id}/results"
    resp = httpx.put(url, json=payload, headers=_api_headers(), timeout=30)
    resp.raise_for_status()


def run_scan(job_id: str, target: str, nmap_args: str) -> None:
    """Run an nmap scan and report results back to the web API."""
    logger.info("Starting scan %s: target=%s args=%s", job_id, target, nmap_args)

    # Mark job as running
    _update_job(job_id, {"status": "running"})

    try:
        scanner = nmap.PortScanner()
        scanner.scan(hosts=target, arguments=nmap_args)

        # Collect structured results
        results = []
        for host in scanner.all_hosts():
            for proto in scanner[host].all_protocols():
                ports = scanner[host][proto].keys()
                for port in ports:
                    port_info = scanner[host][proto][port]
                    results.append({
                        "host": host,
                        "port": port,
                        "protocol": proto,
                        "state": port_info.get("state", "unknown"),
                        "service": port_info.get("name") or None,
                        "version": port_info.get("version") or None,
                    })

        # Get raw XML output
        raw_xml_out = scanner.get_nmap_last_output()
        raw_xml = raw_xml_out.decode("utf-8", errors="replace") if isinstance(raw_xml_out, bytes) else raw_xml_out

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
