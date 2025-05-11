import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import io
import pulp
from datetime import datetime, timedelta

# 导入路径修复
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(app_dir)
sys.path.append(project_dir)

# 使用相对导入
sys.path.append(os.path.join(project_dir, "app", "utils"))
from data_loader import load_case2_data, validate_case2_data

# 设置页面配置
st.set_page_config(
    page_title="案例2: 供应分配优化",
    page_icon="🔄",
    layout="wide"
)

# 页面标题
st.title("Case 2: Supply Allocation Optimization")

# 加载数据
with st.spinner("Loading data..."):
    data_dict = load_case2_data()
    if not validate_case2_data(data_dict):
        st.error("Unable to load valid supply allocation data")
        st.stop()
    
    # 获取各个数据表
    total_supply = data_dict.get('total_supply')
    actual_build = data_dict.get('actual_build')
    demand_forecast = data_dict.get('demand_forecast')
    customer_demand = data_dict.get('customer_demand')

# 数据概览
st.header("1. Data Overview")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1.1 Total Supply")
    st.dataframe(total_supply, use_container_width=True)

    st.subheader("1.2 Actual Production")
    st.dataframe(actual_build, use_container_width=True)

with col2:
    st.subheader("1.3 Demand Forecast")
    st.dataframe(demand_forecast, use_container_width=True)
    
    st.subheader("1.4 Customer Demand")
    st.dataframe(customer_demand, use_container_width=True)

# 供需分析
st.header("2. Supply and Demand Analysis")

# 2.1 总体供需对比
st.subheader("2.1 Overall Supply and Demand Comparison")

# 处理数据格式以便于分析
# 宽格式转长格式
weeks = [col for col in demand_forecast.columns if col != 'product']

# 计算每周总需求
total_demand_by_week = {}
for week in weeks:
    total_demand_by_week[week] = demand_forecast[week].sum()

# 创建总供需对比数据框
supply_demand_df = pd.DataFrame({
    'Week': total_supply['week'],
    'Total Supply': total_supply['total_supply'],
    'Total Demand': [total_demand_by_week.get(week, 0) for week in total_supply['week']]
})

# 计算供需差异
supply_demand_df['Supply-Demand Gap'] = supply_demand_df['Total Supply'] - supply_demand_df['Total Demand']
supply_demand_df['Supply-Demand Ratio'] = supply_demand_df['Total Supply'] / supply_demand_df['Total Demand']

# 展示供需对比表格
st.dataframe(supply_demand_df, use_container_width=True)

# 供需对比图表
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=supply_demand_df, x='Week', y='Total Supply', color='blue', alpha=0.7, label='Total Supply', ax=ax)
sns.barplot(data=supply_demand_df, x='Week', y='Total Demand', color='red', alpha=0.7, label='Total Demand', ax=ax)
plt.title('Weekly Total Supply vs Total Demand')
plt.legend()
st.pyplot(fig)

# 2.2 按产品的需求分析
st.subheader("2.2 Demand Analysis by Product")

# 转换为长格式以便绘图
demand_long = pd.melt(
    demand_forecast, 
    id_vars=['product'], 
    value_vars=weeks,
    var_name='Week', 
    value_name='Demand'
)

# 按产品绘制需求趋势图
fig, ax = plt.subplots(figsize=(12, 6))
sns.lineplot(data=demand_long, x='Week', y='Demand', hue='product', marker='o', ax=ax)
plt.title('Product Demand Trends')
plt.xticks(rotation=45)
plt.grid(True, linestyle='--', alpha=0.7)
st.pyplot(fig)

# 2.3 按地区和渠道的需求分析
st.subheader("2.3 Demand Analysis by Region and Channel")

# 转换客户需求数据为长格式
customer_long = pd.melt(
    customer_demand, 
    id_vars=['channel', 'region'], 
    value_vars=[col for col in customer_demand.columns if col.startswith('Jan-')],
    var_name='Week', 
    value_name='Demand'
)

# 按地区分组求和
region_demand = customer_long.groupby(['region', 'Week'])['Demand'].sum().reset_index()

# 按渠道分组求和
channel_demand = customer_long.groupby(['channel', 'Week'])['Demand'].sum().reset_index()

col1, col2 = st.columns(2)

with col1:
    # 按地区绘制需求图
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=region_demand, x='Week', y='Demand', hue='region', ax=ax)
    plt.title('Demand Distribution by Region')
    plt.xticks(rotation=45)
    st.pyplot(fig)

with col2:
    # 按渠道绘制需求图
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=channel_demand, x='Week', y='Demand', hue='channel', ax=ax)
    plt.title('Demand Distribution by Sales Channel')
    plt.xticks(rotation=45)
    st.pyplot(fig)

