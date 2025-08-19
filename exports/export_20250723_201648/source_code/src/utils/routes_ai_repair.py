from flask import Blueprint, render_template, request
from auto_cycle_manager import auto_repair_cycle

bp = Blueprint('ai_repair', __name__)

@bp.route("/ai_repair", methods=["GET", "POST"])
def ai_repair():
    code_text = ""
    result_code = ""
    output = ""
    if request.method == "POST":
        code_text = request.form.get("code_text", "")
        if code_text.strip():
            result_code, output = auto_repair_cycle(code_text)
    return render_template("ai_repair.html", code_text=code_text, result_code=result_code, output=output)

