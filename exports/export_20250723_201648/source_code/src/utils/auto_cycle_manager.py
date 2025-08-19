from auto_execute import execute_python_code
from auto_repair import suggest_fix
from patch_applier import apply_patch_to_code

def auto_repair_cycle(initial_code, max_iter=3):
    code = initial_code
    for i in range(max_iter):
        print(f"🔁 試行 {i+1}回目...")
        output, error = execute_python_code(code)
        if not error:
            print("✅ 実行成功！\n出力:\n", output)
            return code, output
        print("⚠ エラー検出:\n", error)
        suggestion = suggest_fix(error, code)
        code = apply_patch_to_code(code, suggestion)
    print("❌ 最大試行回数に達しました。")
    return code, None