#!/usr/bin/env python3
"""Small command sender for Tortue95's DGT3000-BLE-Gateway.

The Lucas-facing DLL calls this script for clock updates. Keeping BLE in Python
avoids shipping a large Windows BLE stack inside the DLL.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any

from bleak import BleakClient, BleakScanner


DEVICE_NAME = "DGT3000-Gateway"
BLE_TIMEOUT_SECONDS = 12.0
RECONNECT_DELAY_SECONDS = 3.0
LUCAS_INACTIVITY_STOP_SECONDS = 4.0
PROTOCOL_VERSION_CHAR_UUID = "73822f6e-edcd-44bb-974b-93ee97cb0001"
COMMAND_CHAR_UUID = "73822f6e-edcd-44bb-974b-93ee97cb0002"
EVENT_CHAR_UUID = "73822f6e-edcd-44bb-974b-93ee97cb0003"
STATUS_CHAR_UUID = "73822f6e-edcd-44bb-974b-93ee97cb0004"


class GatewayClient:
    def __init__(self, address: str | None = None, button_path: str | None = None) -> None:
        self.address = address
        self.button_path = button_path
        self.client: BleakClient | None = None
        self.pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self.lever_right_count = 0

    async def find_address(self) -> str:
        if self.address:
            return self.address
        devices = await asyncio.wait_for(BleakScanner.discover(timeout=8.0), timeout=BLE_TIMEOUT_SECONDS)
        for device in devices:
            if device.name and DEVICE_NAME in device.name:
                return str(device.address)
        raise RuntimeError("DGT3000-Gateway not found")

    async def connect(self, subscribe: bool = True) -> None:
        address = await self.find_address()
        self.client = BleakClient(address, timeout=BLE_TIMEOUT_SECONDS)
        await asyncio.wait_for(self.client.connect(), timeout=BLE_TIMEOUT_SECONDS)
        if subscribe:
            await asyncio.wait_for(self.client.start_notify(EVENT_CHAR_UUID, self._on_event), timeout=BLE_TIMEOUT_SECONDS)

    async def disconnect(self) -> None:
        if not self.client:
            return
        try:
            try:
                await asyncio.wait_for(self.client.stop_notify(EVENT_CHAR_UUID), timeout=5.0)
            except Exception:
                pass
        finally:
            await asyncio.wait_for(self.client.disconnect(), timeout=5.0)

    def _on_event(self, _sender: Any, data: bytearray) -> None:
        try:
            event = json.loads(data.decode("utf-8"))
        except Exception:
            return
        print(json.dumps(event), flush=True)
        data = event.get("data", {})
        if (
            event.get("type") == "buttonEvent"
            and data.get("button") == "lever_right"
            and not data.get("isRepeat")
        ):
            self.lever_right_count += 1
            if self.button_path:
                write_button_event(self.button_path)
        if event.get("type") == "command_response":
            command_id = event.get("id")
            future = self.pending.get(command_id)
            if future and not future.done():
                future.set_result(event)

    async def read_status(self) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("not connected")
        data = await asyncio.wait_for(self.client.read_gatt_char(STATUS_CHAR_UUID), timeout=BLE_TIMEOUT_SECONDS)
        return json.loads(data.decode("utf-8"))

    async def protocol_version(self) -> str:
        if not self.client:
            raise RuntimeError("not connected")
        data = await asyncio.wait_for(self.client.read_gatt_char(PROTOCOL_VERSION_CHAR_UUID), timeout=BLE_TIMEOUT_SECONDS)
        return data.decode("utf-8")

    async def command(self, name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("not connected")
        command_id = str(uuid.uuid4())[:8]
        payload: dict[str, Any] = {"command": name, "id": command_id}
        if params is not None:
            payload["params"] = params
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self.pending[command_id] = future
        await asyncio.wait_for(
            self.client.write_gatt_char(COMMAND_CHAR_UUID, json.dumps(payload).encode("utf-8")),
            timeout=BLE_TIMEOUT_SECONDS,
        )
        try:
            return await asyncio.wait_for(future, timeout=5.0)
        finally:
            self.pending.pop(command_id, None)


async def run_once(raw: str, address: str | None, keep_alive: bool = False) -> None:
    request = json.loads(raw)
    client = GatewayClient(address)
    await client.connect(subscribe=not request.get("status"))
    try:
        if request.get("status"):
            print(json.dumps(await client.read_status()), flush=True)
            return
        if request.get("setTime"):
            try:
                await client.command("endDisplay")
            except Exception as exc:
                print(json.dumps({"warning": f"initial endDisplay failed: {exc}"}), flush=True)
            response = await client.command("setTime", request["params"])
            print(json.dumps(response), flush=True)
            try:
                time_response = await client.command("getTime")
                print(json.dumps(time_response), flush=True)
            except Exception as exc:
                print(json.dumps({"warning": f"getTime failed: {exc}"}), flush=True)
            try:
                end_response = await client.command("endDisplay")
                print(json.dumps(end_response), flush=True)
            except Exception as exc:
                print(json.dumps({"warning": f"final endDisplay failed: {exc}"}), flush=True)
            if keep_alive:
                while True:
                    await asyncio.sleep(3600)
            return
        if request.get("stop"):
            print(json.dumps(await client.command("stop")), flush=True)
            return
        raise RuntimeError(f"unknown request: {request}")
    finally:
        await client.disconnect()


async def monitor(address: str | None) -> None:
    client = GatewayClient(address)
    await client.connect()
    try:
        print(json.dumps({"protocolVersion": await client.protocol_version()}), flush=True)
        print(json.dumps(await client.read_status()), flush=True)
        while True:
            await asyncio.sleep(3600)
    finally:
        await client.disconnect()


def clock_text_from_request(request: dict[str, Any]) -> str:
    params = request.get("params", {})
    return clock_text_from_seconds(
        seconds_from_params(params, "left"),
        seconds_from_params(params, "right"),
    )


def seconds_from_params(params: dict[str, Any], prefix: str) -> int:
    return (
        int(params.get(prefix + "Hours", 0)) * 3600
        + int(params.get(prefix + "Minutes", 0)) * 60
        + int(params.get(prefix + "Seconds", 0))
    )


def clock_text_from_seconds(left_seconds: int, right_seconds: int) -> str:
    left_seconds = max(0, int(left_seconds))
    right_seconds = max(0, int(right_seconds))
    left_hours, left_remainder = divmod(left_seconds, 3600)
    right_hours, right_remainder = divmod(right_seconds, 3600)
    left_minutes, left_secs = divmod(left_remainder, 60)
    right_minutes, right_secs = divmod(right_remainder, 60)

    if left_hours or right_hours:
        left = f"{left_hours}{left_minutes:02d}".rjust(6)
        right = f"{right_hours}{right_minutes:02d}".rjust(5)
    else:
        left = f"{left_minutes:02d}{left_secs:02d}".rjust(6)
        right = f"{right_minutes:02d}{right_secs:02d}".rjust(5)
    return (left + right)[:11]


class NativeClock:
    def __init__(self) -> None:
        self.initialized = False
        self.left = 0
        self.right = 0
        self.raw_left: int | None = None
        self.raw_right: int | None = None
        self.active: str | None = None
        self.last_switch: str | None = None
        self.last_sent: tuple[int, int, str | None] | None = None
        self.display_ended = False

    def update_from_lucas(self, request: dict[str, Any]) -> bool:
        params = request.get("params", {})
        new_left = seconds_from_params(params, "left")
        new_right = seconds_from_params(params, "right")
        human_side = request.get("humanSide")

        if not self.initialized:
            self.left = new_left
            self.right = new_right
            self.active = self.initial_active(new_left, new_right, human_side)
            self.last_switch = "clock" if self.active else None
            self.initialized = True
            self.raw_left = new_left
            self.raw_right = new_right
            return True

        old_active = self.active
        left_delta = new_left - (self.raw_left if self.raw_left is not None else new_left)
        right_delta = new_right - (self.raw_right if self.raw_right is not None else new_right)
        dirty = False

        if self.active is None:
            if left_delta < 0 and right_delta >= 0:
                self.active = "left"
            elif right_delta < 0 and left_delta >= 0:
                self.active = "right"
            else:
                self.active = self.initial_active(new_left, new_right, human_side)
            if self.active is not None:
                self.last_switch = "clock"
                dirty = True

        if new_left != self.left:
            self.left = new_left
            dirty = True
        if new_right != self.right:
            self.right = new_right
            dirty = True

        self.raw_left = new_left
        self.raw_right = new_right
        return dirty or self.active != old_active

    def engine_position(self) -> bool:
        if not self.initialized:
            return False
        if self.active != "right":
            self.active = "right"
            self.last_switch = "engine_position"
            return True
        return False

    def human_clock_pressed(self) -> bool:
        if not self.initialized:
            return False
        if self.active != "left":
            self.active = "left"
            self.last_switch = "lever_right"
            return True
        return False

    def stop_running(self) -> bool:
        if not self.initialized or self.active is None:
            return False
        self.active = None
        self.last_switch = "inactivity_stop"
        return True

    def update_from_gateway_time(self, result: dict[str, Any]) -> None:
        left = (
            int(result.get("leftHours", 0)) * 3600
            + int(result.get("leftMinutes", 0)) * 60
            + int(result.get("leftSeconds", 0))
        )
        right = (
            int(result.get("rightHours", 0)) * 3600
            + int(result.get("rightMinutes", 0)) * 60
            + int(result.get("rightSeconds", 0))
        )
        if left == 0 and right == 0 and (self.left > 0 or self.right > 0):
            return
        self.left = left
        self.right = right

    @staticmethod
    def infer_initial_active(left: int, right: int) -> str | None:
        if left and right:
            if left < right:
                return "left"
            if right < left:
                return "right"
        return None

    @classmethod
    def initial_active(cls, left: int, right: int, human_side: Any) -> str | None:
        if human_side == "black":
            return "left"
        if human_side == "white":
            return "right"
        return cls.infer_initial_active(left, right)

    def command_params(self) -> dict[str, int]:
        left_mode = 1 if self.active == "left" else 0
        right_mode = 1 if self.active == "right" else 0
        params: dict[str, int] = {}
        params.update(time_fields(self.left, "left", left_mode))
        params.update(time_fields(self.right, "right", right_mode))
        return params

    def needs_send(self) -> bool:
        current = (self.left, self.right, self.active)
        return current != self.last_sent

    def mark_sent(self) -> None:
        self.last_sent = (self.left, self.right, self.active)


def time_fields(seconds: int, prefix: str, mode: int) -> dict[str, int]:
    seconds = max(0, int(seconds))
    return {
        prefix + "Mode": mode,
        prefix + "Hours": seconds // 3600,
        prefix + "Minutes": (seconds // 60) % 60,
        prefix + "Seconds": seconds % 60,
    }


async def watch_clock_file(path: str, address: str | None, button_path: str | None) -> None:
    last_payload = ""
    while True:
        client = GatewayClient(address, button_path)
        clock = NativeClock()
        last_lever_right_count = 0
        last_lucas_update = time.monotonic()
        stopped_for_inactivity = False
        try:
            await client.connect()
            try:
                print(json.dumps({"protocolVersion": await client.protocol_version()}), flush=True)
                print(json.dumps(await client.read_status()), flush=True)
            except Exception as exc:
                print(json.dumps({"warning": f"initial status read failed: {exc}"}), flush=True)

            # Replay Lucas' last clock state after each connect/reconnect.
            last_payload = ""

            while client.client and client.client.is_connected:
                try:
                    if client.lever_right_count != last_lever_right_count:
                        last_lever_right_count = client.lever_right_count
                        try:
                            time_response = await client.command("getTime")
                            if time_response.get("status") == "success":
                                clock.update_from_gateway_time(time_response.get("result", {}))
                        except Exception as exc:
                            print(json.dumps({"warning": f"getTime on lever_right failed: {exc}"}), flush=True)
                        changed = clock.human_clock_pressed()
                        if changed and clock.needs_send():
                            params = clock.command_params()
                            response = await client.command("setTime", params)
                            clock.mark_sent()
                            stopped_for_inactivity = False
                            print(json.dumps({"nativeClock": {"left": clock.left, "right": clock.right, "active": clock.active}, "event": "lever_right", "params": params, "response": response}), flush=True)

                    raw = read_text_if_exists(path)
                    if raw and raw != last_payload:
                        request = json.loads(raw)
                        event = request.get("event", "clock")
                        changed = clock.engine_position() if event == "engine_position" else clock.update_from_lucas(request)
                        last_lucas_update = time.monotonic()
                        stopped_for_inactivity = False
                        if changed and clock.needs_send():
                            if not clock.display_ended:
                                try:
                                    await client.command("endDisplay")
                                except Exception as exc:
                                    print(json.dumps({"warning": f"endDisplay before native clock failed: {exc}"}), flush=True)
                                clock.display_ended = True
                            params = clock.command_params()
                            response = await client.command("setTime", params)
                            clock.mark_sent()
                            print(json.dumps({"nativeClock": {"left": clock.left, "right": clock.right, "active": clock.active}, "event": event, "rawWhite": request.get("rawWhite"), "rawBlack": request.get("rawBlack"), "params": params, "response": response}), flush=True)
                        last_payload = raw

                    if (
                        clock.initialized
                        and clock.active is not None
                        and not stopped_for_inactivity
                        and time.monotonic() - last_lucas_update >= LUCAS_INACTIVITY_STOP_SECONDS
                    ):
                        try:
                            time_response = await client.command("getTime")
                            if time_response.get("status") == "success":
                                clock.update_from_gateway_time(time_response.get("result", {}))
                        except Exception as exc:
                            print(json.dumps({"warning": f"getTime on inactivity stop failed: {exc}"}), flush=True)
                        if clock.stop_running() and clock.needs_send():
                            params = clock.command_params()
                            response = await client.command("setTime", params)
                            clock.mark_sent()
                            stopped_for_inactivity = True
                            print(json.dumps({"nativeClock": {"left": clock.left, "right": clock.right, "active": clock.active}, "event": "inactivity_stop", "params": params, "response": response}), flush=True)
                except Exception as exc:
                    print(json.dumps({"warning": f"clock watch update failed: {exc}"}), flush=True)
                    if not client.client or not client.client.is_connected:
                        break
                await asyncio.sleep(0.2)
        except Exception as exc:
            print(json.dumps({"warning": f"BLE connection failed, retrying: {exc}"}), flush=True)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
        await asyncio.sleep(RECONNECT_DELAY_SECONDS)


def read_text_if_exists(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


def write_button_event(path: str) -> None:
    tmp = path + ".tmp"
    payload = {"button": "lever_right", "sequence": int(time.time() * 1000), "timestamp": time.time()}
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address")
    parser.add_argument("--once", help="JSON request to execute once")
    parser.add_argument("--once-file", help="File containing a JSON request to execute once")
    parser.add_argument("--keep-alive", action="store_true", help="Stay connected after executing --once/--once-file")
    parser.add_argument("--watch-clock-file", help="Keep BLE connected and mirror Lucas clock text from this JSON file")
    parser.add_argument("--button-file", help="Write DGT3000 button events to this JSON file")
    parser.add_argument("--monitor", action="store_true", help="Print gateway events forever")
    args = parser.parse_args()

    try:
        if args.watch_clock_file:
            asyncio.run(watch_clock_file(args.watch_clock_file, args.address, args.button_file))
        elif args.once or args.once_file:
            raw = args.once
            if args.once_file:
                with open(args.once_file, "r", encoding="utf-8") as handle:
                    raw = handle.read()
            asyncio.run(run_once(raw or "{}", args.address, args.keep_alive))
        else:
            asyncio.run(monitor(args.address))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