# 优化模型
st.header("3. Supply Allocation Optimization Model")

st.subheader("3.1 Optimization Method")
st.write("""
This case uses linear programming to optimize product supply allocation across different channels and regions. The main steps include:

1. **Objective Function**: Maximize total sales
2. **Constraints**:
   - Weekly total supply limits
   - Product production capacity constraints
   - Minimum demand priority satisfaction
   - Special constraint for PAC region in Week 4
3. **Decision Variables**: Allocation amount for each product in each week, region, and channel
""")

# 3.2 优化设置
st.subheader("3.2 Optimization Parameters")

# 侧边栏 - 优化参数
st.sidebar.header("Optimization Parameters")

# 选择要优化的周
target_week = st.sidebar.selectbox(
    "Select the Week to Optimize", 
    options=["Jan-Wk2", "Jan-Wk3", "Jan-Wk4", "Jan-Wk5"],
    index=2  # 默认选择Jan-Wk4
)

# 产品优先级
product_priorities = {}
st.sidebar.subheader("Product Priority (1-10)")
for product in demand_forecast['product']:
    product_priorities[product] = st.sidebar.slider(
        f"{product} Priority", 
        min_value=1, 
        max_value=10, 
        value=5
    )

# 地区优先级
region_priorities = {}
st.sidebar.subheader("Region Priority (1-10)")
for region in customer_demand['region'].unique():
    region_priorities[region] = st.sidebar.slider(
        f"{region} Priority", 
        min_value=1, 
        max_value=10, 
        value=5 if region != "PAC" else 8  # PAC默认较高优先级
    )

# 渠道优先级
channel_priorities = {}
st.sidebar.subheader("Channel Priority (1-10)")
for channel in customer_demand['channel'].unique():
    channel_priorities[channel] = st.sidebar.slider(
        f"{channel} Priority", 
        min_value=1, 
        max_value=10, 
        value=5
    )

# 运行优化按钮
run_optimization = st.sidebar.button("Run Optimization")

# 3.3 优化结果
st.subheader("3.3 Optimization Results")

