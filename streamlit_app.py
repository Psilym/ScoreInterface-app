import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pathlib import Path
from PIL import Image
import glob
import base64
import tempfile

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

def create_data_from_uploaded_files(uploaded_files):
    """从上传的文件创建数据"""
    data = {}
    
    # 创建临时目录来存储上传的文件
    temp_dir = tempfile.mkdtemp()
    
    # 保存所有上传的文件到临时目录
    saved_files = {}
    for file in uploaded_files:
        file_path = os.path.join(temp_dir, file.name)
        with open(file_path, 'wb') as f:
            f.write(file.getvalue())
        saved_files[file.name] = file_path
    
    # 读取原始报告
    report_data = None
    for filename, file_path in saved_files.items():
        if filename.endswith('report.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
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
    image_files = {name: path for name, path in saved_files.items() 
                  if name.startswith('image_') and name.endswith(('.jpg', '.png'))}
    
    if image_files:
        # 提取文件名中的数字并排序，选择n最小的
        def extract_number(filename):
            import re
            match = re.search(r'image_(\d+)\.', filename)
            return int(match.group(1)) if match else float('inf')
        
        sorted_images = sorted(image_files.items(), key=lambda x: extract_number(x[0]))
        data['image'] = sorted_images[0][1]  # 取n最小的图像文件路径
        data['temp_dir'] = temp_dir  # 保存临时目录路径以便后续清理
    
    # 读取所有模型预测文件
    data['models'] = {}
    
    for filename, file_path in saved_files.items():
        if filename.endswith('_predict.json'):
            model_name = filename.replace('_predict.json', '')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data['models'][model_name] = json.load(f)
            except Exception as e:
                st.error(f"读取{filename}失败: {e}")
    
    # 检查是否已有review文件（支持新的命名规则）
    data['reviews'] = {}
    data['review_files'] = {}
    
    for model_name in data['models'].keys():
        # 查找所有相关的review文件
        review_files = {name: path for name, path in saved_files.items() 
                       if name.startswith(f"{model_name}_review")}
        data['review_files'][model_name] = list(review_files.values())
        
        # 如果有review文件，加载最新的一个
        if review_files:
            # 按文件名排序，取最新的（假设文件名包含时间戳或序号）
            latest_review_path = sorted(review_files.values())[-1]
            try:
                with open(latest_review_path, 'r', encoding='utf-8') as f:
                    data['reviews'][model_name] = json.load(f)
            except Exception as e:
                st.error(f"读取review文件失败: {e}")
    
    return data

def cleanup_temp_files(data):
    """清理临时文件"""
    if 'temp_dir' in data and os.path.exists(data['temp_dir']):
        import shutil
        try:
            shutil.rmtree(data['temp_dir'])
        except:
            pass

def main():
    st.markdown('<div class="main-header">报告评估系统</div>', unsafe_allow_html=True)
    
    # 初始化session state
    if 'current_data' not in st.session_state:
        st.session_state.current_data = None
    if 'uploaded_files_key' not in st.session_state:
        st.session_state.uploaded_files_key = 0
    
    # 用户名输入
    st.sidebar.header("👤 用户信息")
    username = st.sidebar.text_input("用户名:", placeholder="请输入您的用户名", 
                                   key="username_input")
    
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
        help="请选择包含图像和报告的文件夹中的所有文件",
        key=f"file_uploader_{st.session_state.uploaded_files_key}"
    )
    
    
    # 处理上传的文件
    if uploaded_files:
        # 检查文件是否发生变化
        current_file_names = sorted([f.name for f in uploaded_files])
        
        # 如果数据不存在或文件发生变化，重新加载数据
        if (st.session_state.current_data is None or 
            'uploaded_file_names' not in st.session_state or
            st.session_state.uploaded_file_names != current_file_names):
            
            # 清理之前的临时文件
            if st.session_state.current_data:
                cleanup_temp_files(st.session_state.current_data)
            
            # 显示加载状态
            with st.spinner('正在加载文件...'):
                st.session_state.current_data = create_data_from_uploaded_files(uploaded_files)
                st.session_state.uploaded_file_names = current_file_names
            
            st.success("文件加载完成！")
        
        data = st.session_state.current_data
        
        # 检查是否包含必要的文件
        has_necessary_files = data.get('report') is not None and data.get('image') is not None
        
        if has_necessary_files:
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
                display_main_interface(data, selected_model, username)
            else:
                st.error("未找到任何模型预测文件 (*_predict.json)")
        else:
            st.error("上传的文件不包含完整的病例数据，请确保包含图像文件和报告文件")
            
            # 显示调试信息
            with st.expander("调试信息"):
                st.write("找到的文件:", list(data.keys()))
                if 'report' not in data:
                    st.error("缺少 report.json 文件")
                if 'image' not in data:
                    st.error("缺少图像文件 (image_*.jpg 或 image_*.png)")
    else:
        # 清理临时数据
        if st.session_state.current_data:
            cleanup_temp_files(st.session_state.current_data)
            st.session_state.current_data = None
        
        st.info("💡 请上传病例文件夹文件开始评估")

