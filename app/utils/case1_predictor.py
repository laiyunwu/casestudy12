'''
Case 1: 销量预测核心逻辑模块
'''
import pandas as pd
import numpy as np

def calculate_price_impact_factor(target_price: float, 
                                  reference_price: float, 
                                  price_elasticity: float) -> float:
    """
    计算价格差异对销量的原始影响系数 (基于弹性)。
    """
    if reference_price == 0: # 避免除以零
        return 1.0 
    price_ratio = target_price / reference_price
    return np.power(price_ratio, price_elasticity)

def calculate_linear_price_adjustment(target_price: float, 
                                      reference_price: float, 
                                      price_sensitivity_coeff: float) -> float:
    """
    计算价格差异的线性调整因子。
    """
    if reference_price == 0: # 避免除以零
        return 1.0
    # 因子 = 1 - (价格增长百分比) * 敏感度系数
    # 例如，如果提价10% (price_ratio=1.1)，敏感度为1，则因子为 1 - (0.1)*1 = 0.9
    price_increase_ratio = (target_price / reference_price) - 1
    return 1.0 - (price_increase_ratio * price_sensitivity_coeff)

def generate_sales_forecast(
    historical_sales_data: pd.DataFrame, # 包含 'Product', 'Region', 'Week', 'Sales' 等
    product_to_forecast: str,            # 例如 "Superman Plus"
    target_product_price: float,
    reference_products_info: dict,     # {'ProductA': {'Price': X, 'Weight': W_a}, 'ProductB': {'Price': Y, 'Weight': W_b}}
    price_elasticity_params: dict,     # {'RegionA': val, 'RegionB': val}
    price_sensitivity_params: dict,    # {'RegionA': val, 'RegionB': val}
    battery_upgrade_impact: float,       # 例如 0.05 (代表+5%)
    launch_time_impact_params: dict,   # {'RegionA': val, 'RegionB': val} (前4周影响)
    weeks_for_launch_impact: int = 4
) -> pd.DataFrame:
    """
    根据输入参数生成销量预测。

    Args:
        historical_sales_data: 包含参考产品历史销量、区域、周次的数据。
                                 需要有 'Product', 'Region', 'Week', 'Sales' 列。
        product_to_forecast: 要预测的目标产品名称。
        target_product_price: 目标产品的设定价格。
        reference_products_info: 一个字典，键是参考产品名称，值是包含 'Price' 和 'Weight' 的字典。
                                   示例: {
                                       'Princess Plus': {'Price': 150, 'Weight': 0.7},
                                       'Dwarf Plus': {'Price': 100, 'Weight': 0.3}
                                   }
        price_elasticity_params: 各区域的价格弹性系数。示例: {'AMR': -1.0, 'Europe': -0.5, 'PAC': -1.5}
        price_sensitivity_params: 各区域的价格敏感度系数。示例: {'AMR': 1.0, 'Europe': 0.5, 'PAC': 1.5}
        battery_upgrade_impact: 电池升级带来的销量提升比例 (例如 0.05 表示 5%)。
        launch_time_impact_params: 各区域新品上市初期（前N周）的额外销量提升比例。
                                     示例: {'AMR': 0.05, 'Europe': 0.05, 'PAC': 0.05}
        weeks_for_launch_impact: 新品上市初期影响适用的周数，默认为4周。

    Returns:
        pd.DataFrame: 预测销量，包含 'Region', 'Week', 'Predicted_Sales' 列。
    """
    
    if historical_sales_data.empty:
        return pd.DataFrame(columns=['Region', 'Week', 'Predicted_Sales'])

    # 确保参考产品信息中的权重总和约为1 (允许小的浮点误差)
    total_weight = sum(info.get('Weight', 0) for info in reference_products_info.values())
    if not np.isclose(total_weight, 1.0):
        # 简单归一化处理，或者可以抛出错误/警告
        if total_weight > 0:
            for product_name in reference_products_info:
                reference_products_info[product_name]['Weight'] /= total_weight
        else:
            # 如果总权重为0，则平均分配权重或抛出错误，这里简单处理，实际应用中需要更稳健
            num_ref_products = len(reference_products_info)
            if num_ref_products > 0:
                avg_weight = 1.0 / num_ref_products
                for product_name in reference_products_info:
                    reference_products_info[product_name]['Weight'] = avg_weight 
            # else: (没有参考产品的情况，预测可能无法进行或返回空)

    all_predicted_sales = []
    
    # 确定所有涉及的周和区域，以统一预测范围
    # 假设所有参考产品的周序列是一致的，取第一个参考产品的周作为基准
    # 或者可以从 historical_sales_data 中提取所有唯一的周
    unique_weeks = historical_sales_data['Week'].unique()
    unique_regions = historical_sales_data['Region'].unique()

    for region in unique_regions:
        region_elasticity = price_elasticity_params.get(region, -0.5) # 默认弹性
        region_sensitivity = price_sensitivity_params.get(region, 1.0) # 默认敏感度
        region_launch_impact = launch_time_impact_params.get(region, 0.0) # 默认上市影响
        
        combined_sales_for_region = pd.Series(0.0, index=unique_weeks)
        base_sales_available = False

        for ref_product_name, ref_info in reference_products_info.items():
            ref_price = ref_info['Price']
            ref_weight = ref_info.get('Weight', 0) # 如果没有权重，则此产品不贡献

            if ref_weight == 0:
                continue

            # 筛选特定参考产品和区域的历史销量数据
            ref_sales_data = historical_sales_data[
                (historical_sales_data['Product'] == ref_product_name) &
                (historical_sales_data['Region'] == region)
            ].set_index('Week')['Sales']

            if ref_sales_data.empty:
                # print(f"警告: 参考产品 '{ref_product_name}' 在区域 '{region}' 无历史数据。")
                continue # 跳过没有数据的参考产品
            
            base_sales_available = True # 标记至少有一个参考产品有数据

            # 1. 计算价格弹性影响因子
            price_elastic_factor = calculate_price_impact_factor(
                target_product_price, ref_price, region_elasticity
            )
            
            # 2. 计算线性价格调整因子
            linear_price_adj_factor = calculate_linear_price_adjustment(
                target_product_price, ref_price, region_sensitivity
            )
            
            # 计算调整后的销量贡献 (与 predict_model.py 逻辑对齐)
            # 原始：ref_sales * weight * elastic_factor * linear_adj_factor
            adjusted_ref_sales = ref_sales_data * ref_weight * price_elastic_factor * linear_price_adj_factor
            
            # 将当前参考产品的贡献累加到该区域的总预测销量中
            # 需要处理索引可能不完全对齐的情况，使用 reindex 和 fill_value
            combined_sales_for_region = combined_sales_for_region.add(adjusted_ref_sales.reindex(unique_weeks, fill_value=0), fill_value=0)

        if not base_sales_available:
            # print(f"警告: 区域 '{region}' 所有参考产品均无历史数据，无法预测。")
            # 为该区域所有周创建空的或0值的预测
            for week_idx, week_name in enumerate(unique_weeks):
                all_predicted_sales.append({
                    'Region': region,
                    'Week': week_name,
                    'Predicted_Sales': 0
                })
            continue

        # 3. 应用电池升级影响 (对加权后的总销量应用)
        combined_sales_for_region *= (1 + battery_upgrade_impact)
        
        # 4. 应用上市初期影响
        # 创建一个布尔序列，标记哪些周属于上市初期
        launch_weeks_mask = pd.Series(False, index=unique_weeks)
        if weeks_for_launch_impact > 0 and len(unique_weeks) > 0:
            # 假设 unique_weeks 是有序的，取前 N 周
            # 注意：实际应用中，周的顺序和识别上市期需要更精确的定义
            # 这里简单地取排序后的前 N 周
            sorted_weeks = sorted(unique_weeks) # 确保顺序，尽管 unique() 通常保留顺序
            launch_period_weeks = sorted_weeks[:min(weeks_for_launch_impact, len(sorted_weeks))]
            launch_weeks_mask[launch_period_weeks] = True
        
        combined_sales_for_region[launch_weeks_mask] *= (1 + region_launch_impact)

        # 收集结果
        for week_name, pred_sale in combined_sales_for_region.items():
            all_predicted_sales.append({
                'Region': region,
                'Week': week_name,
                'Predicted_Sales': pred_sale if pd.notna(pred_sale) else 0 # 确保 NaN 转为 0
            })

    predicted_df = pd.DataFrame(all_predicted_sales)
    
    # 确保列的顺序和存在性
    if not all_predicted_sales:
         return pd.DataFrame(columns=['Region', 'Week', 'Predicted_Sales'])

    return predicted_df.round(2) # 四舍五入到两位小数


