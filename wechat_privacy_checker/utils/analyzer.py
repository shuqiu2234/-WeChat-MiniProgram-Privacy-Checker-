import re
import json
from pathlib import Path

class PrivacyAnalyzer:
    def __init__(self, rules):
        self.rules = rules
        self.api_rules = rules.get('api_rules', [])
        self.privacy_keywords = rules.get('privacy_keywords', {})
        self.classify_subitems = rules.get('classify_subitems', {})

    # ================== 增强版敏感 API 扫描 ==================


    # ================== 隐私弹窗检测 ==================
    def check_privacy_popup(self, source_dir):
        """检测隐私弹窗（wx.showModal / wx.openPrivacyContract）"""
        privacy_keywords = ['隐私', '协议', '同意', 'privacy', 'agree', 'policy']
        js_files = Path(source_dir).rglob('*.js')
        wxml_files = Path(source_dir).rglob('*.wxml')

        for js_file in js_files:
            try:
                with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if re.search(r'wx\.openPrivacyContract\s*\(', content):
                        return True
                    if re.search(r'wx\.(showModal|showActionSheet)\s*\(', content):
                        if any(kw in content for kw in privacy_keywords):
                            return True
                    pattern = r'(show|open|display)\s*([A-Za-z_]*?(?:privacy|policy|agree|协议|隐私|同意)[A-Za-z_]*?)\s*\('
                    if re.search(pattern, content, re.IGNORECASE):
                        return True
            except Exception:
                continue

        modal_tags = ['modal', 'dialog', 'popup', 'action-sheet', 'half-screen-dialog']
        for wxml_file in wxml_files:
            try:
                with open(wxml_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    has_privacy = any(kw in content for kw in privacy_keywords)
                    if has_privacy:
                        for tag in modal_tags:
                            if re.search(f'<{tag}[^>]*>', content, re.IGNORECASE):
                                return True
            except Exception:
                continue
        return False

    # ================== 过度收集检测 ==================
    def check_over_collection(self, api_matches, privacy_text):
        """过度收集检测：API 收集的信息类型未在隐私政策中提及"""
        over_collection = []
        for match in api_matches:
            info_type = match['info_type']
            if info_type not in privacy_text:
                over_collection.append(match)
        return over_collection

    # ================== 隐私政策完整性检查 ==================
    def check_privacy_completeness(self, privacy_text):
        """基础完整性检查（仅用于报告）"""
        if not privacy_text:
            return {'missing': list(self.privacy_keywords.keys()), 'score': 0}
        missing_clauses = []
        for clause, keywords in self.privacy_keywords.items():
            if clause == 'SDK相关':
                continue
            found = False
            for kw in keywords:
                if kw in privacy_text:
                    found = True
                    break
            if not found:
                missing_clauses.append(clause)
        return {'missing': missing_clauses, 'score': len(self.privacy_keywords) - len(missing_clauses)}

    # ================== 静态提取隐私文本（基于内容关键词） ==================
    def _static_extract(self, source_dir):
        """
        静态提取：扫描所有文本文件，如果文件内容包含足够多的隐私关键词，则采纳。
        不排除任何目录（包括 miniprogram_npm），以获取第三方库中的隐私声明。
        """
        all_texts = []
        # 内容关键词（用于判断是否与隐私相关）
        content_keywords = [
            '隐私政策', '个人信息保护', '用户协议', '服务条款', 'privacy policy',
            '收集个人信息', '注销账号', '删除信息', '用户权利', '同意', '授权',
            '第三方SDK', '共享信息', '跨境传输', '未成年人保护', '个人信息收集',
            '账号注销', '撤回同意', '隐私声明', '数据保护'
        ]
        # 支持的文件扩展名
        extensions = ['.txt', '.html', '.wxml', '.js', '.json', '.xml']

        total_scanned = 0
        total_accepted = 0
        accepted_files = []

        for ext in extensions:
            for file_path in Path(source_dir).rglob('*' + ext):
                total_scanned += 1

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    cleaned = re.sub(r'\s+', ' ', content).strip()
                    if len(cleaned) < 50:
                        continue

                    keyword_count = sum(1 for kw in content_keywords if kw in cleaned)
                    if keyword_count >= 2:
                        all_texts.append(cleaned)
                        total_accepted += 1
                        accepted_files.append(str(file_path))
                        print(f"[静态提取] 采纳文件: {file_path} (关键词数: {keyword_count}, 长度: {len(cleaned)})")
                    else:
                        if any(k in file_path.name.lower() for k in ['privacy', '协议', '政策']):
                            print(f"[静态提取] 文件 {file_path} 包含隐私文件名但内容关键词不足 ({keyword_count}), 未采纳")
                except Exception as e:
                    print(f"[静态提取] 警告：读取 {file_path} 失败: {e}")

        unique_texts = list(dict.fromkeys(all_texts))
        combined = '\n'.join(unique_texts).strip()
        print(f"[静态提取] 扫描文件总数: {total_scanned}，采纳文件数: {total_accepted}")
        print(f"[静态提取] 采纳的文件列表: {accepted_files}")
        print(f"[静态提取] 合并后文本总长度: {len(combined)} 字符")
        return combined

    # ================== 分类与评分 ==================
    def classify_privacy_text(self, privacy_text):
        """根据规则库将隐私政策文本分类，返回每个大类下缺失的子项列表"""
        if not privacy_text:
            subitems = self.classify_subitems
            return {cat: list(items.keys()) for cat, items in subitems.items()}
        result = {}
        for category, items in self.classify_subitems.items():
            missing = []
            for item_name, keywords in items.items():
                if not any(kw in privacy_text for kw in keywords):
                    missing.append(item_name)
            result[category] = missing
        return result

    def calculate_score(self, categories):
        """根据四大类缺失子项比例计算总分"""
        category_scores = {
            'A类：基础法律声明': 40,
            'B类：数据收集与使用': 30,
            'C类：数据共享与披露': 10,
            'D类：用户权利实现': 20
        }
        total_items = {}
        for cat, items in self.classify_subitems.items():
            total_items[cat] = len(items)

        score_details = {}
        for cat, total_score in category_scores.items():
            missing = categories.get(cat, [])
            total = total_items.get(cat, 1)
            if total == 0:
                score = total_score
            else:
                score = total_score * (1 - len(missing) / total)
            score_details[cat] = round(score, 1)

        total_score = sum(score_details.values())
        if total_score >= 90:
            grade = 'S'
        elif total_score >= 75:
            grade = 'A'
        elif total_score >= 60:
            grade = 'B'
        else:
            grade = 'C'
        return total_score, score_details, grade

    # ================== 主分析方法 ==================
    def analyze(self, source_dir):
        """执行完整分析"""
        result = {}
        api_matches = self.scan_api_calls(source_dir)
        result['api_calls'] = api_matches

        privacy_text = self._static_extract(source_dir)
        result['privacy_text'] = privacy_text[:500] + "..." if len(privacy_text) > 500 else privacy_text
        result['privacy_text_full'] = privacy_text

        has_popup = self.check_privacy_popup(source_dir)
        result['has_privacy_popup'] = has_popup

        over_collection = self.check_over_collection(api_matches, privacy_text)
        result['over_collection'] = over_collection

        completeness = self.check_privacy_completeness(privacy_text)
        result['privacy_completeness'] = completeness

        categories = self.classify_privacy_text(privacy_text)
        result['privacy_categories'] = categories

        total_score, score_details, grade = self.calculate_score(categories)
        result['total_score'] = total_score
        result['score_details'] = score_details
        result['grade'] = grade

        return result