# 🗺️ Code & Structure Manifest
これはプロジェクト全体の構造と主要コンポーネントの概要を示す設計図です。

## 🌳 プロジェクト全体ディレクトリ構造
`[INCLUDED]` は本パックに含まれる主要ファイル。
```
NexusCore/
├── .env.template [INCLUDED]
├── .github
│   └── workflows
│       └── ci.yml
├── .nexus_context.json
├── .python-version
├── LICENSE
├── OpenCodeInterpreter.code-workspace
├── README.md
├── README_old.md
├── _extract_deps.py [INCLUDED]
├── app
│   ├── __init__.py [INCLUDED]
│   ├── celery_worker.py [INCLUDED]
│   ├── extensions.py [INCLUDED]
│   └── routes.py [INCLUDED]
├── archive
│   ├── ai_assistant.py
│   ├── app.py [INCLUDED]
│   └── git_manager.py
├── config
│   ├── env_loader.py
│   └── policy_rules.json
├── data
│   ├── cost_table.json
│   ├── knowledge_bases
│   │   └── fkb_local.json
│   ├── nexus_cost_table.json
│   └── usage
│       └── usage_202508.jsonl
├── data_collection
│   ├── Local-Code-Interpreter
│   │   ├── LICENSE
│   │   ├── README.md
│   │   ├── README_CN.md
│   │   ├── config_example
│   │   │   ├── config.azure.example.json
│   │   │   └── config.example.json
│   │   ├── example_img
│   │   │   ├── 1.jpg
│   │   │   ├── 2.jpg
│   │   │   ├── 3.jpg
│   │   │   ├── 4.jpg
│   │   │   ├── 5.jpg
│   │   │   ├── 6.jpg
│   │   │   ├── save_to_notebook_demo.gif
│   │   │   └── vision_example.jpg
│   │   ├── requirements.txt
│   │   ├── requirements_full.txt
│   │   └── src
│   │       ├── bot_backend.py
│   │       ├── cli.py
│   │       ├── functional.py
│   │       ├── jupyter_backend.py
│   │       ├── notebook_serializer.py
│   │       ├── response_parser.py
│   │       ├── tools.py
│   │       └── web_ui.py
│   └── README.md
├── database
│   ├── knowledge_base.py
│   └── state_manager.py
├── dev_tools
│   └── test_linter_ast.py
├── docker-compose.yml
├── fix_imports.py [INCLUDED]
├── fkb_local.json
├── gradio_app.py [INCLUDED]
├── healing_sandbox
│   ├── app
│   │   ├── __init__.py
│   │   └── main.py [INCLUDED]
│   ├── fkb_local.json
│   ├── sandbox_runner.py
│   ├── src
│   │   ├── __init__.py
│   │   └── agents
│   │       ├── __init__.py
│   │       ├── base_agent.py
│   │       ├── debugger_agent.py
│   │       ├── orchestrator.py [INCLUDED]
│   │       └── patch_applier.py
│   └── tests
│       ├── __init__.py
│       └── test_main.py
├── how mainREADME.md  Set-Clipboard
├── install-pyenv-win.ps1
├── launch.bat
├── launch_all.ps1
├── launch_dev.ps1
├── main_cli.py [INCLUDED]
├── my-crm-app
│   ├── app
│   │   ├── __init__.py [INCLUDED]
│   │   ├── main.py [INCLUDED]
│   │   ├── models.py [INCLUDED]
│   │   ├── routes.py [INCLUDED]
│   │   ├── static
│   │   │   └── style.css
│   │   ├── templates
│   │   │   └── index.html
│   │   └── views.py [INCLUDED]
│   ├── config.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── run.py
│   └── tests
│       ├── __init__.py
│       └── test_main.py
├── nexus_os_kernel.py [INCLUDED]
├── old_tool
│   ├── __init__.py
│   └── core.py
├── output
│   ├── NexusCore_bundle_20250806_224858.zip
│   ├── NexusCore_combined_20250801_130327.txt
│   ├── NexusCore_combined_20250806_224858.txt
│   ├── NexusCore_structure_20250801_130327.json
│   ├── NexusCore_structure_20250801_130327.md
│   ├── NexusCore_structure_20250806_224858.json
│   └── NexusCore_structure_20250806_224858.md
├── policy_test_sandbox
│   ├── app
│   │   ├── __init__.py
│   │   └── main.py
│   └── tests
│       ├── __init__.py
│       └── test_main.py
├── project_chronicle.jsonl
├── project_structure.json
├── project_structure_and_code_export.py [INCLUDED]
├── project_structure_export
│   └── NexusCore_folder_structure.txt
├── pyproject.toml [INCLUDED]
├── pytest.ini
├── quality_gate_test_sandbox
│   ├── .nexus_logs
│   │   └── fkb_suggestions_rejected.jsonl
│   ├── app
│   │   └── calculator.py [INCLUDED]
│   ├── config
│   │   └── policy_rules.json
│   ├── fkb_local.json
│   ├── pyproject.toml
│   └── tests
│       └── test_calculator.py
├── quality_loop_test_sandbox
│   ├── .nexus_logs
│   │   ├── run_data.jsonl
│   │   └── run_log.md
│   ├── app
│   │   ├── __init__.py
│   │   └── main.py [INCLUDED]
│   └── tests
│       ├── __init__.py
│       └── test_main.py
├── requirements.dev.lock.txt
├── requirements.lock.txt
├── requirements.txt [INCLUDED]
├── run_policy_check_test.py [INCLUDED]
├── run_quality_gate_test.py [INCLUDED]
├── run_quality_loop_test.py [INCLUDED]
├── run_self_healing.py [INCLUDED]
├── run_tests.py [INCLUDED]
├── run_vc_scout.py [INCLUDED]
├── sandbox_repo
│   ├── app
│   │   └── main.py [INCLUDED]
│   ├── pyproject.toml
│   └── tests
│       ├── __init__.py
│       └── test_main.py
├── scripts
│   ├── Get-WeatherAndAskGPT.ps1
│   └── migrate_fkb.py
├── simple_context_agent.py [INCLUDED]
├── src
│   ├── LICENSE
│   ├── README.md
│   ├── README_ja.md
│   ├── __init__.py [INCLUDED]
│   ├── assets
│   │   ├── assistant.pic.jpg
│   │   └── user.pic.jpg
│   ├── dev_tools
│   │   ├── test_manager.py [INCLUDED]
│   │   └── test_openai_connection.py [INCLUDED]
│   ├── env_sorted.txt
│   ├── file_creator.py [INCLUDED]
│   ├── folder_structure.txt
│   ├── history_20250713_055827.json
│   ├── history_20250713_064458.json
│   ├── history_manager.py [INCLUDED]
│   ├── lock_sorted.txt
│   ├── logo.png
│   ├── main_ui.py [INCLUDED]
│   ├── nexuscore
│   │   ├── __init__.py
│   │   ├── agents
│   │   │   ├── __init__.py
│   │   │   ├── architect_agent.py
│   │   │   ├── base_agent.py [INCLUDED]
│   │   │   ├── coder_agent.py
│   │   │   ├── constitutional_council_agent.py
│   │   │   ├── context_agent.py [INCLUDED]
│   │   │   ├── context_analyzer.py [INCLUDED]
│   │   │   ├── debugger_agent.py [INCLUDED]
│   │   │   ├── guardian_agent.py
│   │   │   ├── knowledge_curator_agent.py
│   │   │   ├── patch_applier.py
│   │   │   ├── planner_agent.py [INCLUDED]
│   │   │   ├── policy_agent.py
│   │   │   ├── policy_interface.py
│   │   │   ├── postmortem_agent.py
│   │   │   ├── requirement_agent.py [INCLUDED]
│   │   │   └── tester_agent.py
│   │   ├── analyzer
│   │   │   ├── graph_builder.py
│   │   │   └── unified_analyzer.py
│   │   ├── api
│   │   │   ├── __init__.py
│   │   │   └── server.py
│   │   ├── audio
│   │   │   ├── __init__.py
│   │   │   └── voice_to_text.py
│   │   ├── code_interpreter
│   │   │   ├── BaseCodeInterpreter.py
│   │   │   ├── JupyterClient.py
│   │   │   ├── OpenCodeInterpreter.py
│   │   │   ├── __init__.py
│   │   │   ├── gradio_test_runner.py
│   │   │   ├── repair_module.py
│   │   │   └── sandbox_runner.py
│   │   ├── config
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── generate_secrets.py
│   │   ├── core
│   │   │   ├── __init__.py
│   │   │   └── orchestrator.py
│   │   ├── gradio_app
│   │   │   ├── .nexus_context.json
│   │   │   ├── __init__.py
│   │   │   ├── app_ui.py
│   │   │   ├── auto_revision_runner.py
│   │   │   ├── interactive_generator.py
│   │   │   ├── revision_loop.py
│   │   │   ├── revision_tab.py
│   │   │   ├── sandbox_output
│   │   │   │   ├── sample.py
│   │   │   │   └── test_sample.py
│   │   │   └── streamlit_migrated_tab.py [INCLUDED]
│   │   ├── llm
│   │   │   ├── __init__.py
│   │   │   └── llm_router.py [INCLUDED]
│   │   ├── modules
│   │   │   ├── __init__.py
│   │   │   ├── chat_handler.py
│   │   │   ├── code_generator.py
│   │   │   ├── diff_viewer.py
│   │   │   ├── history_viewer.py
│   │   │   ├── tester.py
│   │   │   └── whisper_handler.py
│   │   ├── npe
│   │   │   ├── budget.py
│   │   │   ├── engine.py [INCLUDED]
│   │   │   ├── logger.py
│   │   │   └── policies.py
│   │   ├── utils
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── cleaner.py
│   │   │   ├── code_analyzer.py
│   │   │   ├── const.py
│   │   │   ├── diff_tools.py
│   │   │   ├── file_utils.py
│   │   │   ├── json_sanitizer.py
│   │   │   ├── log_monitor.py
│   │   │   ├── templates
│   │   │   │   └── ai_repair.html
│   │   │   ├── test_generator.py
│   │   │   ├── test_utils.py
│   │   │   ├── tree_sitter_checker.py
│   │   │   ├── vcs.py
│   │   │   └── zip_output.py
│   │   ├── ventures
│   │   │   └── vc_agent.py
│   │   └── workflows
│   │       └── multi_llm_review.py [INCLUDED]
│   ├── nexuscore.egg-info
│   │   ├── PKG-INFO
│   │   ├── SOURCES.txt
│   │   ├── dependency_links.txt
│   │   ├── requires.txt
│   │   └── top_level.txt
│   ├── opencodeinterpreter_webui.py [INCLUDED]
│   ├── project_structure.json
│   ├── project_structure.md
│   ├── pytest.ini
│   ├── realtime_whisper.py [INCLUDED]
│   ├── requirements.txt
│   ├── requirements_lock.tx
│   ├── requirements_lock.txt
│   ├── requirements_soft.txt
│   ├── sandbox_executor.py [INCLUDED]
│   ├── sandbox_logs
│   │   ├── repair_20250713_082119_fixed.py [INCLUDED]
│   │   ├── repair_20250713_082119_original.py [INCLUDED]
│   │   ├── repair_20250713_082119_traceback.txt
│   │   ├── repair_20250713_114519_fixed.py [INCLUDED]
│   │   ├── repair_20250713_114519_original.py
│   │   ├── repair_20250713_114519_traceback.txt
│   │   ├── repair_20250713_114534_fixed.py [INCLUDED]
│   │   ├── repair_20250713_114534_original.py [INCLUDED]
│   │   ├── repair_20250713_114534_traceback.txt
│   │   ├── repair_20250713_114552_fixed.py [INCLUDED]
│   │   ├── repair_20250713_114552_original.py [INCLUDED]
│   │   ├── repair_20250713_114552_traceback.txt
│   │   ├── repair_20250713_121010_fixed.py [INCLUDED]
│   │   ├── repair_20250713_121010_original.py
│   │   ├── repair_20250713_121010_traceback.txt
│   │   ├── repair_20250713_121031_fixed.py [INCLUDED]
│   │   ├── repair_20250713_121031_original.py [INCLUDED]
│   │   ├── repair_20250713_121031_traceback.txt
│   │   ├── repair_20250713_124402_fixed.py [INCLUDED]
│   │   ├── repair_20250713_124402_original.py
│   │   ├── repair_20250713_124402_traceback.txt
│   │   ├── repair_20250713_124414_fixed.py [INCLUDED]
│   │   ├── repair_20250713_124414_original.py [INCLUDED]
│   │   ├── repair_20250713_124414_traceback.txt
│   │   ├── repair_20250713_124433_fixed.py [INCLUDED]
│   │   ├── repair_20250713_124433_original.py [INCLUDED]
│   │   ├── repair_20250713_124433_traceback.txt
│   │   ├── repair_20250713_125710_fixed.py [INCLUDED]
│   │   ├── repair_20250713_125710_original.py
│   │   ├── repair_20250713_125710_traceback.txt
│   │   ├── repair_20250713_125723_fixed.py [INCLUDED]
│   │   ├── repair_20250713_125723_original.py [INCLUDED]
│   │   ├── repair_20250713_125723_traceback.txt
│   │   ├── repair_20250713_125733_fixed.py [INCLUDED]
│   │   ├── repair_20250713_125733_original.py [INCLUDED]
│   │   ├── repair_20250713_125733_traceback.txt
│   │   ├── repair_20250713_131833_fixed.py [INCLUDED]
│   │   ├── repair_20250713_131833_original.py
│   │   ├── repair_20250713_131833_traceback.txt
│   │   ├── repair_20250713_131843_fixed.py [INCLUDED]
│   │   ├── repair_20250713_131843_original.py [INCLUDED]
│   │   ├── repair_20250713_131843_traceback.txt
│   │   ├── repair_20250713_131857_fixed.py [INCLUDED]
│   │   ├── repair_20250713_131857_original.py [INCLUDED]
│   │   ├── repair_20250713_131857_traceback.txt
│   │   ├── repair_20250713_132959_fixed.py [INCLUDED]
│   │   ├── repair_20250713_132959_original.py [INCLUDED]
│   │   ├── repair_20250713_132959_traceback.txt
│   │   ├── repair_20250713_133018_fixed.py [INCLUDED]
│   │   ├── repair_20250713_133018_original.py [INCLUDED]
│   │   ├── repair_20250713_133018_traceback.txt
│   │   ├── repair_20250713_133036_fixed.py [INCLUDED]
│   │   ├── repair_20250713_133036_original.py [INCLUDED]
│   │   ├── repair_20250713_133036_traceback.txt
│   │   ├── repair_20250713_134136_fixed.py [INCLUDED]
│   │   ├── repair_20250713_134136_original.py [INCLUDED]
│   │   ├── repair_20250713_134136_traceback.txt
│   │   ├── repair_20250713_134145_fixed.py [INCLUDED]
│   │   ├── repair_20250713_134145_original.py [INCLUDED]
│   │   ├── repair_20250713_134145_traceback.txt
│   │   ├── repair_20250713_134201_fixed.py [INCLUDED]
│   │   ├── repair_20250713_134201_original.py [INCLUDED]
│   │   ├── repair_20250713_134201_traceback.txt
│   │   ├── repair_20250713_142257_fixed.py [INCLUDED]
│   │   ├── repair_20250713_142257_original.py
│   │   ├── repair_20250713_142257_traceback.txt
│   │   ├── repair_20250713_142312_fixed.py
│   │   ├── repair_20250713_142312_original.py [INCLUDED]
│   │   ├── repair_20250713_142312_traceback.txt
│   │   ├── repair_20250713_142329_fixed.py [INCLUDED]
│   │   ├── repair_20250713_142329_original.py
│   │   ├── repair_20250713_142329_traceback.txt
│   │   ├── repair_20250713_173707_fixed.py [INCLUDED]
│   │   ├── repair_20250713_173707_original.py
│   │   ├── repair_20250713_173707_traceback.txt
│   │   ├── repair_20250713_173722_fixed.py [INCLUDED]
│   │   ├── repair_20250713_173722_original.py [INCLUDED]
│   │   ├── repair_20250713_173722_traceback.txt
│   │   ├── repair_20250713_173733_fixed.py [INCLUDED]
│   │   ├── repair_20250713_173733_original.py [INCLUDED]
│   │   ├── repair_20250713_173733_traceback.txt
│   │   ├── repair_20250713_174013_fixed.py [INCLUDED]
│   │   ├── repair_20250713_174013_original.py [INCLUDED]
│   │   ├── repair_20250713_174013_traceback.txt
│   │   ├── repair_20250713_174027_fixed.py [INCLUDED]
│   │   ├── repair_20250713_174027_original.py [INCLUDED]
│   │   ├── repair_20250713_174027_traceback.txt
│   │   ├── repair_20250713_174037_fixed.py [INCLUDED]
│   │   ├── repair_20250713_174037_original.py [INCLUDED]
│   │   ├── repair_20250713_174037_traceback.txt
│   │   ├── repair_20250713_213259_fixed.py [INCLUDED]
│   │   ├── repair_20250713_213259_original.py
│   │   ├── repair_20250713_213259_traceback.txt
│   │   ├── repair_20250713_213319_fixed.py [INCLUDED]
│   │   ├── repair_20250713_213319_original.py [INCLUDED]
│   │   ├── repair_20250713_213319_traceback.txt
│   │   ├── repair_20250713_213331_fixed.py [INCLUDED]
│   │   ├── repair_20250713_213331_original.py [INCLUDED]
│   │   ├── repair_20250713_213331_traceback.txt
│   │   ├── repair_20250713_213522_fixed.py [INCLUDED]
│   │   ├── repair_20250713_213522_original.py [INCLUDED]
│   │   ├── repair_20250713_213522_traceback.txt
│   │   ├── repair_20250713_213538_fixed.py [INCLUDED]
│   │   ├── repair_20250713_213538_original.py [INCLUDED]
│   │   ├── repair_20250713_213538_traceback.txt
│   │   ├── repair_20250713_213549_fixed.py
│   │   ├── repair_20250713_213549_original.py [INCLUDED]
│   │   └── repair_20250713_213549_traceback.txt
│   ├── sandbox_output
│   │   ├── sample.py [INCLUDED]
│   │   └── test_sample.py [INCLUDED]
│   └── streamlit_legacy.py [INCLUDED]
├── test_localsystem.txt
├── tests
│   ├── __init__.py
│   ├── agents
│   │   ├── test_debugger_agent.py
│   │   ├── test_debugger_agent_enhanced.py
│   │   ├── test_debugger_enhanced_final.py
│   │   ├── test_guardian_agent.py
│   │   ├── test_guardian_agent_ultimate.py
│   │   ├── test_knowledge_curator_agent_ultimate.py
│   │   ├── test_policy_agent.py
│   │   ├── test_policy_agent_deep.py
│   │   └── test_simple_working.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── test_api_comprehensive.py
│   │   └── test_server.py
│   ├── audio
│   │   ├── __init__.py
│   │   ├── test_voice_to_text_deep.py
│   │   └── test_voice_to_text_ultimate.py
│   ├── code_interpreter
│   │   ├── __init__.py
│   │   ├── test_base_interpreter.py
│   │   ├── test_jupyter_client_enhanced.py
│   │   └── test_sandbox_runner_enhanced.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── test_orchestrator.py
│   │   ├── test_orchestrator_enhanced.py
│   │   ├── test_orchestrator_mega.py
│   │   └── test_orchestrator_ultimate.py
│   ├── gradio_app
│   │   ├── __init__.py
│   │   ├── api_key_test.py
│   │   ├── clean_test.py
│   │   ├── debug_api_key.py
│   │   ├── functional_test_streamlit_tab.py
│   │   ├── launch_test.py
│   │   ├── test_app_ui.py
│   │   ├── test_auto_revision_runner.py
│   │   ├── test_gradio_integration.py
│   │   ├── test_interactive_generator.py
│   │   ├── test_revision_loop.py
│   │   ├── test_streamlit_migrated_tab.py
│   │   └── test_streamlit_tab.py
│   ├── integration
│   │   └── test_real_functionality.py
│   ├── modules
│   │   ├── __init__.py
│   │   ├── test_chat_handler.py
│   │   ├── test_code_generator.py
│   │   ├── test_diff_viewer.py
│   │   ├── test_history_viewer.py
│   │   ├── test_tester.py
│   │   └── test_whisper_handler.py
│   ├── test.apikey.py
│   ├── test_deepseek.py
│   ├── test_env_load.py
│   ├── test_file_creator.py
│   ├── test_graph_builder.py
│   ├── test_history_manager.py
│   ├── test_immediate_boost.py
│   ├── test_kimi.py
│   ├── test_llm_integration.py
│   ├── test_main_ui.py
│   ├── test_opencodeinterpreter_webui.py
│   ├── test_opencodeinterpreter_webui_ultimate.py
│   ├── test_realtime_whisper.py
│   ├── test_sandbox_executor.py
│   ├── test_smoke.py
│   ├── test_streamlit_legacy.py
│   ├── test_unified_analyzer.py
│   ├── test_voice_to_text.py
│   └── utils
│       ├── __init__.py
│       ├── test_app.py
│       ├── test_cleaner.py
│       ├── test_code_analyzer.py
│       ├── test_code_analyzer_enhanced.py
│       ├── test_config_deep.py
│       ├── test_const.py
│       ├── test_const_extended.py
│       ├── test_diff_tools.py
│       ├── test_file_utils.py
│       ├── test_file_utils_enhanced.py
│       ├── test_log_monitor.py
│       ├── test_tree_sitter_checker.py
│       ├── test_vcs.py
│       └── test_zip_output.py
├── tools
│   ├── backup_tool.py
│   ├── balance_watch.py
│   ├── build_tree_sitter.py
│   ├── chatgpt_whisper_chatbot.py
│   ├── chronicle_visualizer.py
│   ├── code_export_gemini_fixed.py [INCLUDED]
│   ├── code_export_gemini_old.py [INCLUDED]
│   ├── code_export_gui.py
│   ├── code_export_gui_SaaS.py [INCLUDED]
│   ├── code_export_gui_fixed.py [INCLUDED]
│   ├── context_bundle_prime.config.json
│   ├── context_bundle_prime.py [INCLUDED]
│   ├── cost_dashboard.py
│   ├── create_init_files.py
│   ├── dashboard.py
│   ├── export_structure.py
│   ├── genesis_analyzer.config.json
│   ├── genesis_analyzer.py [INCLUDED]
│   ├── gradio_code_initializer.py
│   ├── gradio_project_export_ui.py
│   ├── live_lint_checker.py
│   ├── logicbridge_chatbot.py
│   ├── loosen_requirements.py
│   ├── price_sync.py
│   ├── project_structure_export
│   │   └── NexusCore_folder_structure.txt
│   ├── prompt_batcher.py
│   ├── scribe.py
│   ├── streamlit_dashboard.py
│   ├── utils
│   │   └── test_tree_sitter.py
│   ├── watcher.py
│   └── weather_gpt.py
├── tree_sitter_languages
│   └── tree-sitter-python
│       ├── .editorconfig
│       ├── .github
│       │   ├── FUNDING.yml
│       │   ├── ISSUE_TEMPLATE
│       │   │   ├── bug_report.yml
│       │   │   ├── config.yml
│       │   │   └── feature_request.yml
│       │   └── workflows
│       │       ├── ci.yml
│       │       ├── fuzz.yml
│       │       ├── lint.yml
│       │       └── publish.yml
│       ├── CMakeLists.txt
│       ├── Cargo.lock
│       ├── Cargo.toml
│       ├── LICENSE
│       ├── Makefile
│       ├── Package.resolved
│       ├── Package.swift
│       ├── README.md
│       ├── binding.gyp
│       ├── bindings
│       │   ├── c
│       │   │   ├── tree-sitter-python.h
│       │   │   └── tree-sitter-python.pc.in
│       │   ├── go
│       │   │   ├── binding.go
│       │   │   └── binding_test.go
│       │   ├── node
│       │   │   ├── binding.cc
│       │   │   ├── binding_test.js
│       │   │   ├── index.d.ts
│       │   │   └── index.js
│       │   ├── python
│       │   │   ├── tests
│       │   │   │   └── test_binding.py
│       │   │   └── tree_sitter_python
│       │   │       ├── __init__.py
│       │   │       ├── __init__.pyi
│       │   │       ├── binding.c
│       │   │       └── py.typed
│       │   ├── rust
│       │   │   ├── build.rs
│       │   │   └── lib.rs
│       │   └── swift
│       │       ├── TreeSitterPython
│       │       │   └── python.h
│       │       └── TreeSitterPythonTests
│       │           └── TreeSitterPythonTests.swift
│       ├── eslint.config.mjs
│       ├── examples
│       │   ├── compound-statement-without-trailing-newline.py
│       │   ├── crlf-line-endings.py
│       │   ├── mixed-spaces-tabs.py
│       │   ├── multiple-newlines.py
│       │   ├── python2-grammar-crlf.py
│       │   ├── python2-grammar.py
│       │   ├── python3-grammar-crlf.py
│       │   ├── python3-grammar.py
│       │   ├── python3.8_grammar.py
│       │   ├── simple-statements-without-trailing-newline.py
│       │   ├── tabs.py
│       │   └── trailing-whitespace.py
│       ├── go.mod
│       ├── go.sum
│       ├── grammar.js
│       ├── package-lock.json
│       ├── package.json
│       ├── pyproject.toml
│       ├── queries
│       │   ├── highlights.scm
│       │   └── tags.scm
│       ├── setup.py
│       ├── src
│       │   ├── grammar.json
│       │   ├── node-types.json
│       │   ├── parser.c
│       │   ├── scanner.c
│       │   └── tree_sitter
│       │       ├── alloc.h
│       │       ├── array.h
│       │       └── parser.h
│       ├── test
│       │   ├── corpus
│       │   │   ├── errors.txt
│       │   │   ├── expressions.txt
│       │   │   ├── literals.txt
│       │   │   ├── pattern_matching.txt
│       │   │   └── statements.txt
│       │   ├── highlight
│       │   │   ├── keywords.py
│       │   │   ├── parameters.py
│       │   │   └── pattern_matching.py
│       │   └── tags
│       │       └── main.py
│       └── tree-sitter.json
├── vscode-extension
│   ├── .vscodeignore
│   ├── codegpt-tree-sitter-0.0.1.vsix
│   ├── media
│   │   └── tree_visualizer.html
│   ├── package-lock.json
│   ├── package.json
│   ├── python
│   │   └── tree_sitter_checker.py
│   ├── src
│   │   ├── ast_visualizer.ts
│   │   ├── extension.ts
│   │   └── openai_summarizer.ts
│   └── tsconfig.json
├── vscode-extension.zip
└── workspace
    ├── BUYMA無在庫転売で “実際に利用実績がある” 追加転送サービス.md
    ├── crm_project
    │   └── app
    │       └── main.py
    ├── default_project
    │   ├── app
    │   │   ├── __init__.py
    │   │   └── main.py
    │   └── tests
    │       ├── __init__.py
    │       └── test_main.py
    └── test_crm_app
        ├── .nexus_logs
        │   ├── fkb_suggestions_rejected.jsonl
        │   ├── run_data.jsonl
        │   └── run_log.md
        ├── app
        │   └── main.py
        └── tests
            └── test_main.py
```

