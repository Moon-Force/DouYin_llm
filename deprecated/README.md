# Deprecated Files

This directory contains the old client-based collector path that existed before
the backend gained a built-in collector.

Current main path:

```text
tool/douyinLive-windows-amd64.exe
  -> backend/services/collector.py
  -> backend/app.py
  -> frontend/
```

Files kept here:

- `client.py`: legacy websocket-to-backend forwarder, no longer required.
- `debug_client.py`: optional raw websocket debugger.
- `config.py`: config used only by the legacy scripts in this folder.

Normal startup should use:

```powershell
.\start_all.ps1
```

or:

```powershell
.\start_backend_qwen.ps1
.\start_frontend.ps1
```
