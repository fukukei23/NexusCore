# NexusCore Export Manifest

- Date: 20250829_162420
- Profile: gemini-10
- Target: 9.5 MB
- Roots: C:\Users\USER\tools\NexusCore
- Emit ZIP: True / Emit Folder: True / Dry-run: False
- Estimated ZIP Size: 9.46 MB

## Suggested Entry Points / Registry (auto-detected)
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/_pytest/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/gradio/routes.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/gradio/sketch/run.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/isort/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/mypy/dmypy_server.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/mypy/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/mypy/semanal_main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250829_162420/included_source/.venv/Lib/site-packages/mypyc/test/test_run.py`

## How to Use
1. Upload the generated ZIP to the target model (Gemini/GPT-5) as needed.
2. For Gemini packs, keep under ~10MB; for GPT-5 packs, under ~50MB.
3. Web UI: `python tools/nexus_export_ui.py`.
4. CLI examples:
   - Gemini: `python tools/code_export_gemini_fixed.py --profile gemini-10 --emit-zip --emit-folder`
   - GPT-5 : `python tools/code_export_gemini_fixed.py --profile gpt5-50 --emit-zip --emit-folder`

## Notes
- Windows long path is mitigated by flattening deep paths via hashed middle segments.
- Logs are written to `logs/` and mirrored into this manifest directory.