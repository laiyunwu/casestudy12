"""
验证 CSV 文件内容
"""
import os
import pandas as pd
import time

def read_csv_content(file_path):
    """读取并显示 CSV 文件内容"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return
    
    print(f"\n文件: {file_path}")
    print(f"大小: {os.path.getsize(file_path)} 字节")
    print(f"修改时间: {time.ctime(os.path.getmtime(file_path))}")
    
    # 读取文件内容
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        print("\n文件内容:")
        print(content)
    except Exception as e:
        print(f"读取文件出错: {str(e)}")
    
    # 尝试使用 pandas 解析
    try:
        # 忽略注释行和空行
        df = pd.read_csv(file_path, comment='#', skip_blank_lines=True)
        print("\nPandas 解析结果:")
        print(df)
    except Exception as e:
        print(f"Pandas 解析出错: {str(e)}")

if __name__ == "__main__":
    # 检查多个可能的路径
    paths = [
        "case2/data/case2_example.csv",  # 相对于当前目录
        "../case2/data/case2_example.csv",  # 相对于上级目录
        # 绝对路径
        "/Users/yanzhenghui/yun_test/case2/data/case2_example.csv",
        "/Users/yanzhenghui/yun_test/project/case2/data/case2_example.csv"
    ]
    
    for path in paths:
        if os.path.exists(path):
            read_csv_content(path)

    # 在 case2/data 目录下查找所有 CSV 文件
    try:
        csv_files = []
        for root, dirs, files in os.walk("case2"):
            for file in files:
                if file.endswith(".csv"):
                    csv_files.append(os.path.join(root, file))
        
        if csv_files:
            print(f"\n找到 {len(csv_files)} 个 CSV 文件:")
            for file in csv_files:
                print(f"- {file}")
        else:
            print("\n未找到 CSV 文件")
    except Exception as e:
        print(f"查找 CSV 文件出错: {str(e)}") 