✨ 功能特性
🔓 一键解密与反编译：集成 UnpackMiniApp 和 killwxakg，自动将加密包转换为可读源码。

🔍 敏感API检测：扫描 40+ 种微信小程序敏感 API（位置、手机号、相册、剪切板、蓝牙等），支持多种调用写法。

📄 隐私政策提取：基于内容关键词的智能识别，无需依赖文件名，支持用户手动补充 .txt 文件。

🛡️ 隐私弹窗检测：检测 wx.openPrivacyContract、wx.showModal 等合规弹窗逻辑。

📊 可视化评分体系：将隐私政策条款分为四大类（A/B/C/D），共34个子项，自动评分并评定 S/A/B/C 等级。

✅ 一致性检测：比对代码中的敏感API调用与隐私政策声明，发现“未声明的收集行为”。

🌐 Web 界面：基于 Flask + Bootstrap 的清新商务风格，操作简单，支持 HTML/PDF 报告导出。

🛠 技术栈
层级	技术
后端框架	Flask 2.3+, Python 3.9+
前端	Bootstrap 5, Chart.js
解密工具	UnpackMiniApp (需手动下载)
反编译工具	killwxakg (需Node.js环境)
PDF生成	pdfkit + wkhtmltopdf
文本处理	jieba (分词，可选)
📦 安装与使用
1. 环境准备
Python 3.8 或更高版本

Node.js 14.x (用于 killwxakg)

wkhtmltopdf (用于PDF导出，下载地址)

2. 克隆项目
bash
git clone https://github.com/yourname/wechat-miniprogram-privacy-checker.git
cd wechat-miniprogram-privacy-checker
3. 安装 Python 依赖
bash
pip install -r requirements.txt
requirements.txt 内容示例：

text
Flask==2.3.3
pdfkit==1.0.0
jieba==0.42.1
requests==2.31.0
beautifulsoup4==4.12.2
4. 配置外部工具路径
编辑 app.py，修改以下变量为你的实际路径：

python
UNPACK_MINI_APP_PATH = r"C:\Tools\UnpackMiniApp.exe"
KILLWXAKG_SCRIPT = r"C:\Tools\killwxakg\killwxakg.js"
5. 运行
bash
python app.py
访问 http://127.0.0.1:5000 即可使用。

🚀 使用示例
获取小程序包：从电脑微信缓存或手机中提取 .wxapkg 文件（如 __APP__.wxapkg）。

上传分析：点击“选择文件”上传包体或源码压缩包，点击“开始检测”。

查看报告：等待片刻，页面展示合规评分、等级、缺失条款、敏感API列表、一致性检测结果等。

导出PDF：点击“下载PDF报告”保存报告。

如果无法获取源码，展开页面中的“如何获取小程序源代码包？”手风琴面板，根据指引使用 UnpackMiniApp 和 killwxakg 自行解密反编译。

📁 项目结构
text
wechat-miniprogram-privacy-checker/
├── app.py                  # Flask主程序
├── rules.json              # 规则库（API列表、关键词、分类子项）
├── utils/
│   └── analyzer.py         # 静态分析核心模块
├── templates/
│   ├── index.html          # 上传页面
│   └── report.html         # 报告页面
├── uploads/                # 临时上传目录（自动创建）
├── outputs/                # 分析结果目录（自动创建）
└── requirements.txt


📄 许可证
本项目采用 MIT 许可证。

🙏 致谢
UnpackMiniApp 解密工具

killwxakg 反编译工具

Flask Web框架

Bootstrap 前端组件库


觉得好用请给个 ⭐ Star 支持一下～
