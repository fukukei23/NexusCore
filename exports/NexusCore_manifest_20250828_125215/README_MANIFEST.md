# NexusCore Export Manifest

- Date: 20250828_125215
- Profile: gpt5-50
- Target: 49.5 MB
- Roots: C:\Users\USER\tools\NexusCore
- Emit ZIP: True / Emit Folder: True / Dry-run: False
- Estimated ZIP Size: 27.91 MB

## Suggested Entry Points / Registry (auto-detected)
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/_pytest/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/gradio/routes.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/gradio/sketch/run.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/httpx/_main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/huggingface_hub/_webhooks_server.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/isort/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/markdown_it/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/mypy/dmypy_server.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/mypy/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/mypy/semanal_main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/mypyc/test/test_run.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/beta/thread_create_and_run_params.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/beta/threads/run_create_params.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/evals/run_cancel_response.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/evals/run_create_params.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/evals/run_create_response.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/evals/run_list_response.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/openai/types/evals/run_retrieve_response.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/.venv/Lib/site-packages/typer/main.py`
- `C:/Users/USER/tools/NexusCore/exports/NexusCore_manifest_20250828_125215/included_source/src/nexuscore/core/orchestrator.py`

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