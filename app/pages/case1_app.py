import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import io
from datetime import datetime, timedelta

# 导入路径修复
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
project_dir = os.path.dirname(app_dir)
sys.path.append(project_dir)

# 使用相对导入 (尝试直接导入，如果不行则用下面的 sys.path.append)
sys.path.append(os.path.join(project_dir, "app", "utils"))
from data_loader import load_case1_data, validate_case1_data
from case1_predictor import generate_sales_forecast # 修改此行

# 顶级排序函数，确保所有图表都能正确使用
def sort_key_date(date_str):
    month_map = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}
    try:
        parts = str(date_str).split('-') #确保输入是字符串
        if len(parts) == 3: # "YYYY-Mon-wkN"
            year_str, month_str, week_str = parts[0], parts[1], parts[2]
            year = int(year_str)
            month_num = month_map.get(month_str, 0)
            week_num = int(week_str.replace('wk',''))
            return (year, month_num, week_num)
        elif len(parts) == 2: # Fallback for "Mon-wkN" (如果原始数据只有月和周)
            month_str, week_str = parts[0], parts[1]
            month_num = month_map.get(month_str, 0)
            week_num = int(week_str.replace('wk',''))
            # 假设一个默认年份或基于当前上下文的年份，这里用0表示无特定年份或最早
            # 在load_case1_data中，这些日期会被赋予年份，所以这里主要是为了稳健性
            return (0, month_num, week_num) 
        else: # Malformed
            return (float('inf'), float('inf'), float('inf')) # 使格式错误的排在最后
    except ValueError: 
        return (float('inf'), float('inf'), float('inf')) 
    except Exception: 
        return (float('inf'), float('inf'), float('inf'))

# 设置页面配置
st.set_page_config(
    page_title="案例1: 销量预测分析",
    page_icon="📈",
    layout="wide"
)

# 页面标题
st.title("Case 1: Sales Forecast Analysis")

# 加载数据
@st.cache_data # 添加缓存以提高性能
def load_data():
    data_dict = load_case1_data()
    if not validate_case1_data(data_dict):
        st.error("无法加载有效的销量预测数据")
        return None
    return data_dict.get('historical_sales')

with st.spinner("正在加载数据..."):
    raw_sales_data = load_data()
    if raw_sales_data is None:
        st.stop()

    # 重命名列以匹配 case1_predictor.py 的期望
    # case1_app.py 中的列: 'product', 'region', 'date', 'sales', 'price'
    # case1_predictor.py 期望: 'Product', 'Region', 'Week', 'Sales' (Price 在 reference_products_info 中)
    sales_data_for_predictor = raw_sales_data.rename(columns={
        'product': 'Product',
        'region': 'Region',
        'date': 'Week', # 'date' 列的格式是 'Sep-wk1', 'Sep-wk2' 等，与 'Week' 语义一致
        'sales': 'Sales'
    })
    # 确保 'Week' 列是字符串类型，如果它是 Categorical，转换它
    if isinstance(sales_data_for_predictor['Week'].dtype, pd.CategoricalDtype): # 修正 DeprecationWarning
        sales_data_for_predictor['Week'] = sales_data_for_predictor['Week'].astype(str)


# 数据概览
st.header("1. Data Overview")

st.subheader("1.1 Dataset Information")
st.write(f"Records: {raw_sales_data.shape[0]} rows, {raw_sales_data.shape[1]} columns")
st.write("Columns: ", ", ".join(raw_sales_data.columns.tolist()))

# 显示前几行数据
st.subheader("1.2 Historical Sales Data Preview")
st.dataframe(raw_sales_data.head(10), use_container_width=True)

# 基本统计信息
st.subheader("1.3 Basic Statistics")
st.dataframe(raw_sales_data.describe(include='all'), use_container_width=True)

# 数据可视化
st.header("2. Data Visualization")

# 产品分布
st.subheader("2.1 Product Sales Distribution")
product_sales = raw_sales_data.groupby('product')['sales'].sum().reset_index()
fig_prod, ax_prod = plt.subplots(figsize=(10, 6))
sns.barplot(data=product_sales, x='product', y='sales', ax=ax_prod)
ax_prod.set_title('Total Sales by Product')
ax_prod.tick_params(axis='x', rotation=45)
st.pyplot(fig_prod)

