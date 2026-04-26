import os
import uuid
import shutil
import json
import zipfile
import subprocess
import time
from pathlib import Path
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# 导入分析模块
from utils.analyzer import PrivacyAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# ================== 工具路径配置（请修改为实际路径） ==================
UNPACK_MINI_APP_PATH = r"C:\Users\86156\Desktop\wechat_privacy_checker\UnpackMiniApp\UnpackMiniApp-main\UnpackMiniApp.exe"
KILLWXAKG_SCRIPT = r"C:\Users\86156\Desktop\wechat_privacy_checker\KillWxapkg_2.4.1_windows_amd64.exe"
# ===================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ['wxapkg', 'zip']

# ================== 解密与反编译辅助函数 ==================
def decrypt_with_unpackminiapp(encrypted_path, output_dir):
    """调用 UnpackMiniApp 解密，返回解密后的文件路径"""
    if not os.path.exists(UNPACK_MINI_APP_PATH):
        raise FileNotFoundError(f"UnpackMiniApp 工具未找到: {UNPACK_MINI_APP_PATH}")

    tool_dir = os.path.dirname(UNPACK_MINI_APP_PATH)
    wxpack_dir = os.path.join(tool_dir, 'wxpack')
    os.makedirs(wxpack_dir, exist_ok=True)

    before = set(os.listdir(wxpack_dir)) if os.path.exists(wxpack_dir) else set()

    cmd = [UNPACK_MINI_APP_PATH, encrypted_path]
    subprocess.run(cmd, cwd=tool_dir, check=True, capture_output=True, text=True, timeout=120)

    time.sleep(1)
    after = set(os.listdir(wxpack_dir))
    new_files = after - before
    if not new_files:
        raise Exception("解密后未找到输出文件")

    src = os.path.join(wxpack_dir, list(new_files)[0])
    dst = os.path.join(output_dir, 'decrypted.wxapkg')
    shutil.copy2(src, dst)
    return dst

def unpack_with_killwxakg(decrypted_path, output_dir):
    """调用 killwxakg 反编译，返回源码目录"""
    if not os.path.exists(KILLWXAKG_SCRIPT):
        raise FileNotFoundError(f"killwxakg 脚本未找到: {KILLWXAKG_SCRIPT}")

    node_path = shutil.which('node')
    if node_path is None:
        raise Exception("未找到 Node.js，请确保 Node.js 已安装并添加到 PATH")

    cmd = [node_path, KILLWXAKG_SCRIPT, decrypted_path, '-o', output_dir]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)

    base = os.path.splitext(os.path.basename(decrypted_path))[0]
    possible = os.path.join(output_dir, base)
    if os.path.isdir(possible) and os.path.exists(os.path.join(possible, 'app.json')):
        return possible
    if os.path.exists(os.path.join(output_dir, 'app.json')):
        return output_dir
    raise Exception("反编译后未找到源码目录")

# ================== Flask 路由 ==================
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
            flash('不支持的文件类型，请上传 .wxapkg 或 .zip 文件', 'danger')
            return redirect(request.url)

        task_id = str(uuid.uuid4())
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        output_dir = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        try:
            if filename.endswith('.wxapkg'):
                decrypted = decrypt_with_unpackminiapp(filepath, output_dir)
                source_dir = unpack_with_killwxakg(decrypted, output_dir)
            else:  # .zip
                extract_dir = os.path.join(output_dir, 'source')
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(filepath, 'r') as zf:
                    zf.extractall(extract_dir)
                items = os.listdir(extract_dir)
                if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                    source_dir = os.path.join(extract_dir, items[0])
                else:
                    source_dir = extract_dir

            with open('rules.json', 'r', encoding='utf-8') as f:
                rules = json.load(f)
            analyzer = PrivacyAnalyzer(rules)
            result = analyzer.analyze(source_dir)

            result_path = os.path.join(output_dir, 'result.json')
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            report_html = render_template('report.html', result=result, task_id=task_id)
            html_path = os.path.join(output_dir, 'report.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(report_html)

            return render_template('report.html', result=result, task_id=task_id)

        except Exception as e:
            flash(f'处理过程中出现错误：{str(e)}', 'danger')
            return redirect(request.url)

    return render_template('index.html')

@app.route('/download_pdf/<task_id>')
def download_pdf(task_id):
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
    html_path = os.path.join(output_dir, 'report.html')
    if not os.path.exists(html_path):
        return '报告不存在', 404
    pdf_path = os.path.join(output_dir, 'report.pdf')
    try:
        import pdfkit
        # 手动指定 wkhtmltopdf 的完整路径
        wkhtmltopdf_path = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        pdfkit.from_file(html_path, pdf_path, configuration=config)
        return send_file(pdf_path, as_attachment=True, download_name='隐私合规检测报告.pdf')
    except Exception as e:
        return f'PDF 生成失败：{str(e)}', 500

# ================== 独立工具调用接口（直接运行，无需选文件） ==================
@app.route('/run/unpackminiapp', methods=['POST'])
def run_unpackminiapp():
    """直接运行 UnpackMiniApp 程序（不带参数）"""
    try:
        if not os.path.exists(UNPACK_MINI_APP_PATH):
            return jsonify({'success': False, 'message': f'工具未找到: {UNPACK_MINI_APP_PATH}'})
        # 启动 UnpackMiniApp.exe（后台运行，不等待）
        subprocess.Popen([UNPACK_MINI_APP_PATH], shell=True)
        return jsonify({'success': True, 'message': 'UnpackMiniApp 已启动（命令行窗口可能一闪而过，如需使用请手动输入参数）'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})

@app.route('/run/killwxakg', methods=['POST'])
def run_killwxakg():
    """直接运行 killwxakg 脚本（不带参数），打开命令行窗口显示帮助"""
    try:
        if not os.path.exists(KILLWXAKG_SCRIPT):
            return jsonify({'success': False, 'message': f'脚本未找到: {KILLWXAKG_SCRIPT}'})
        node_path = shutil.which('node')
        if node_path is None:
            return jsonify({'success': False, 'message': '未找到 Node.js'})
        # 打开一个新的命令行窗口，执行 node killwxakg.js（不带参数会显示使用帮助）
        subprocess.Popen(['start', 'cmd', '/k', node_path, KILLWXAKG_SCRIPT], shell=True)
        return jsonify({'success': True, 'message': '已打开命令行窗口运行 killwxakg，请查看帮助信息'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})

if __name__ == '__main__':
    app.run(debug=True)