# CalDigit Dock USB Diagnostic — Feb 24, 2026

**Status:** Diagnostic complete  
**Device:** CalDigit TS4 (Thunderbolt 4 Station)  
**Issue:** None of the USBs on the dock are working.

---

## 1. What Was Found

### Dock presence
- **CalDigit TS4** is visible to Windows as:
  - `USB4 Router (1.0), CalDigit. Inc. - TS4` (two nodes)
- Both show **Status: Unknown** (not OK), so the dock is only partially recognized.

### USB enumeration failures
- **Device Descriptor Request Failed** (Windows cannot read the device):
  - `USB\VID_0000&PID_0002\9&13BF103E&0&2`
  - `USB\VID_0000&PID_0002\9&13BF103E&0&4`
  - `USB\VID_0000&PID_0002\9&A6D8FA&0&4` — **Status: Error**
- VID_0000&PID_0002 usually means the host could not get a valid descriptor from the device (failed port or device behind the dock).

### Other system errors (unrelated to dock)
- PCI Encryption/Decryption Controller, AMD ACPI, PCI devices, WD SES Device, Microsoft Basic Display Adapter, MX Brio (camera) also show Error. These are separate from the CalDigit USB issue.

---

## 2. Likely Cause

- The dock’s **USB ports depend on PCIe over Thunderbolt/USB4**. If that path isn’t enabled or the link is unstable, the downstream USB ports won’t enumerate and you get “Device Descriptor Request Failed.”
- CalDigit’s own support (e.g. for TS5 Plus on Windows 11) states: USB-A and rear USB-C data ports **require Thunderbolt 4/5 or USB4** and **PCIe over Thunderbolt/USB4**; without it, those USB ports (and often 10GbE) do not work.

---

## 3. Recommended Actions (in order)

### A. BIOS
1. Reboot and enter BIOS (e.g. Del/F2/F12, depends on motherboard).
2. Find **Thunderbolt** or **USB4** settings.
3. Ensure **PCIe over Thunderbolt/USB4** (or equivalent) is **Enabled**.
4. Save and exit.

### B. Windows and drivers
1. **Windows Update** — Install all optional and driver updates.
2. **Thunderbolt / USB4** — In Device Manager, under “System devices” or “Thunderbolt,” update drivers for Thunderbolt/USB4 host controller (Update driver → Search automatically). Or install the latest from your PC/laptop vendor (e.g. ASUS/AMD support page).
3. **CalDigit 10Gb Ethernet driver** (if you use dock Ethernet):  
   [CalDigit TS5 Plus / Connect 10G Ethernet driver](https://www.caldigit.com/caldigit-ts5-plus-and-connect-10g-ethernet-driver-update-procedure/) — TS4 may use same or similar; check CalDigit downloads for “TS4”.

### C. Physical and power
1. Use the **original Thunderbolt/USB4 cable** and plug into a port that is **Thunderbolt 4 or USB4** (not plain USB 3.x).
2. **Power cycle:** Unplug dock from wall and from the PC for 30+ seconds, then reconnect.
3. Try **another Thunderbolt/USB4 port** on the PC if available.

### D. Device Manager cleanup (optional)
1. Open **Device Manager**.
2. **View → Show hidden devices**.
3. Under **Universal Serial Bus devices**, find **Unknown USB Device (Device Descriptor Request Failed)**.
4. Right‑click → **Uninstall device** (check “Attempt to remove driver” if offered).
5. Unplug the CalDigit dock, wait 10 seconds, plug it back in and let Windows re-enumerate.

### E. Power management (if devices drop after a while)
1. Device Manager → **Universal Serial Bus controllers**.
2. For each **USB Root Hub** / **USB Host Controller** → **Properties → Power Management**.
3. Uncheck **“Allow the computer to turn off this device to save power.”**

---

## 4. If It Still Fails

- **Firmware:** Check [CalDigit Support](https://www.caldigit.com/support/) for **TS4** firmware and apply if available.
- **Contact CalDigit:** Have **product name (TS4), serial number, and Windows version** ready.  
  Americas: [Support@CalDigit.com](mailto:Support@CalDigit.com), +1 (714) 519-3387.

---

## 5. Commands used for this diagnostic

```powershell
Get-PnpDevice -Class USB | Select-Object Status, Class, FriendlyName, InstanceId
Get-PnpDevice | Where-Object { $_.Status -eq 'Error' }
```

---

**Doc:** `docs/CALDIGIT_DOCK_USB_DIAGNOSTIC_FEB24_2026.md`