# 地区分布
st.subheader("2.2 Regional Sales Distribution")
region_sales = raw_sales_data.groupby('region')['sales'].sum().reset_index()
fig_reg, ax_reg = plt.subplots(figsize=(10, 6))
sns.barplot(data=region_sales, x='region', y='sales', ax=ax_reg)
ax_reg.set_title('Total Sales by Region')
st.pyplot(fig_reg)

# 时间趋势分析
st.subheader("2.3 Time Trend Analysis")

# 提取时间信息并按周聚合
# 确保 'date' 列是 Categorical 以便正确排序
if not isinstance(raw_sales_data['date'].dtype, pd.CategoricalDtype):
    unique_sorted_dates = sorted(raw_sales_data['date'].unique(), key=sort_key_date)
    raw_sales_data['date'] = pd.Categorical(raw_sales_data['date'],
                                        categories=unique_sorted_dates,
                                        ordered=True)

time_sales = raw_sales_data.groupby(['date'], observed=True)['sales'].sum().reset_index()

fig_time, ax_time = plt.subplots(figsize=(14, 8))
sns.lineplot(data=time_sales, x='date', y='sales', marker='o', ax=ax_time)
ax_time.set_title('Sales Trend Over Time')
ax_time.tick_params(axis='x', rotation=90)
ax_time.grid(True, linestyle='--', alpha=0.7)
st.pyplot(fig_time)

# 交互式产品和地区选择的时间序列
st.subheader("2.4 Interactive Time Series Analysis")

# 侧边栏 - 过滤条件
st.sidebar.header("Data Filtering for Visualization")
selected_products_viz = st.sidebar.multiselect(
    "Select Products for Visualization",
    options=raw_sales_data['product'].unique(),
    default=raw_sales_data['product'].unique()[0:1] # 默认选择第一个
)

selected_regions_viz = st.sidebar.multiselect(
    "Select Regions for Visualization",
    options=raw_sales_data['region'].unique(),
    default=raw_sales_data['region'].unique()[0:1] # 默认选择第一个
)

# 根据筛选条件过滤数据
if selected_products_viz and selected_regions_viz:
    filtered_data_viz = raw_sales_data[
        (raw_sales_data['product'].isin(selected_products_viz)) & 
        (raw_sales_data['region'].isin(selected_regions_viz))
    ]

    # 按日期和产品聚合
    if not filtered_data_viz.empty:
        # 绘制交互式图表
        pivot_data_viz = filtered_data_viz.pivot_table(
            index='date', 
            columns=['product', 'region'], 
            values='sales',
            aggfunc='sum'
        ).fillna(0)
        
        fig_interact, ax_interact = plt.subplots(figsize=(14, 8))
        pivot_data_viz.plot(ax=ax_interact, marker='o')
        ax_interact.set_title('Sales Trends by Product and Region')
        ax_interact.tick_params(axis='x', rotation=90)
        ax_interact.grid(True, linestyle='--', alpha=0.7)
        ax_interact.legend(title='Product - Region')
        st.pyplot(fig_interact)
    else:
        st.warning("No data for selected products and regions in visualization.")
else:
    st.info("Please select at least one product and one region for interactive visualization.")

# 销量预测模型
st.header("3. Sales Forecasting Model for Superman Plus")

# --- 参数输入 ---
st.subheader("3.1 Prediction Parameters")
product_to_forecast = "Superman Plus" # 固定预测目标
st.write(f"Forecasting sales for: **{product_to_forecast}**")