## 🧩 主要コンポーネント要約

### 📄 `tree_sitter_languages\tree-sitter-python\examples\python3.8_grammar.py`
- *解析中にエラー*

### 📄 `tree_sitter_languages\tree-sitter-python\examples\python2-grammar.py`
- *解析中にエラー*

### 📄 `tree_sitter_languages\tree-sitter-python\examples\python2-grammar-crlf.py`
- *解析中にエラー*

### 📄 `tree_sitter_languages\tree-sitter-python\examples\python3-grammar-crlf.py`
- **class** `TokenTests`
- **class** `GrammarTests`
- **def** `test_main()`

### 📄 `tree_sitter_languages\tree-sitter-python\examples\python3-grammar.py`
- **class** `TokenTests`
- **class** `GrammarTests`
- **def** `test_main()`

### 📄 `src\nexuscore\agents\requirement_agent.py`
- **class** `RequirementAgent`
- **def** `_to_half_width_digits()`

### 📄 `tools\code_export_gemini_fixed.py`
- **class** `ChronicleGenerator`
- **def** `sanitize_name()`
- **def** `generate_project_prefix()`
- **def** `load_gitignore()`
- **def** `path_is_ignored()`
- **def** `build_import_map()`
- **def** `loc_count()`
- **def** `file_score()`
- **def** `collect_and_score_files()`
- **def** `create_readme_md()`
- **def** `create_code_structure_manifest_md()`
- **def** `_bytes_from_mb()`
- **def** `_copy_to_manifest_folder()`
- **def** `export_for_gemini()`
- **def** `run_export_wrapper()`
- **def** `create_interface()`

