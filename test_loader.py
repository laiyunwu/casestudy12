import os
import sys
# 添加app目录到路径
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from app.utils.data_loader import load_case2_data

# 加载case2数据
data = load_case2_data()

# 打印结果检查
print("加载的数据结构:")
for key, df in data.items():
    print(f"\n{key} 表格信息:")
    print(f"列名: {df.columns.tolist()}")
    print(f"行数: {len(df)}")
    print("前3行数据:")
    print(df.head(3)) 