import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import sys
import os
from pathlib import Path
from datetime import datetime

# 导入路径修复
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(app_dir)
sys.path.append(project_dir)

# 使用相对导入
sys.path.append(os.path.join(project_dir, "app", "utils"))
from data_loader import load_case2_data
from supply_optimizer import optimize_supply_allocation, get_summary_stats

st.set_page_config(page_title="供应分配优化", page_icon="📦", layout="wide")

# 页面标题
st.title("📦 案例2: 供应分配优化")
st.markdown("""
该应用程序使用线性规划模型优化产品的供应分配。通过考虑产品优先级、渠道优先级和区域优先级，
在有限的供应量下最大化满足率。
""")

# 添加刷新按钮，确保读取最新数据
refresh_data = st.button("🔄 刷新数据", help="点击刷新数据，确保读取最新数据")

# 加载数据 - 使用st.experimental_rerun实现强制刷新
with st.spinner("正在加载数据..."):
    # 显示当前数据源路径 - 使用相对于项目根目录的路径
    case2_path = os.path.join(project_dir, "case2", "data", "case2_example.csv")
    
    # 检查这个路径是否存在
    if not os.path.exists(case2_path):
        # 如果不存在，尝试使用相对于当前文件的路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        case2_path = os.path.join(root_dir, "case2", "data", "case2_example.csv")
    
    # 再次检查
    if not os.path.exists(case2_path):
        # 如果仍然不存在，尝试直接在 case2/data 中查找
        possible_paths = [
            "/Users/yanzhenghui/yun_test/case2/data/case2_example.csv",
            "/Users/yanzhenghui/yun_test/project/case2/data/case2_example.csv",
            os.path.abspath("case2/data/case2_example.csv"),
            os.path.abspath("../case2/data/case2_example.csv")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                case2_path = path
                st.success(f"找到文件: {case2_path}")
                break
    
    if os.path.exists(case2_path):
        file_size = os.path.getsize(case2_path)
        st.write(f"文件存在，大小: {file_size} 字节")
        
        # 显示文件前几行内容便于验证
        try:
            with open(case2_path, 'r') as f:
                preview = ''.join(f.readlines()[:10])
                st.code(preview, language="text")
        except Exception as e:
            st.error(f"读取文件预览时出错: {str(e)}")
    else:
        st.error(f"文件不存在: {case2_path}")
        # 尝试列出目录内容
        try:
            dir_path = os.path.dirname(case2_path)
            if os.path.exists(dir_path):
                st.write(f"目录 {dir_path} 内容:")
                st.write(os.listdir(dir_path))
            else:
                st.error(f"目录不存在: {dir_path}")
        except Exception as e:
            st.error(f"列出目录内容时出错: {str(e)}")
    
    data_source_time = None
    try:
        data_source_time = os.path.getmtime(case2_path)
        data_source_time = datetime.fromtimestamp(data_source_time).strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        st.error(f"获取文件修改时间出错: {str(e)}")
    
    if data_source_time:
        st.caption(f"数据源: {case2_path} (最后修改时间: {data_source_time})")
    
    # 加载数据，如果按下刷新按钮，则清除会话状态以确保重新加载
    if refresh_data:
        # 清除可能的缓存数据
        for key in list(st.session_state.keys()):
            if key.startswith('data_'):
                del st.session_state[key]
        st.success("数据已刷新!")
        st.experimental_rerun()  # 重新运行应用，确保数据被重新加载
    
    try:
        # 加载数据
        st.write("正在加载数据...")
        data = load_case2_data(case2_path)
        st.write(f"数据加载完成，表数量: {len(data)}")
        
        # 打印加载的数据概况
        for key, df in data.items():
            st.write(f"{key}: {len(df)} 行, 列: {', '.join(df.columns)}")
    except Exception as e:
        st.error(f"加载数据时出错: {str(e)}")
        import traceback
        st.code(traceback.format_exc(), language="python")

# 边栏: 优化参数设置
st.sidebar.header("优化参数设置")

# 产品优先级设置
st.sidebar.subheader("产品优先级")
product_priorities = {}
for product in data["demand_forecast"]["product"].unique():
    default_priority = 8 if "plus" in product.lower() else (3 if "mini" in product.lower() else 5)
    product_priorities[product] = st.sidebar.slider(
        f"{product} 优先级", 
        min_value=1, 
        max_value=10, 
        value=default_priority,
        help="值越大，优先级越高"
    )

# 渠道优先级设置
st.sidebar.subheader("渠道优先级")
channel_priorities = {
    'Default': 1 # 默认渠道优先级低
}
for channel in data["customer_demand"]["channel"].unique():
    default_priority = 5
    if "online" in channel.lower():
        default_priority = 7
    elif "reseller" in channel.lower():
        default_priority = 8
        
    channel_priorities[channel] = st.sidebar.slider(
        f"{channel} 优先级", 
        min_value=1, 
        max_value=10, 
        value=default_priority,
        help="值越大，优先级越高"
    )

# 区域优先级设置
st.sidebar.subheader("区域优先级")
region_priorities = {
    'Default': 1 # 默认区域优先级低
}
for region in data["customer_demand"]["region"].unique():
    region_priorities[region] = st.sidebar.slider(
        f"{region} 优先级", 
        min_value=1, 
        max_value=10, 
        value=1,
        help="值越大，优先级越高"
    )

# 特殊约束设置
st.sidebar.subheader("特殊约束")
add_special_constraint = st.sidebar.checkbox("添加特殊约束", value=True)

special_constraints = []
if add_special_constraint:
    weeks = [col for col in data["demand_forecast"].columns if "wk" in col.lower() or "week" in col.lower()]
    
    # 允许用户选择特殊约束
    constraint_product = st.sidebar.selectbox(
        "选择产品", 
        options=data["demand_forecast"]["product"].unique()
    )
    constraint_channel = st.sidebar.selectbox(
        "选择渠道", 
        options=data["customer_demand"]["channel"].unique()
    )
    constraint_region = st.sidebar.selectbox(
        "选择区域", 
        options=data["customer_demand"]["region"].unique()
    )
    constraint_week = st.sidebar.selectbox(
        "选择周", 
        options=weeks
    )
    satisfaction_rate = st.sidebar.slider(
        "满足率", 
        min_value=0.0, 
        max_value=1.0, 
        value=1.0,
        step=0.05
    )
    
    special_constraints.append({
        "product": constraint_product,
        "channel": constraint_channel,
        "region": constraint_region,
        "week": constraint_week,
        "satisfaction_rate": satisfaction_rate
    })
    
    st.sidebar.info(f"已添加约束: {constraint_product} 在 {constraint_region} 区域的 {constraint_channel} 渠道在第 {constraint_week} 周的满足率 >= {satisfaction_rate*100:.0f}%")

# 主内容区: 数据展示和优化结果
# 显示原始数据
st.subheader("输入数据概览")

tab1, tab2, tab3, tab4 = st.tabs(["总供应量", "实际生产量", "需求预测", "客户需求"])

with tab1:
    st.dataframe(data["total_supply"])
    
    # 可视化总供应量
    chart_data = data["total_supply"].copy()
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('week:N', title='周'),
        y=alt.Y('total_supply:Q', title='总供应量'),
        color=alt.value('#1f77b4')
    ).properties(
        title='每周总供应量',
        width=600,
        height=300
    )
    st.altair_chart(chart, use_container_width=True)

