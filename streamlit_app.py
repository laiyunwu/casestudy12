"""
Streamlit应用主入口点
"""
import os
import sys
import shutil

# 将当前目录添加到Python路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPT_DIR)

# 确保数据目录存在并可访问
def ensure_data_directories():
    """确保所有必需的数据目录存在且可访问"""
    # case1数据目录
    case1_data_dir = os.path.join(SCRIPT_DIR, "case1", "data")
    os.makedirs(case1_data_dir, exist_ok=True)
    
    # case2数据目录
    case2_data_dir = os.path.join(SCRIPT_DIR, "case2", "data")
    os.makedirs(case2_data_dir, exist_ok=True)
    
    # 检查和复制示例数据文件 - 如果源文件存在且目标不存在或已过期
    example_csv = os.path.join(SCRIPT_DIR, "case2", "data", "case2_example.csv")
    if not os.path.exists(example_csv):
        # 尝试从其他位置复制文件
        src_paths = [
            "/Users/yanzhenghui/yun_test/project/case2/data/case2_example.csv",
            "/Users/yanzhenghui/yun_test/case2/data/case2_example.csv",
            os.path.join(SCRIPT_DIR, "..", "case2", "data", "case2_example.csv")
        ]
        
        for src_path in src_paths:
            if os.path.exists(src_path):
                print(f"复制数据文件从 {src_path} 到 {example_csv}")
                try:
                    shutil.copy2(src_path, example_csv)
                    print(f"复制成功: {example_csv}")
                    break
                except Exception as e:
                    print(f"复制文件出错: {str(e)}")
    
    return {
        "case1_data": case1_data_dir,
        "case2_data": case2_data_dir
    }

# 确保数据目录存在
data_dirs = ensure_data_directories()
print(f"数据目录: {data_dirs}")

# 运行Streamlit应用
if __name__ == "__main__":
    import streamlit.web.cli as stcli
    import sys
    
    sys.argv = ["streamlit", "run", os.path.join(SCRIPT_DIR, "app", "app.py")]
    sys.exit(stcli.main()) 