import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pathlib import Path
from PIL import Image
import glob
import base64

# 页面配置
st.set_page_config(
    page_title="报告评分系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    /* 设置页面可横向拖拽和更大宽度 */
    .main .block-container {
        max-width: 95%;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
        text-align: center;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    
    .status-processed {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .status-unprocessed {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .report-section {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .section-title {
        font-size: 1.25rem;
        font-weight: bold;
        color: #495057;
        margin-bottom: 0.5rem;
        border-bottom: 1px solid #dee2e6;
        padding-bottom: 0.25rem;
    }
    
    .scoring-section {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 0.375rem;
        padding: 1rem;
        margin-top: 1rem;
    }
    
    .error-count-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .error-count-item {
        text-align: center;
    }
    
    .error-count-label {
        font-weight: bold;
        margin-bottom: 0.25rem;
    }
    
    .fixed-image-container {
        height: 500px;
        overflow: hidden;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
    }
    
    .fixed-report-container {
        height: 400px;
        overflow-y: auto;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
        margin-bottom: 1rem;
    }
    
    .report-content {
        white-space: pre-wrap;
        word-wrap: break-word;
        line-height: 1.5;
    }
    
    /* 自定义滚动条样式 */
    .fixed-report-container::-webkit-scrollbar {
        width: 8px;
    }
    
    .fixed-report-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    .fixed-report-container::-webkit-scrollbar-thumb {
        background: #888;
        border-radius: 4px;
    }
    
    .fixed-report-container::-webkit-scrollbar-thumb:hover {
        background: #555;
    }
</style>
""", unsafe_allow_html=True)

def load_folder_data(folder_path):
    """加载文件夹中的所有数据"""
    data = {}
    
    # 读取原始报告
    report_file = os.path.join(folder_path, "report.json")
    if os.path.exists(report_file):
        with open(report_file, 'r', encoding='utf-8') as f:
            data['report'] = json.load(f)
    
    # 读取图像文件 - 选择image_{n}.jpg中n最小的文件
    image_files = glob.glob(os.path.join(folder_path, "image_*.jpg")) + glob.glob(os.path.join(folder_path, "image_*.png"))
    if image_files:
        # 提取文件名中的数字并排序，选择n最小的
        def extract_number(filename):
            import re
            match = re.search(r'image_(\d+)\.', filename)
            return int(match.group(1)) if match else float('inf')
        
        image_files.sort(key=extract_number)
        data['image'] = image_files[0]  # 取n最小的图像文件
    
    # 读取所有模型预测文件
    predict_files = glob.glob(os.path.join(folder_path, "*_predict.json"))
    data['models'] = {}
    
    for predict_file in predict_files:
        model_name = os.path.basename(predict_file).replace("_predict.json", "")
        with open(predict_file, 'r', encoding='utf-8') as f:
            data['models'][model_name] = json.load(f)
    
    # 检查是否已有review文件（支持新的命名规则）
    data['reviews'] = {}
    data['review_files'] = {}
    
    for model_name in data['models'].keys():
        # 查找所有相关的review文件
        review_pattern = os.path.join(folder_path, f"{model_name}_review*.json")
        review_files = glob.glob(review_pattern)
        
        data['review_files'][model_name] = review_files
        
        # 如果有review文件，加载最新的一个
        if review_files:
            # 按修改时间排序，取最新的
            latest_review = max(review_files, key=os.path.getmtime)
            with open(latest_review, 'r', encoding='utf-8') as f:
                data['reviews'][model_name] = json.load(f)
    
    return data

def get_next_review_number(folder_path, model_name, username):
    """获取下一个review文件编号"""
    pattern = os.path.join(folder_path, f"{model_name}_review_{username}_*.json")
    existing_files = glob.glob(pattern)
    
    if not existing_files:
        return 0
    
    # 提取现有的编号
    numbers = []
    for file_path in existing_files:
        filename = os.path.basename(file_path)
        # 提取编号部分
        try:
            # 格式: {model_name}_review_{username}_{N}.json
            parts = filename.replace('.json', '').split('_')
            if len(parts) >= 4 and parts[-1].isdigit():
                numbers.append(int(parts[-1]))
        except:
            continue
    
    return max(numbers) + 1 if numbers else 0

def save_review(folder_path, model_name, username, review_data, save_path=None):
    """保存review文件"""
    if not username.strip():
        raise ValueError("用户名不能为空")
    
    # 使用指定的保存路径，如果没有指定则使用默认路径
    if save_path and save_path.strip():
        target_path = save_path.strip()
    else:
        target_path = folder_path
    
    # 确保保存路径存在
    os.makedirs(target_path, exist_ok=True)
    
    # 获取下一个编号
    review_number = get_next_review_number(target_path, model_name, username)
    
    # 生成文件名
    review_file = os.path.join(target_path, f"{model_name}_review_{username}_{review_number}.json")
    
    # 添加额外信息到review_data
    review_data['username'] = username
    review_data['review_number'] = review_number
    
    with open(review_file, 'w', encoding='utf-8') as f:
        json.dump(review_data, f, ensure_ascii=False, indent=2)
    
    return review_file

def create_fixed_image_container(image_path, width=600, height=600):
    """创建固定尺寸的图像容器"""
    try:
        # 读取图像并转换为base64
        with open(image_path, "rb") as img_file:
            img_data = base64.b64encode(img_file.read()).decode()
        
        # 创建HTML容器
        html = f"""
        <div style="
            width: {width}px;
            height: {height}px;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 0.5rem;
            background-color: #f8f9fa;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
        ">
            <img src="data:image/jpeg;base64,{img_data}" 
                 style="
                     max-width: 100%;
                     max-height: 100%;
                     object-fit: contain;
                     display: block;
                     margin: auto;
                     position: absolute;
                     top: 50%;
                     left: 50%;
                     transform: translate(-50%, -50%);
                 " 
                 alt="胸部X光片" />
        </div>
        """
        return html
    except Exception as e:
        return f"<div style='color: red;'>图像加载失败: {e}</div>"

def create_fixed_text_container(content, width=500, height=400, title="报告内容"):
    """创建固定尺寸的文本容器"""
    # 转义HTML特殊字符
    import html
    escaped_content = html.escape(content)
    
    # 创建HTML容器
    html = f"""
    <div style="
        width: {width}px;
        height: {height}px;
        border: 1px solid #dee2e6;
        border-radius: 0.375rem;
        padding: 0.5rem;
        background-color: #f8f9fa;
        overflow-y: auto;
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.4;
        white-space: pre-wrap;
        word-wrap: break-word;
    ">
        <div style="font-size: 14px; font-weight: bold; margin-bottom: 0.5rem; color: #495057;">{title}</div>
        <div style="font-size: 12px;">{escaped_content}</div>
    </div>
    
    <style>
    .fixed-text-container::-webkit-scrollbar {{
        width: 8px;
    }}
    .fixed-text-container::-webkit-scrollbar-track {{
        background: #f1f1f1;
        border-radius: 4px;
    }}
    .fixed-text-container::-webkit-scrollbar-thumb {{
        background: #888;
        border-radius: 4px;
    }}
    .fixed-text-container::-webkit-scrollbar-thumb:hover {{
        background: #555;
    }}
    </style>
    """
    return html

def create_findings_impression_containers(findings, impression, width=600, height=300):
    """创建分别显示findings和impression的容器"""
    import html
    
    findings_escaped = html.escape(findings) if findings else ""
    impression_escaped = html.escape(impression) if impression else ""
    
    # 创建HTML容器
    html_content = f"""
    <div style="display: flex; flex-direction: column; gap: 1rem; width: {width}px;">
        <!-- Findings容器 -->
        <div style="
            height: {height}px;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 0.5rem;
            background-color: #f8f9fa;
            overflow-y: auto;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
        ">
            <div style="font-size: 14px; font-weight: bold; margin-bottom: 0.5rem; color: #495057;">Findings</div>
            <div style="font-size: 12px;">{findings_escaped}</div>
        </div>
        
        <!-- Impression容器 -->
        <div style="
            height: {height}px;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            padding: 0.5rem;
            background-color: #f8f9fa;
            overflow-y: auto;
            font-family: Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            white-space: pre-wrap;
            word-wrap: break-word;
        ">
            <div style="font-size: 14px; font-weight: bold; margin-bottom: 0.5rem; color: #495057;">Impression</div>
            <div style="font-size: 12px;">{impression_escaped}</div>
        </div>
    </div>
    
    <style>
    .report-container::-webkit-scrollbar {{
        width: 8px;
    }}
    .report-container::-webkit-scrollbar-track {{
        background: #f1f1f1;
        border-radius: 4px;
    }}
    .report-container::-webkit-scrollbar-thumb {{
        background: #888;
        border-radius: 4px;
    }}
    .report-container::-webkit-scrollbar-thumb:hover {{
        background: #555;
    }}
    </style>
    """
    return html_content

def create_data_from_uploaded_files(uploaded_files):
    """从上传的文件创建数据"""
    data = {}
    
    # 读取原始报告
    report_data = None
    for file in uploaded_files:
        if file.name.endswith('report.json'):
            try:
                content = file.getvalue().decode('utf-8')
                report_data = json.loads(content)
                data['report'] = report_data
                break
            except Exception as e:
                st.error(f"读取report.json失败: {e}")
    
    # 从report.json中提取subject_id和study_id
    if report_data:
        subject_id = report_data.get('subject_id', 'unknown')
        study_id = report_data.get('study_id', 'unknown')
        data['case_name'] = f"subject_{subject_id}_study_{study_id}"
    else:
        data['case_name'] = "unknown_case"
    
    # 读取图像文件 - 选择image_{n}.jpg中n最小的文件
    image_files = [f for f in uploaded_files if f.name.startswith('image_') and f.name.endswith(('.jpg', '.png'))]
    if image_files:
        # 提取文件名中的数字并排序，选择n最小的
        def extract_number(filename):
            import re
            match = re.search(r'image_(\d+)\.', filename)
            return int(match.group(1)) if match else float('inf')
        
        image_files.sort(key=lambda f: extract_number(f.name))
        # 将图像文件保存到临时位置供显示
        import tempfile
        temp_image_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_image_path.write(image_files[0].getvalue())
        temp_image_path.close()
        data['image'] = temp_image_path.name
    
    # 读取所有模型预测文件
    data['models'] = {}
    
    for file in uploaded_files:
        if file.name.endswith('_predict.json'):
            model_name = file.name.replace('_predict.json', '')
            try:
                content = file.getvalue().decode('utf-8')
                data['models'][model_name] = json.loads(content)
            except Exception as e:
                st.error(f"读取{file.name}失败: {e}")
    
    # 检查是否已有review文件（支持新的命名规则）
    data['reviews'] = {}
    data['review_files'] = {}
    
    for model_name in data['models'].keys():
        # 查找所有相关的review文件
        review_files = [f for f in uploaded_files if f.name.startswith(f"{model_name}_review")]
        data['review_files'][model_name] = review_files
        
        # 如果有review文件，加载最新的一个
        if review_files:
            # 按修改时间排序，取最新的
            latest_review = max(review_files, key=lambda f: f.name)
            try:
                content = latest_review.getvalue().decode('utf-8')
                data['reviews'][model_name] = json.loads(content)
            except Exception as e:
                st.error(f"读取review文件失败: {e}")
    
    return data

def main():
    st.markdown('<div class="main-header">报告评估系统</div>', unsafe_allow_html=True)
    # 用户名输入
    st.sidebar.header("👤 用户信息")
    username = st.sidebar.text_input("用户名:", placeholder="请输入您的用户名")
    
    # 侧边栏 - 文件夹选择
    st.sidebar.header("📁 上传数据文件夹")
    
    # 显示需要的文件类型
    with st.sidebar.expander("📋 文件夹中需要的文件", expanded=False):
        st.markdown("""
        **必需文件:**
        - `image_{n}.jpg` - 医学图像 (n为数字，系统会选择n最小的图像)
        - `report.json` - 原始报告
        
        **模型预测文件 (至少一个):**
        - `{model_name}_predict.json` 文件
        """)
    
    # 文件上传功能 - 支持多种格式
    uploaded_files = st.sidebar.file_uploader(
        "上传病例文件夹文件",
        type=['jpg', 'jpeg', 'png', 'json'],
        accept_multiple_files=True,
        help="请选择包含图像和报告的文件夹中的所有文件"
    )
    
    # 处理上传的文件
    if uploaded_files:
        # 检查是否包含subject文件夹结构的文件
        has_subject_files = any(
            file.name.startswith("subject_") or 
            "subject_" in file.name or
            file.name.endswith(("_predict.json", "report.json", "image_1.jpg"))
            for file in uploaded_files
        )
        
        if has_subject_files:
            # 从上传的文件中提取原始文件夹名称
            original_folder_name = None
            
            # 方法1: 查找包含subject的文件名
            for file in uploaded_files:
                if "subject_" in file.name:
                    # 提取文件夹名称（假设文件名格式为 subject_xxx_study_xxx/xxx.jpg）
                    parts = file.name.split('/')
                    if len(parts) > 1:
                        original_folder_name = parts[0]
                        break
                    else:
                        # 如果文件名直接包含subject_，使用文件名作为文件夹名
                        original_folder_name = file.name.split('.')[0]
                        break
            
            # 方法2: 如果没有找到subject文件，查找其他可能的文件夹结构
            if not original_folder_name:
                for file in uploaded_files:
                    if '/' in file.name:
                        folder_part = file.name.split('/')[0]
                        # 检查是否是合理的文件夹名（不是临时文件名）
                        if not folder_part.startswith('tmp') and len(folder_part) > 3:
                            original_folder_name = folder_part
                            break
            
            # 方法3: 如果还是没有找到，使用第一个文件的目录名
            if not original_folder_name:
                first_file = uploaded_files[0]
                if '/' in first_file.name:
                    original_folder_name = first_file.name.split('/')[0]
                else:
                    # 使用第一个文件的名称（去掉扩展名）作为文件夹名
                    original_folder_name = first_file.name.split('.')[0]
            
            # 确保文件夹名称不为空
            if not original_folder_name or original_folder_name == "":
                original_folder_name = "uploaded_case"
            
            # 直接从上传的文件创建数据
            data = create_data_from_uploaded_files(uploaded_files)
            
            # 使用从report.json中提取的病例名称
            case_name = data.get('case_name', original_folder_name)
            
            # 调试信息：显示提取的文件夹名称和病例名称
            st.sidebar.info(f"📁 检测到文件夹: {original_folder_name}")
            st.sidebar.info(f"🏥 病例名称: {case_name}")
            st.sidebar.info(f"📄 上传文件数量: {len(uploaded_files)}")
            if uploaded_files:
                st.sidebar.info(f"📄 第一个文件: {uploaded_files[0].name}")
            
            # 侧边栏 - 模型选择
            st.sidebar.header("🤖 模型选择")
            
            if data.get('models'):
                # 创建可折叠的模型选择器
                with st.sidebar.expander("选择模型", expanded=True):
                    # 创建模型列表，包含状态信息
                    model_options = []
                    for model_name in data['models'].keys():
                        status = "✅" if model_name in data.get('reviews', {}) else "❌"
                        model_options.append(f"{status} {model_name}")
                    
                    selected_option = st.radio(
                        "可用模型:",
                        model_options,
                        key="model_selection"
                    )
                    
                    # 提取选中的模型名称
                    selected_model = selected_option.split(" ", 1)[1] if " " in selected_option else selected_option
                
                # 主界面显示
                display_main_interface(data, selected_model, case_name, username, case_name)
            else:
                st.error("未找到任何模型预测文件 (*_predict.json)")
        else:
            st.error("上传的文件不包含有效的病例数据，请确保包含图像、报告和模型预测文件")
    else:
        st.info("💡 请上传病例文件夹文件开始评估")

def display_main_interface(data, selected_model, case_name, username, usr_dir):
    """显示主界面"""
    
    # 顶部信息显示 - 病例名称和状态在同一行
    # 使用传递的病例名称
    folder_name = case_name
    
    # 检查处理状态
    if selected_model in data.get('reviews', {}):
        status_text = "✅ 已处理"
        status_class = "status-processed"
        is_processed = True
    else:
        status_text = "❌ 未处理"
        status_class = "status-unprocessed"
        is_processed = False
    
    # 在同一行显示病例名称和状态
    st.markdown(f"**当前病例:** {folder_name} <span class='status-badge {status_class}'>{status_text}</span>", unsafe_allow_html=True)
    
    # 创建三列布局：图像、报告、打分系统
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # 图像显示 - 可收起和展开
        if 'image' in data and os.path.exists(data['image']):
            with st.expander("🖼️ 医学图像", expanded=True):
                try:
                    st.image(data['image'], caption="胸部X光片", width=400)
                except Exception as e:
                    st.error(f"图像加载失败: {e}")
        else:
            st.warning("未找到图像文件")
    
    with col2:
        # 原始报告显示（上半部分，对齐图像上边界）
        if 'report' in data:
            st.markdown('<div class="section-title">📋 原始报告</div>', unsafe_allow_html=True)
            
            # 使用Streamlit原生方式显示findings和impression
            findings = data['report'].get('findings', '')
            impression = data['report'].get('impression', '')
            
            # Findings部分
            st.markdown("**Findings:**")
            findings_container = st.container()
            with findings_container:
                st.markdown(f"""
                <div style="
                    height: 140px;
                    border: 1px solid #dee2e6;
                    border-radius: 0.375rem;
                    padding: 0.5rem;
                    background-color: #f8f9fa;
                    overflow-y: auto;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">{findings}</div>
                """, unsafe_allow_html=True)
            
            # Impression部分
            st.markdown("**Impression:**")
            impression_container = st.container()
            with impression_container:
                st.markdown(f"""
                <div style="
                    height: 140px;
                    border: 1px solid #dee2e6;
                    border-radius: 0.375rem;
                    padding: 0.5rem;
                    background-color: #f8f9fa;
                    overflow-y: auto;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">{impression}</div>
                """, unsafe_allow_html=True)
        
        # 预测报告显示（下半部分，对齐图像下边界）
        if selected_model in data.get('models', {}):
            model_data = data['models'][selected_model]
            
            st.markdown('<div class="section-title">🤖 模型预测报告</div>', unsafe_allow_html=True)
            
            # 使用Streamlit原生方式显示模型预测的findings和impression
            model_findings = model_data.get('findings', '')
            model_impression = model_data.get('impression', '')
            
            # 模型Findings部分
            st.markdown("**Findings:**")
            model_findings_container = st.container()
            with model_findings_container:
                st.markdown(f"""
                <div style="
                    height: 140px;
                    border: 1px solid #dee2e6;
                    border-radius: 0.375rem;
                    padding: 0.5rem;
                    background-color: #f8f9fa;
                    overflow-y: auto;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">{model_findings}</div>
                """, unsafe_allow_html=True)
            
            # 模型Impression部分
            st.markdown("**Impression:**")
            model_impression_container = st.container()
            with model_impression_container:
                st.markdown(f"""
                <div style="
                    height: 140px;
                    border: 1px solid #dee2e6;
                    border-radius: 0.375rem;
                    padding: 0.5rem;
                    background-color: #f8f9fa;
                    overflow-y: auto;
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    line-height: 1.4;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                ">{model_impression}</div>
                """, unsafe_allow_html=True)
    
    with col3:
        # 用户名验证
        if not username or not username.strip():
            st.warning("⚠️ 请输入用户名后才能进行评分")
            return
        
        # 打分系统
        # st.markdown('<div class="scoring-section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">📊 打分系统</div>', unsafe_allow_html=True)
        
        # 显示用户名信息
        st.info(f"👤 当前用户: {username}")
        
        # 获取之前的review数据（如果存在）
        previous_review = data.get('reviews', {}).get(selected_model, {})
        
        # PEER打分
        st.markdown("**PEER打分 (0-5分):**")
    
        
        peer_score = st.slider(
            "评分",
            min_value=0,
            max_value=5,
            value=previous_review.get('peer_score', 0),
            step=1,
            key=f"peer_score_{selected_model}",
            label_visibility="collapsed"  # 隐藏标签
        )
        
        # 添加帮助信息
        with st.expander("📖 PEER评分标准说明", expanded=True):
            st.markdown("""
            **PEER评分详细标准：**
            
            **5分 - 正确**
            - 大部分诊断结果正确
            - 大部分描述相同
            - 存在一些错误描述，但不太可能具有临床意义
            
            **4分 - 基本正确**
            - 75%的诊断结果正确
            - 大部分描述相同
            - 存在一些可能具有临床意义的错误描述
            
            **3分 - 部分正确**
            - 50%的诊断结果正确
            
            **2分 - 部分错误**
            - 25%的诊断结果正确
            
            **1分 - 存在重大错误**
            - 诊断错误
            - 可能只有一些阴性描述是相同的
            
            **0分 - 不可接受**
            - 所描述的信息完全没有重叠
            """)

        
        # 准备保存的数据
        review_data = {
            "model_name": selected_model,
            "peer_score": peer_score,
            "timestamp": str(Path().cwd()),
            "folder_name": folder_name
        }
        
        # 将数据转换为JSON字符串
        import json
        json_data = json.dumps(review_data, ensure_ascii=False, indent=2)
        
        # 生成文件名
        # 从当前数据中查找该用户该模型的最大review_number
        review_number = 0
        
        # 查找该用户该模型的所有review文件
        if selected_model in data.get('reviews', {}):
            current_review = data['reviews'][selected_model]
            # 检查是否是同一个用户的review
            if current_review.get('username') == username and 'review_number' in current_review:
                review_number = current_review['review_number'] + 1
        
        # 如果没有找到该用户的review文件，从0开始
        filename = f"{selected_model}_review_{username}_{review_number}.json"
        
        # 下载按钮
        st.download_button(
            label="💾 下载评分结果",
            data=json_data,
            file_name=filename,
            mime="application/json",
            key=f"download_{selected_model}",
            type="primary"
        )

if __name__ == "__main__":
    main()