with tab2:
    st.dataframe(data["actual_build"])
    
    # 可视化实际生产量
    chart_data = data["actual_build"].copy()
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('product:N', title='产品'),
        y=alt.Y('actual_build:Q', title='实际生产量'),
        color='product:N'
    ).properties(
        title='产品实际生产量',
        width=600,
        height=300
    )
    st.altair_chart(chart, use_container_width=True)

with tab3:
    st.dataframe(data["demand_forecast"])
    
    # 将数据转化为长格式用于可视化
    df_long = pd.melt(
        data["demand_forecast"], 
        id_vars=['product'], 
        value_vars=[col for col in data["demand_forecast"].columns if col != 'product'],
        var_name='week', 
        value_name='demand'
    )
    
    # 可视化需求预测
    chart = alt.Chart(df_long).mark_line(point=True).encode(
        x=alt.X('week:N', title='周'),
        y=alt.Y('demand:Q', title='需求量'),
        color='product:N',
        tooltip=['product', 'week', 'demand']
    ).properties(
        title='产品需求预测',
        width=600,
        height=300
    )
    st.altair_chart(chart, use_container_width=True)

with tab4:
    st.dataframe(data["customer_demand"])
    
    # 将数据转化为长格式用于可视化
    df_long = pd.melt(
        data["customer_demand"], 
        id_vars=['channel', 'region'], 
        value_vars=[col for col in data["customer_demand"].columns if col not in ['channel', 'region']],
        var_name='week', 
        value_name='demand'
    )
    
    # 可视化客户需求 - 按渠道
    chart1 = alt.Chart(df_long).mark_bar().encode(
        x=alt.X('week:N', title='周'),
        y=alt.Y('sum(demand):Q', title='需求总量'),
        color='channel:N',
        tooltip=['channel', 'week', 'sum(demand)']
    ).properties(
        title='按渠道的客户需求',
        width=600,
        height=300
    )
    
    # 可视化客户需求 - 按区域
    chart2 = alt.Chart(df_long).mark_bar().encode(
        x=alt.X('week:N', title='周'),
        y=alt.Y('sum(demand):Q', title='需求总量'),
        color='region:N',
        tooltip=['region', 'week', 'sum(demand)']
    ).properties(
        title='按区域的客户需求',
        width=600,
        height=300
    )
    
    st.altair_chart(chart1, use_container_width=True)
    st.altair_chart(chart2, use_container_width=True)