### 📄 `tools\code_export_gemini_old.py`
- **class** `ChronicleGenerator`
- **def** `sanitize_name()`
- **def** `generate_project_prefix()`
- **def** `load_gitignore()`
- **def** `path_is_ignored()`
- **def** `build_import_map()`
- **def** `degree_centrality()`
- **def** `loc_count()`
- **def** `file_score()`
- **def** `collect_files()`
- **def** `make_tree_and_list()`
- **def** `generate_project_info_content()`
- **def** `create_combined_code()`
- **def** `create_readme_md()`
- **def** `export_for_gemini()`
- **def** `create_interface()`
- **def** `show_gemini_preview()`
- **def** `run_export_wrapper()`
- **def** `cancel_export()`
- **def** `browse_and_append()`
- **def** `_get_allowed_paths()`

### 📄 `tools\code_export_gui_fixed.py`
> code_export_gui_fixed.py — importance-aware export with folder-named outputs (ERROR FIXED)
- **class** `ProgressProxy`
- **def** `sanitize_name()`
- **def** `generate_project_prefix()`
- **def** `load_gitignore()`
- **def** `path_is_ignored()`
- **def** `build_import_map()`
- **def** `degree_centrality()`
- **def** `loc_count()`
- **def** `file_score()`
- **def** `collect_files()`
- **def** `make_tree()`
- **def** `def_class_only()`
- **def** `combine_py()`
- **def** `export_multi()`
- **def** `run_export()`
- **def** `cancel_export()`
- **def** `browse_and_append()`
- **def** `show_naming_preview()`
- **def** `create_interface()`

