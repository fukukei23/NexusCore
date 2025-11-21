# ファイル名: sandbox_executor.py
# メモ:
# - run_code_in_sandbox()を呼び出し、標準出力・標準エラー・出力ファイルを返す
# - エラー・タイムアウトも判定しやすい
# - opencodeinterpreter_webui.py等からimportして使う

from sandbox_runner import run_code_in_sandbox

def execute_code_and_return_output(
    code,
    jupyter_state=None,      # 互換性のため残しているが未使用
    lang="python",
    input_files=None,
    output_files=None,
    timeout=10,
    cpu="0.5",
    memory="256m"
):
    """
    サンドボックスでコードを実行し、結果・エラー・出力ファイルを返す
    """
    try:
        stdout, stderr, returncode, outputs = run_code_in_sandbox(
            code=code,
            lang=lang,
            input_files=input_files,
            output_files=output_files,
            timeout=timeout,
            cpu=cpu,
            memory=memory
        )
        if returncode == 0:
            return stdout, "OK", outputs
        elif stderr == "Timeout":
            return "Timeout", "Timeout", outputs
        else:
            return stderr, "Error", outputs
    except Exception as e:
        return str(e), "Error", {}
