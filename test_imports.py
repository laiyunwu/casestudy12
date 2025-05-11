"""
测试导入是否正常工作
"""
import sys
print(f"Python 路径: {sys.path}")

try:
    # 测试绝对导入
    print("\n测试绝对导入:")
    from app.utils.data_loader import load_case2_data
    print("✓ 成功导入 load_case2_data")
    
    from app.utils.supply_optimizer import optimize_supply_allocation
    print("✓ 成功导入 optimize_supply_allocation")
    
    print("\n导入测试成功完成!")
except Exception as e:
    print(f"✗ 导入错误: {str(e)}")
    
print("\n建议修复:")
print("1. 确保__init__.py文件存在于app目录和其子目录中")
print("2. 在pages模块中使用相对导入 (from ..utils import ...)")
print("3. 在运行Streamlit应用时使用正确的工作目录") 