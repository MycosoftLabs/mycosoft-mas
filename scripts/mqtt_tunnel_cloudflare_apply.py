#!/usr/bin/env python3
"""
Set Cloudflare Tunnel ingress for MQTT and status hostnames.

- GETs current tunnel ingress, upserts:
  - mqtt.mycosoft.com -> http://<MQTT_BROKER_LAN_IP>:9001
  - mqtt-status.mycosoft.com -> http://localhost:3000
  then PUTs back.
- Upstream: http://<MQTT_BROKER_LAN_IP>:9001 (Mosquitto websockets; clients use wss:// on 443).

Requires: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID (e.g. from .credentials.local)

Env:
  MQTT_TUNNEL_ID       default bd385313-a44a-47ae-8f8a-581608118127 (mycosoft-tunnel)
  MQTT_BROKER_LAN_IP   default 192.168.0.196 (or MQTT_VM_GUEST_IP)
  MQTT_STATUS_UPSTREAM default http://localhost:3055
  CLOUDFLARE_ZONE_ID   optional, enables DNS upsert for mqtt-status.mycosoft.com

Date: 2026-04-08
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests


def _load_creds() -> None:
    for base in (Path(__file__).resolve().parent.parent, Path.cwd()):
        for name in (".credentials.local", ".env.local", ".env"):
            p = base / name
            if not p.exists():
                continue
            for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v


def main() -> int:
    _load_creds()
    account = (os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    token = (os.environ.get("CLOUDFLARE_API_TOKEN") or "").strip()
    tid = (os.environ.get("MQTT_TUNNEL_ID") or "bd385313-a44a-47ae-8f8a-581608118127").strip()
    broker = (
        os.environ.get("MQTT_BROKER_LAN_IP")
        or os.environ.get("MQTT_VM_GUEST_IP")
        or "192.168.0.196"
    ).strip()
    status_upstream = (os.environ.get("MQTT_STATUS_UPSTREAM") or "http://localhost:3055").strip()
    zone_id = (os.environ.get("CLOUDFLARE_ZONE_ID") or "").strip()

    if not account or not token:
        print("ERROR: CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN required", file=sys.stderr)
        return 1

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    cfg_url = f"https://api.cloudflare.com/client/v4/accounts/{account}/cfd_tunnel/{tid}/configurations"

    r = requests.get(cfg_url, headers=headers, timeout=60)
    if not r.ok:
        print(f"ERROR: GET tunnel config {r.status_code}: {r.text}", file=sys.stderr)
        return 1
    body = r.json()
    if not body.get("success"):
        print(f"ERROR: GET failed: {body}", file=sys.stderr)
        return 1

    result = body.get("result") or {}
    config = result.get("config") or {}
    ingress = list(config.get("ingress") or [])
    if not ingress:
        ingress = [{"service": "http_status:404"}]

    ws_upstream = f"http://{broker}:9001"
    mqtt_rule = {
        "hostname": "mqtt.mycosoft.com",
        "service": ws_upstream,
        "originRequest": {},
    }
    status_rule = {
        "hostname": "mqtt-status.mycosoft.com",
        "service": status_upstream,
        "originRequest": {},
    }

    mqtt_replaced = False
    status_replaced = False
    new_ingress: list[dict] = []
    for rule in ingress:
        hostname = (rule.get("hostname") or "").lower()
        if hostname == "mqtt.mycosoft.com":
            new_ingress.append(mqtt_rule)
            mqtt_replaced = True
        elif hostname == "mqtt-status.mycosoft.com":
            new_ingress.append(status_rule)
            status_replaced = True
        else:
            new_ingress.append(rule)

    if not mqtt_replaced or not status_replaced:
        catch: list[dict] = []
        named: list[dict] = []
        for rule in new_ingress:
            if rule.get("hostname"):
                named.append(rule)
            else:
                catch.append(rule)
        if not mqtt_replaced:
            named.append(mqtt_rule)
        if not status_replaced:
            named.append(status_rule)
        new_ingress = named + catch

    put_body = {"config": {"ingress": new_ingress}}
    r2 = requests.put(cfg_url, headers=headers, json=put_body, timeout=60)
    if not r2.ok:
        print(f"ERROR: PUT {r2.status_code}: {r2.text}", file=sys.stderr)
        return 1
    j2 = r2.json()
    if not j2.get("success"):
        print(f"ERROR: PUT failed: {j2}", file=sys.stderr)
        return 1

    print("OK: mqtt.mycosoft.com ->", ws_upstream)
    print(f"OK: mqtt-status.mycosoft.com -> {status_upstream}")
    print("Remote: wss://mqtt.mycosoft.com:443 - WebSocket path / (Mosquitto default); TLS at Cloudflare edge")
    print("LAN:    mqtt://%s:1883 (plain TCP; keep on trusted LAN only)" % broker)
    if zone_id:
        dns_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        dns_name = "mqtt-status.mycosoft.com"
        dns_value = f"{tid}.cfargotunnel.com"
        list_url = (
            f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            f"?type=CNAME&name={dns_name}"
        )
        r3 = requests.get(list_url, headers=dns_headers, timeout=30)
        if not r3.ok:
            print(f"WARN: DNS list failed {r3.status_code}: {r3.text}", file=sys.stderr)
            return 0
        j3 = r3.json()
        if not j3.get("success"):
            print(f"WARN: DNS list error: {j3}", file=sys.stderr)
            return 0
        result_records = j3.get("result") or []
        payload = {"type": "CNAME", "name": dns_name, "content": dns_value, "proxied": True, "ttl": 1}
        if result_records:
            rid = result_records[0].get("id")
            upd_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rid}"
            r4 = requests.put(upd_url, headers=dns_headers, json=payload, timeout=30)
            if r4.ok and (r4.json() or {}).get("success"):
                print(f"OK: DNS updated {dns_name} -> {dns_value} (proxied)")
            else:
                print(f"WARN: DNS update failed: {r4.status_code} {r4.text}", file=sys.stderr)
        else:
            create_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            r5 = requests.post(create_url, headers=dns_headers, json=payload, timeout=30)
            if r5.ok and (r5.json() or {}).get("success"):
                print(f"OK: DNS created {dns_name} -> {dns_value} (proxied)")
            else:
                print(f"WARN: DNS create failed: {r5.status_code} {r5.text}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