def display_main_interface(data, selected_model, username):
    """显示主界面"""
    
    # 使用从数据中提取的病例名称
    case_name = data.get('case_name', 'unknown_case')
    
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
    st.markdown(f"**当前病例:** {case_name} <span class='status-badge {status_class}'>{status_text}</span>", unsafe_allow_html=True)
    
    # 创建三列布局：图像、报告、打分系统
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # 图像显示
        if 'image' in data and os.path.exists(data['image']):
            with st.expander("🖼️ 医学图像", expanded=True):
                try:
                    # 使用PIL打开图像以确保兼容性
                    image = Image.open(data['image'])
                    st.image(image, caption="胸部X光片", use_container_width=True)
                except Exception as e:
                    st.error(f"图像加载失败: {e}")
                    # 显示调试信息
                    st.write(f"图像路径: {data['image']}")
                    st.write(f"文件存在: {os.path.exists(data['image'])}")
        else:
            st.warning("未找到图像文件")
            if 'image' in data:
                st.write(f"图像路径: {data['image']}")
    
    with col2:
        # 原始报告显示
        if 'report' in data:
            st.markdown('<div class="section-title">📋 原始报告</div>', unsafe_allow_html=True)
            
            findings = data['report'].get('findings', '')
            impression = data['report'].get('impression', '')
            
            # Findings部分
            st.markdown("**Findings:**")
            findings_container = st.container()
            with findings_container:
                st.text_area(
                    "Findings内容",
                    value=findings,
                    height=140,
                    key="original_findings",
                    label_visibility="collapsed"
                )
            
            # Impression部分
            st.markdown("**Impression:**")
            impression_container = st.container()
            with impression_container:
                st.text_area(
                    "Impression内容",
                    value=impression,
                    height=140,
                    key="original_impression",
                    label_visibility="collapsed"
                )
        
        # 预测报告显示
        if selected_model in data.get('models', {}):
            model_data = data['models'][selected_model]
            
            st.markdown('<div class="section-title">🤖 模型预测报告</div>', unsafe_allow_html=True)
            
            model_findings = model_data.get('findings', '')
            model_impression = model_data.get('impression', '')
            
            # 模型Findings部分
            st.markdown("**Findings:**")
            model_findings_container = st.container()
            with model_findings_container:
                st.text_area(
                    "模型Findings内容",
                    value=model_findings,
                    height=140,
                    key="model_findings",
                    label_visibility="collapsed"
                )
            
            # 模型Impression部分
            st.markdown("**Impression:**")
            model_impression_container = st.container()
            with model_impression_container:
                st.text_area(
                    "模型Impression内容",
                    value=model_impression,
                    height=140,
                    key="model_impression",
                    label_visibility="collapsed"
                )
    
    with col3:
        # 用户名验证
        if not username or not username.strip():
            st.warning("⚠️ 请输入用户名后才能进行评分")
            return
        
        # 打分系统
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
            label_visibility="collapsed"
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
            - 可能只有一些阴性描述是相同的实现分类精度测试
            
            **0分 - 不可接受**
            - 所描述的信息完全没有重叠
            """)
        
        # 准备保存的数据
        review_data = {
            "model_name": selected_model,
            "peer_score": peer_score,
            "timestamp": str(Path().cwd()),
            "case_name": data.get('case_name', 'unknown_case')
        }
        
        # 将数据转换为JSON字符串
        json_data = json.dumps(review_data, ensure_ascii=False, indent=2)
        
        # 生成文件名
        review_number = 0
        if selected_model in data.get('reviews', {}):
            current_review = data['reviews'][selected_model]
            if current_review.get('username') == username and 'review_number' in current_review:
                review_number = current_review.get('review_number', 0) + 1
        
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
