"""
强制更新 CSV 文件
"""
import os
import time
import shutil

def update_file(file_path):
    """通过创建新文件并替换的方式更新文件"""
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return False
    
    # 读取内容
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 添加时间戳注释
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if "# 注意：这是CSV格式的示例数据" in content:
        content = content.replace(
            "# 注意：这是CSV格式的示例数据", 
            f"# 注意：这是CSV格式的示例数据 - 更新于 {timestamp}"
        )
    else:
        # 在第二行添加时间戳
        lines = content.split('\n')
        if len(lines) > 1:
            lines.insert(1, f"# 更新时间: {timestamp}")
            content = '\n'.join(lines)
    
    # 创建临时文件
    temp_path = f"{file_path}.new"
    with open(temp_path, 'w') as f:
        f.write(content)
    
    # 备份原文件
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    
    # 替换原文件
    os.remove(file_path)
    os.rename(temp_path, file_path)
    
    # 更新文件访问和修改时间
    os.utime(file_path, None)
    
    print(f"已更新文件: {file_path}")
    print(f"备份文件: {backup_path}")
    return True

if __name__ == "__main__":
    # 更新 case2_example.csv 文件
    file_path = "case2/data/case2_example.csv"
    if os.path.exists(file_path):
        update_file(file_path)
    else:
        print(f"找不到文件: {file_path}")
        
        # 尝试搜索其他位置
        other_paths = [
            "../case2/data/case2_example.csv",
            "/Users/yanzhenghui/yun_test/case2/data/case2_example.csv",
            "/Users/yanzhenghui/yun_test/project/case2/data/case2_example.csv"
        ]
        
        for path in other_paths:
            if os.path.exists(path):
                print(f"找到文件: {path}")
                update_file(path)
                break 