# 运行优化模型并显示结果
if run_optimization:
    with st.spinner("Calculating Optimal Allocation..."):
        # 获取特定周的数据
        week_supply = total_supply[total_supply['week'] == target_week]['total_supply'].values[0]
        week_products = demand_forecast['product'].tolist()
        week_product_demand = {}
        for product in week_products:
            week_product_demand[product] = demand_forecast[demand_forecast['product'] == product][target_week].values[0]
            
        # 准备客户需求数据
        customer_week = customer_demand[['channel', 'region', target_week]]
        customer_week = customer_week.rename(columns={target_week: 'demand'})
        
        # 创建线性规划模型
        model = pulp.LpProblem("Supply_Allocation", pulp.LpMaximize)
        
        # 决策变量 - 产品在每个渠道-地区的分配
        allocation = {}
        for product in week_products:
            for _, row in customer_week.iterrows():
                channel, region = row['channel'], row['region']
                allocation[(product, channel, region)] = pulp.LpVariable(
                    f"Alloc_{product}_{channel}_{region}", 
                    lowBound=0,
                    cat='Integer'
                )
        
        # 目标函数 - 最大化加权分配总量
        objective = pulp.lpSum([
            allocation[(product, channel, region)] * 
            product_priorities[product] * 
            region_priorities[region] * 
            channel_priorities[channel]
            for product in week_products
            for channel in customer_demand['channel'].unique()
            for region in customer_demand['region'].unique()
        ])
        model += objective
        
        # 约束1: 总供应量约束
        model += (
            pulp.lpSum([
                allocation[(product, channel, region)]
                for product in week_products
                for channel in customer_demand['channel'].unique()
                for region in customer_demand['region'].unique()
            ]) <= week_supply,
            "Total_Supply_Constraint"
        )
        
        # 约束2: 产品需求约束 - 每个产品的分配不超过其总需求
        for product in week_products:
            model += (
                pulp.lpSum([
                    allocation[(product, channel, region)]
                    for channel in customer_demand['channel'].unique()
                    for region in customer_demand['region'].unique()
                ]) <= week_product_demand[product],
                f"Product_Demand_{product}"
            )
        
        # 约束3: 客户需求约束 - 每个渠道-地区的所有产品分配不超过客户需求
        for _, row in customer_week.iterrows():
            channel, region, demand = row['channel'], row['region'], row['demand']
            model += (
                pulp.lpSum([
                    allocation[(product, channel, region)]
                    for product in week_products
                ]) <= demand,
                f"Customer_Demand_{channel}_{region}"
            )
        
        # 约束4: 如果是Jan-Wk4，添加PAC地区的特殊约束
        if target_week == "Jan-Wk4":
            # PAC地区在Jan-Wk4的总分配至少是总供应量的30%
            model += (
                pulp.lpSum([
                    allocation[(product, channel, "PAC")]
                    for product in week_products
                    for channel in customer_demand['channel'].unique()
                ]) >= 0.3 * week_supply,
                "PAC_Special_Constraint"
            )
        
        # 求解模型
        model.solve(pulp.PULP_CBC_CMD(msg=False))
        
        # 检查求解状态
        if pulp.LpStatus[model.status] == 'Optimal':
            # 汇总结果
            results = []
            for product in week_products:
                for channel in customer_demand['channel'].unique():
                    for region in customer_demand['region'].unique():
                        value = allocation[(product, channel, region)].value()
                        if value is not None and value > 0:  # 只包含非零分配
                            results.append({
                                'Product': product,
                                'Channel': channel,
                                'Region': region,
                                'Allocated Quantity': int(value)
                            })
            
            # 转换为DataFrame
            results_df = pd.DataFrame(results)
            
            # 显示结果
            st.success(f"Optimal Allocation Found! Total Allocated Quantity: {int(pulp.value(model.objective))}")
            
            # 结果数据透视表
            if not results_df.empty:
                # 按产品显示
                st.write("Allocation Results by Product:")
                product_pivot = pd.pivot_table(
                    results_df,
                    values='Allocated Quantity',
                    index=['Product'],
                    columns=['Region'],
                    aggfunc='sum',
                    fill_value=0
                )
                st.dataframe(product_pivot, use_container_width=True)
                
                # 按渠道和地区显示
                st.write("Allocation Results by Channel and Region:")
                channel_region_pivot = pd.pivot_table(
                    results_df,
                    values='Allocated Quantity',
                    index=['Channel'],
                    columns=['Region'],
                    aggfunc='sum',
                    fill_value=0
                )
                st.dataframe(channel_region_pivot, use_container_width=True)
                
                # 详细分配结果
                st.write("Detailed Allocation Results:")
                st.dataframe(results_df, use_container_width=True)
                
                # 可视化分配结果
                # 按产品和地区的分配
                fig, ax = plt.subplots(figsize=(12, 6))
                product_region_data = results_df.groupby(['Product', 'Region'])['Allocated Quantity'].sum().reset_index()
                sns.barplot(x='Product', y='Allocated Quantity', hue='Region', data=product_region_data, ax=ax)
                plt.title(f'{target_week} Allocation by Product and Region')
                plt.xticks(rotation=45)
                st.pyplot(fig)
                
                # 按渠道的分配
                fig, ax = plt.subplots(figsize=(12, 6))
                channel_data = results_df.groupby(['Channel'])['Allocated Quantity'].sum().reset_index()
                sns.barplot(x='Channel', y='Allocated Quantity', data=channel_data, ax=ax)
                plt.title(f'{target_week} Allocation by Channel')
                st.pyplot(fig)
            else:
                st.warning("No allocation made")
        else:
            st.error(f"Optimization Failed, Status: {pulp.LpStatus[model.status]}")
else:
    st.info("Please set optimization parameters and click 'Run Optimization' to generate allocation")

# 业务建议
st.header("4. Business Suggestions")

st.markdown("""
Based on the results of the supply allocation optimization model, we suggest the following business actions:

1. **Product Strategy**:
   - For products with high demand compared to supply, consider increasing production capacity or exploring alternative products
   - For low demand products, consider adjusting product mix or promotional strategies

2. **Region Allocation Strategy**:
   - The special demand in Week 4 of the PAC region indicates its importance for sales growth, and should be given sufficient attention
   - Allocation to each region should consider its strategic importance and historical sales performance

3. **Channel Strategy**:
   - Evaluate the efficiency and importance of each sales channel and adjust resource allocation accordingly
   - Consider providing more products to efficient channels while not neglecting strategically important channels

4. **Inventory Management**:
   - Based on the optimization model results, plan inventory and logistics needs in advance for each week
   - Communicate with suppliers in advance in periods of supply shortage to ensure supply of key products

5. **Long-term Planning**:
   - Run the optimization model periodically to adjust allocation strategy based on latest data
   - Use historical allocation data and actual sales results to continuously improve prediction and optimization model
""")

# 底部信息
st.sidebar.markdown("---")
st.sidebar.info("This application demonstrates the entire supply allocation optimization process, including data analysis, visualization, and optimization modeling.") 