### 📄 `tools\code_export_gui_SaaS.py`
- **def** `sanitize_name()`
- **def** `generate_project_prefix()`
- **def** `load_gitignore()`
- **def** `should_force_include()`
- **def** `path_is_ignored()`
- **def** `build_import_map()`
- **def** `degree_centrality()`
- **def** `loc_count()`
- **def** `file_score()`
- **def** `write_redacted_env()`
- **def** `collect_files()`
- **def** `make_tree()`
- **def** `combine_py()`
- **def** `export_multi()`
- **def** `run_export()`
- **def** `cancel_export()`
- **def** `browse_and_append()`
- **def** `preview_output()`
- **def** `create_interface()`

### 📄 `src\nexuscore\core\orchestrator.py`
- **class** `Orchestrator`
- **def** `clean_llm_output()`

### 📄 `tests\code_interpreter\test_base_interpreter.py`
- **class** `TestBaseCodeInterpreter`
- **class** `TestJupyterClient`
- **class** `TestOpenCodeInterpreter`
- **class** `TestSandboxRunner`
- **class** `TestGradioTestRunner`
- **class** `TestRepairModule`
- **class** `TestCodeInterpreterIntegration`

### 📄 `tools\context_bundle_prime.py`
- **def** `_win_longpath()`
- **def** `_ensure_parent_dir()`
- **def** `save_text()`
- **def** `save_json()`
- **def** `human()`
- **def** `sha256_file()`
- **def** `load_json()`
- **def** `load_gitignore()`
- **def** `match_any()`
- **def** `ast_index()`
- **def** `extract_docstrings()`
- **def** `iter_files()`
- **def** `make_digest()`
- **def** `build_import_graph()`
- **def** `make_repo_summary()`
- **def** `make_tree_text()`
- **def** `load_prev_index()`
- **def** `diff_metas()`
- **def** `zip_dir()`
- **def** `split_file()`
- **def** `main()`