with st.expander("Adjust Prediction Parameters", expanded=True):
    ref_cols = st.columns(2)
    with ref_cols[0]:
        st.markdown("##### Target Product: Superman Plus")
        target_price = st.number_input("Superman Plus Price", min_value=0.0, value=205.0, step=5.0)
        battery_impact = st.slider("Battery Upgrade Impact (%)", min_value=-20.0, max_value=50.0, value=5.0, step=1.0) / 100.0
        
    with ref_cols[1]:
        st.markdown("##### Launch Impact")
        weeks_launch_impact = st.number_input("Weeks for Launch Impact", min_value=0, max_value=20, value=4, step=1)

    st.markdown("---")
    st.markdown("##### Reference Product Information")
    
    # Princess Plus
    st.markdown("###### Princess Plus")
    pp_cols = st.columns(2)
    pp_price = pp_cols[0].number_input("Princess Plus Price", min_value=0.0, value=180.0, step=5.0, key="pp_price")
    pp_weight = pp_cols[1].slider("Princess Plus Weight for Reference", min_value=0.0, max_value=1.0, value=0.7, step=0.05, key="pp_weight")

    # Dwarf Plus
    st.markdown("###### Dwarf Plus")
    dp_cols = st.columns(2)
    dp_price = dp_cols[0].number_input("Dwarf Plus Price", min_value=0.0, value=120.0, step=5.0, key="dp_price")
    dp_weight = dp_cols[1].slider("Dwarf Plus Weight for Reference", min_value=0.0, max_value=1.0, value=0.3, step=0.05, key="dp_weight")

    # 确保权重和为1的提示或自动调整 (predictor中已包含归一化)
    if not np.isclose(pp_weight + dp_weight, 1.0) and (pp_weight + dp_weight > 0):
        st.warning(f"Sum of weights ({pp_weight + dp_weight:.2f}) is not 1. The predictor will normalize them. For direct control, please adjust to sum to 1.")
    elif (pp_weight + dp_weight == 0):
        st.warning("Both reference product weights are zero. Prediction will be based on other factors or might be zero if no other base.")

    reference_products_info_input = {
        'Princess Plus': {'Price': pp_price, 'Weight': pp_weight},
        'Dwarf Plus': {'Price': dp_price, 'Weight': dp_weight}
    }
    
    st.markdown("---")
    st.markdown("##### Regional Parameters")
    regions = sales_data_for_predictor['Region'].unique()
    
    price_elasticity_params_input = {}
    price_sensitivity_params_input = {}
    launch_time_impact_params_input = {}

    reg_param_cols = st.columns(len(regions))
    default_elasticity = {'AMR': -1.0, 'Europe': -0.5, 'PAC': -1.5}
    default_sensitivity = {'AMR': 1.0, 'Europe': 0.5, 'PAC': 1.5}
    default_launch_impact_region = {'AMR': 0.05, 'Europe': 0.05, 'PAC': 0.05}

    for i, region in enumerate(regions):
        with reg_param_cols[i]:
            st.markdown(f"###### {region}")
            price_elasticity_params_input[region] = st.number_input(
                f"Price Elasticity ({region})", value=default_elasticity.get(region, -0.5), step=0.1, key=f"elast_{region}"
            )
            price_sensitivity_params_input[region] = st.number_input(
                f"Price Sensitivity ({region})", value=default_sensitivity.get(region, 1.0), step=0.1, key=f"sens_{region}"
            )
            launch_time_impact_params_input[region] = st.slider(
                f"Launch Impact ({region}) (%)", min_value=-20.0, max_value=50.0, value=default_launch_impact_region.get(region, 0.05)*100, step=1.0, key=f"launch_reg_{region}"
            ) / 100.0
            
# 调用预测函数
if st.button("🚀 Generate Forecast"):
    with st.spinner("Generating sales forecast..."):
        predicted_sales_df = generate_sales_forecast(
            historical_sales_data=sales_data_for_predictor, # 使用重命名后的数据
            product_to_forecast=product_to_forecast,
            target_product_price=target_price,
            reference_products_info=reference_products_info_input,
            price_elasticity_params=price_elasticity_params_input,
            price_sensitivity_params=price_sensitivity_params_input,
            battery_upgrade_impact=battery_impact,
            launch_time_impact_params=launch_time_impact_params_input,
            weeks_for_launch_impact=weeks_launch_impact
        )
    
    st.session_state['predicted_sales_df'] = predicted_sales_df # 存储到 session_state
else:
    # 如果 session_state 中有旧的预测结果，则使用它，否则为空
    if 'predicted_sales_df' not in st.session_state:
        st.session_state['predicted_sales_df'] = pd.DataFrame(columns=['Region', 'Week', 'Predicted_Sales'])


# 预测结果展示
st.subheader("3.2 Forecast Results")
predicted_sales_df_display = st.session_state.get('predicted_sales_df', pd.DataFrame(columns=['Region', 'Week', 'Predicted_Sales']))