if __name__ == '__main__':
    # === 为测试创建模拟数据 ===
    def create_mock_sales_data():
        weeks = [f'Sep wk{i}' for i in range(1,5)] + [f'Oct wk{i}' for i in range(1,5)] + \
                [f'Nov wk{i}' for i in range(1,5)] + [f'Dec wk{i}' for i in range(1,5)] + \
                [f'Jan wk{i}' for i in range(1,5)]
        weeks = weeks[2:2+20] # 取20周数据，与 predict_model.py 对齐
        
        data = []
        for product in ['Princess Plus', 'Dwarf Plus']:
            for region in ['AMR', 'Europe', 'PAC']:
                base_sales = np.random.randint(50, 200)
                for week in weeks:
                    # 添加一些趋势和随机性
                    sales = base_sales + np.random.randint(-20, 20) + (weeks.index(week) * np.random.choice([-1,1,2]))
                    data.append({'Product': product, 'Region': region, 'Week': week, 'Sales': max(0, sales)})
        return pd.DataFrame(data)

    mock_historical_data = create_mock_sales_data()
    print("--- 模拟历史数据 (部分) ---")
    print(mock_historical_data.head())

    # --- 定义输入参数 ---
    product_to_forecast_test = "Superman Plus"
    target_product_price_test = 205.0
    
    reference_products_info_test = {
        'Princess Plus': {'Price': 180, 'Weight': 0.7}, # 假设价格为180
        'Dwarf Plus': {'Price': 120, 'Weight': 0.3}    # 假设价格为120
    }
    
    price_elasticity_params_test = {'AMR': -1.0, 'Europe': -0.5, 'PAC': -1.5}
    price_sensitivity_params_test = {'AMR': 1.0, 'Europe': 0.5, 'PAC': 1.5}
    battery_upgrade_impact_test = 0.05
    launch_time_impact_params_test = {'AMR': 0.05, 'Europe': 0.05, 'PAC': 0.05}
    weeks_for_launch_impact_test = 4

    print("\n--- 输入参数 ---")
    print(f"Target Product: {product_to_forecast_test}, Price: {target_product_price_test}")
    print(f"Reference Products: {reference_products_info_test}")
    print(f"Elasticity: {price_elasticity_params_test}")
    print(f"Sensitivity: {price_sensitivity_params_test}")
    print(f"Battery Impact: {battery_upgrade_impact_test}")
    print(f"Launch Impact: {launch_time_impact_params_test}, Weeks: {weeks_for_launch_impact_test}")

    # --- 调用预测函数 ---
    predicted_sales_df = generate_sales_forecast(
        historical_sales_data=mock_historical_data,
        product_to_forecast=product_to_forecast_test,
        target_product_price=target_product_price_test,
        reference_products_info=reference_products_info_test,
        price_elasticity_params=price_elasticity_params_test,
        price_sensitivity_params=price_sensitivity_params_test,
        battery_upgrade_impact=battery_upgrade_impact_test,
        launch_time_impact_params=launch_time_impact_params_test,
        weeks_for_launch_impact=weeks_for_launch_impact_test
    )

    print("\n--- 预测结果 (Superman Plus) ---")
    print(predicted_sales_df)

    if not predicted_sales_df.empty:
        print("\n--- 预测结果按区域汇总统计 ---")
        print(predicted_sales_df.groupby('Region')['Predicted_Sales'].describe()) 