# 运行优化
st.subheader("供应分配优化")
if st.button("运行优化"):
    with st.spinner("正在优化供应分配..."):
        # 运行优化模型
        result_df = optimize_supply_allocation(
            data, 
            product_priorities=product_priorities,
            channel_priorities=channel_priorities,
            region_priorities=region_priorities,
            special_constraints=special_constraints
        )
        
        if not result_df.empty:
            # 计算汇总统计
            summary_stats = get_summary_stats(result_df)
            
            # 显示优化结果
            st.success("优化完成!")
            
            # 总体满足率
            overall_satisfaction = (result_df['allocation'].sum() / result_df['demand'].sum()) * 100
            st.metric("总体需求满足率", f"{overall_satisfaction:.2f}%")
            
            # 展示详细结果
            st.subheader("优化结果详情")
            
            # 创建结果标签页
            result_tab1, result_tab2, result_tab3, result_tab4 = st.tabs([
                "按产品汇总", "按周汇总", "按渠道和区域汇总", "详细分配结果"
            ])
            
            with result_tab1:
                if "product" in summary_stats:
                    # 格式化百分比
                    formatted_df = summary_stats["product"].copy()
                    formatted_df["satisfaction"] = formatted_df["satisfaction"].apply(lambda x: f"{x*100:.2f}%")
                    st.dataframe(formatted_df)
                    
                    # 可视化 - 按产品的满足率
                    chart_data = summary_stats["product"].reset_index()
                    chart_data["satisfaction_pct"] = chart_data["satisfaction"] * 100
                    
                    chart = alt.Chart(chart_data).mark_bar().encode(
                        x=alt.X('product:N', title='产品'),
                        y=alt.Y('satisfaction_pct:Q', title='满足率 (%)'),
                        color='product:N'
                    ).properties(
                        title='按产品的需求满足率',
                        width=600,
                        height=300
                    )
                    st.altair_chart(chart, use_container_width=True)
            
            with result_tab2:
                if "product_week" in summary_stats:
                    # 重置索引用于显示
                    week_df = summary_stats["product_week"].reset_index()
                    week_df["satisfaction_pct"] = week_df["satisfaction"] * 100
                    
                    # 可视化 - 按产品和周的满足率
                    chart = alt.Chart(week_df).mark_line(point=True).encode(
                        x=alt.X('week:N', title='周'),
                        y=alt.Y('satisfaction_pct:Q', title='满足率 (%)'),
                        color='product:N',
                        tooltip=['product', 'week', 'demand', 'allocation', 'satisfaction_pct']
                    ).properties(
                        title='按产品和周的需求满足率',
                        width=600,
                        height=300
                    )
                    st.altair_chart(chart, use_container_width=True)
                    
                    # 可视化 - 按产品和周的需求与分配对比
                    chart_data = week_df.melt(
                        id_vars=['product', 'week'], 
                        value_vars=['demand', 'allocation'],
                        var_name='类型', 
                        value_name='数量'
                    )
                    
                    chart = alt.Chart(chart_data).mark_bar().encode(
                        x=alt.X('week:N', title='周'),
                        y=alt.Y('数量:Q'),
                        color='类型:N',
                        column='product:N'
                    ).properties(
                        title='按产品和周的需求与分配对比',
                        width=150,
                        height=300
                    )
                    st.altair_chart(chart)
            
            with result_tab3:
                if "channel_region" in summary_stats:
                    # 重置索引用于显示
                    cr_df = summary_stats["channel_region"].reset_index()
                    cr_df["satisfaction_pct"] = cr_df["satisfaction"] * 100
                    
                    # 可视化 - 按渠道和区域的满足率
                    chart = alt.Chart(cr_df).mark_bar().encode(
                        x=alt.X('channel:N', title='渠道'),
                        y=alt.Y('satisfaction_pct:Q', title='满足率 (%)'),
                        color='region:N',
                        column='product:N',
                        tooltip=['product', 'channel', 'region', 'demand', 'allocation', 'satisfaction_pct']
                    ).properties(
                        title='按渠道和区域的需求满足率',
                        width=150,
                        height=300
                    )
                    st.altair_chart(chart)
            
            with result_tab4:
                # 显示详细的分配结果
                st.dataframe(result_df)
        else:
            st.error("优化未产生有效结果，请检查输入数据和约束条件。")
else:
    st.info("点击'运行优化'按钮开始供应分配优化计算。")

# 添加解释说明
with st.expander("关于供应分配优化"):
    st.markdown("""
    ### 供应分配优化模型说明
    
    该模型使用线性规划来优化有限供应量下的产品分配，主要考虑以下因素：
    
    1. **目标函数**: 最大化优先级加权的需求满足率
    2. **决策变量**: 每个产品在每个渠道、区域和周的分配量
    3. **约束条件**:
       - 每周总分配量不超过总供应量
       - 分配量不超过需求量
       - 可以添加特殊约束，要求某些特定组合的满足率达到指定值
    
    ### 使用指南
    
    1. 在左侧面板调整产品、渠道和区域的优先级权重
    2. 可选择添加特殊约束，确保关键需求得到满足
    3. 点击"运行优化"按钮执行计算
    4. 查看不同维度的结果分析和可视化
    
    ### 优先级说明
    
    优先级越高，在供应有限的情况下，该维度将获得更高的分配比例。复合优先级计算为:
    
    `优先级 = 产品优先级 × 渠道优先级 × 区域优先级`
    """) 