if not predicted_sales_df_display.empty:
    # 确保预测结果中的 'Week' 列也按照正确的时序排列
    if 'Week' in predicted_sales_df_display.columns and not predicted_sales_df_display.empty:
        # 使用 sort_key_date 对预测结果中实际存在的周进行排序
        forecast_unique_weeks = predicted_sales_df_display['Week'].unique()
        
        # 确保 forecast_unique_weeks 中的元素是字符串，以便 sort_key_date 正确处理
        # (generate_sales_forecast 返回的Week列应该是字符串类型，这里是双重保证)
        forecast_unique_weeks_str = [str(w) for w in forecast_unique_weeks]
        
        sorted_forecast_weeks = sorted(forecast_unique_weeks_str, key=sort_key_date)
        
        predicted_sales_df_display['Week'] = pd.Categorical(
            predicted_sales_df_display['Week'].astype(str), # 确保转换为字符串再创建Categorical
            categories=sorted_forecast_weeks,
            ordered=True
        )
        # 按区域和已排序的周再次排序整个DataFrame
        predicted_sales_df_display = predicted_sales_df_display.sort_values(by=['Region', 'Week']).reset_index(drop=True)

    st.dataframe(predicted_sales_df_display, use_container_width=True)

    st.subheader("3.3 Forecast Visualization")
    
    # 允许用户选择区域来可视化预测
    available_regions_forecast = predicted_sales_df_display['Region'].unique()
    if len(available_regions_forecast) > 0:
        selected_region_forecast_viz = st.selectbox(
            "Select Region to Visualize Forecast",
            options=available_regions_forecast,
            index=0,
            key="forecast_region_select"
        )
        
        forecast_to_plot = predicted_sales_df_display[predicted_sales_df_display['Region'] == selected_region_forecast_viz]

        if not forecast_to_plot.empty:
            fig_forecast, ax_forecast = plt.subplots(figsize=(14, 7))
            sns.lineplot(data=forecast_to_plot, x='Week', y='Predicted_Sales', marker='o', ax=ax_forecast, label=f"{product_to_forecast} Forecast")
            
            # 可选：叠加上历史数据进行对比 (仅限Dwarf Plus 和 Princess Plus)
            # 这里我们只画目标产品的预测
            
            ax_forecast.set_title(f"Sales Forecast for {product_to_forecast} in {selected_region_forecast_viz}")
            ax_forecast.tick_params(axis='x', rotation=90)
            ax_forecast.grid(True, linestyle='--', alpha=0.7)
            ax_forecast.legend()
            st.pyplot(fig_forecast)
        else:
            st.info(f"No forecast data to display for {selected_region_forecast_viz}.")
    else:
        st.info("No regions found in the forecast data to visualize.")
        
else:
    st.info("Click 'Generate Forecast' to see the results.")

# ... (页脚或其他内容可以保留)

st.markdown("---")
st.caption("Sales Forecasting Model for Superman Plus - End of Page")

# 结论与业务建议
st.header("4. Conclusions and Business Recommendations")

st.markdown("""
Based on our analysis and forecast results, we can make the following business recommendations:

1. **Product Strategy**:
   - **Princess Plus**: Maintain strong sales in the PAC region, while considering promotions in Europe to increase market share
   - **Dwarf Plus**: Performs well in the AMR region, consider expanding the product line or launching limited editions to boost sales

2. **Regional Strategy**:
   - **PAC**: Key market for Princess Plus, should maintain market leadership position
   - **AMR**: Important market for Dwarf Plus, consider bundled sales strategies
   - **Europe**: Requires special attention, consider targeted promotional activities

3. **Timing Strategy**:
   - Increase inventory preparation 1-2 weeks before forecast sales peaks
   - Conduct product promotions during sales troughs to balance sales

4. **Pricing Strategy**:
   - Based on forecast sales fluctuations, adopt different pricing strategies at different times
   - Consider offering small price discounts during periods of intense competition
""")

# 底部信息
st.sidebar.markdown("---")
st.sidebar.info("This application demonstrates the complete process of sales forecast analysis, including data exploration, visualization, and predictive modeling.") 