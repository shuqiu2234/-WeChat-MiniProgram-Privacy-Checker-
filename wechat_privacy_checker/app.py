import os
import uuid
import shutil
import json
import zipfile
from pathlib import Path
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from utils.analyzer import PrivacyAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """只允许上传 .zip 文件（源码压缩包）"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('未选择文件', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('文件名为空', 'danger')
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash('请上传 .zip 格式的小程序源码压缩包', 'danger')
            return redirect(request.url)

        task_id = str(uuid.uuid4())
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        zip_path = os.path.join(upload_dir, filename)
        file.save(zip_path)

        print("[1/3] 上传成功，开始解压源码包...")
        extract_dir = os.path.join(output_dir, 'source')
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        # 定位源码根目录（如果解压后只有一个顶层文件夹，则进入该文件夹）
        items = os.listdir(extract_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            source_dir = os.path.join(extract_dir, items[0])
        else:
            source_dir = extract_dir
        print(f"[2/3] 解压完成，源码目录: {source_dir}")

        try:
            # 加载规则库
            with open('rules.json', 'r', encoding='utf-8') as f:
                rules = json.load(f)
            analyzer = PrivacyAnalyzer(rules)

            print("[3/3] 开始静态分析...")
            result = analyzer.analyze(source_dir)
            print("[3/3] 分析完成，生成报告...")

            # 保存结果 JSON
            result_path = os.path.join(output_dir, 'result.json')
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            # 渲染 HTML 报告并保存（供 PDF 导出）
            report_html = render_template('report.html', result=result, task_id=task_id)
            html_path = os.path.join(output_dir, 'report.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(report_html)

            return render_template('report.html', result=result, task_id=task_id)

        except Exception as e:
            flash(f'分析过程中出现错误：{str(e)}', 'danger')
            return redirect(request.url)

    return render_template('index.html')

@app.route('/download_pdf/<task_id>')
def download_pdf(task_id):
    """导出 PDF 报告"""
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
    html_path = os.path.join(output_dir, 'report.html')
    if not os.path.exists(html_path):
        return '报告不存在', 404
    pdf_path = os.path.join(output_dir, 'report.pdf')
    try:
        import pdfkit
        wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'  # 请根据实际路径修改
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        pdfkit.from_file(html_path, pdf_path, configuration=config)
        return send_file(pdf_path, as_attachment=True, download_name='隐私合规检测报告.pdf')
    except ImportError:
        return '请安装 pdfkit 和 wkhtmltopdf 以支持 PDF 导出', 500
    except Exception as e:
        return f'PDF 生成失败：{str(e)}', 500

if __name__ == '__main__':
    app.run(debug=True)
