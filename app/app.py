import streamlit as st
import pandas as pd
import numpy as np
import os
import sys

# 禁用缓存
st.cache_data.clear()
st.cache_resource.clear()

# 在每次页面加载时强制重新执行
os.environ['STREAMLIT_SERVER_ENABLE_STATIC_SERVING'] = 'false'

# 将当前目录添加到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(current_dir))

# 设置页面配置
st.set_page_config(
    page_title="供应链分析与优化",
    page_icon="📊",
    layout="wide"
)

def main():
    # 侧边栏导航
    st.sidebar.title("导航")
    
    # 添加项目背景信息
    with st.sidebar.expander("项目背景", expanded=False):
        st.markdown("""
        ### 供应链分析与优化
        
        本项目是一个供应链分析与优化解决方案，包含两个案例：
        
        1. **案例1**: 销售预测分析
        2. **案例2**: 供应分配优化
        
        每个案例都有其独特的业务挑战和技术解决方案。
        """)
    
    # 主页内容
    st.title("供应链分析与优化")
    st.markdown("""
    这个应用程序演示了供应链分析与优化的两个典型案例:

    1. **销售预测分析**: 基于历史数据进行销售趋势预测
    2. **供应分配优化**: 在有限供应条件下最优化产品分配
    """)
    
    # 显示数据源时间
    try:
        case2_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "case2", "data", "case2_example.csv")
        if os.path.exists(case2_path):
            mod_time = os.path.getmtime(case2_path)
            from datetime import datetime
            mod_time_str = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
            st.info(f"数据源最后更新时间: {mod_time_str}")
    except Exception as e:
        st.error(f"读取数据源信息时出错: {str(e)}")
    
    # 添加刷新按钮
    if st.button("🔄 刷新页面"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.experimental_rerun()
    
    # 案例概述
    st.header("案例概述")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("案例1：销售预测分析")
        st.write("""
        本案例涉及基于历史数据进行销售趋势预测。
        
        **挑战点**:
        - 分析历史销售数据的趋势和模式
        - 考虑季节性、价格和地区差异等因素
        - 构建准确的销售预测模型
        
        使用先进的时间序列预测方法，结合产品特性和地区因素，提供了准确的销售预测。
        """)
        # 使用直接链接替代page_link
        if st.button("查看案例1：销售预测分析 📈"):
            st.switch_page("pages/case1_app.py")
        
    with col2:
        st.subheader("案例2：供应分配优化")
        st.write("""
        本案例涉及在有限资源约束下，优化多产品线在不同地区和销售渠道的分配。
        
        **挑战点**:
        - 分析供应约束和需求预测的关系
        - 考虑不同地区和渠道的业务优先级
        - 最大化整体销售额同时满足关键业务约束
        
        使用线性规划方法，构建了一个优化模型，能够在满足业务约束的情况下实现最佳资源分配。
        """)
        # 使用直接链接替代page_link
        if st.button("查看案例2：供应分配优化 🔄"):
            st.switch_page("pages/case2_app.py")
    
    # 技术栈概述
    st.header("使用的技术栈")
    st.write("""
    - **Python**: 核心编程语言
    - **Pandas & NumPy**: 数据处理和分析
    - **Scikit-learn**: 机器学习模型构建
    - **Prophet**: 时间序列预测 (案例1)
    - **PuLP**: 线性规划和优化 (案例2)
    - **Streamlit**: 交互式数据可视化仪表板
    - **Matplotlib & Seaborn**: 数据可视化
    """)

if __name__ == "__main__":
    main() 