### 📄 `tests\core\test_orchestrator.py`
- **class** `TestOrchestrator`

### 📄 `tools\genesis_analyzer.py`
- **class** `AnalyzerConfig`
- **def** `_setup_logger()`
- **def** `utc_now_iso()`
- **def** `is_binary()`
- **def** `file_sha1()`
- **def** `to_posix()`
- **def** `match_excluded()`
- **def** `iter_target_files()`
- **def** `is_git_repo()`
- **def** `git_changed_files()`
- **def** `load_state()`
- **def** `save_state()`
- **def** `hash_diff()`
- **def** `ast_outline_for_py()`
- **def** `build_integrated_summary()`
- **def** `append_chronicle()`
- **def** `run_snapshot()`
- **def** `run_diff()`
- **def** `main()`

### 📄 `src\nexuscore\agents\context_agent.py`
> Context Agent - 完全版（simple版の安定性 + 元版の全機能）
- **class** `ContextAgent`

### 📄 `src\nexuscore\llm\llm_router.py`
- **class** `BaseLLM`
- **class** `OpenAICompat`
- **class** `OpenAILLM`
- **class** `DeepSeekLLM`
- **class** `MoonshotLLM`
- **class** `AnthropicLLM`
- **class** `GeminiLLM`
- **class** `LocalLLM`
- **class** `LLMRouter`
- **def** `canonicalize()`
- **def** `read_shared_preamble()`
- **def** `_write_usage()`
- **def** `_get_config()`
- **def** `_price_lookup()`
- **def** `_estimate_cost_usd()`
- **def** `normalize_model()`
- **def** `model_family()`
- **def** `_find_api_key()`

### 📄 `tests\agents\test_knowledge_curator_agent_ultimate.py`
- **class** `TestKnowledgeCuratorAgentUltimate`
- **class** `TestKnowledgeCuratorAgentAdvanced`

### 📄 `src\nexuscore\gradio_app\streamlit_migrated_tab.py`
> Streamlit風コード生成・テストタブ（Context Agent完全統合版）- 最終版 v2.2
- **def** `load_api_key()`
- **def** `extract_code_from_response()`
- **def** `run_tests_safely_sync()`
- **def** `create_streamlit_migrated_tab()`
- **def** `tab_streamlit_port()`

### 📄 `tests\utils\test_file_utils.py`
- **class** `TestFileUtilsBasic`
- **class** `TestFileUtilsAdvanced`
- **class** `TestFileUtilsErrorHandling`
- **class** `TestFileUtilsUtilities`