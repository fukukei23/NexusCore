from flask import Blueprint, render_template, request
from app.utils.image_crawler import crawl_images

bp = Blueprint('image_crawler', __name__)

@bp.route('/image_crawler', methods=['GET', 'POST'])
def image_crawler():
    message = ''
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        use_bing = request.form.get('use_bing') == 'on'
        use_google = request.form.get('use_google') == 'on'
        engines = []
        if use_bing:
            engines.append('bing')
        if use_google:
            engines.append('google')
        if keyword and engines:
            save_dir = crawl_images(keyword, max_num=50, engines=engines)
            message = f"「{keyword}」の画像を {', '.join(engines)} で収集し、{save_dir} に保存しました。"
        elif not engines:
            message = "検索エンジンを1つ以上選択してください。"
    return render_template('image_crawler.html', message=message)
