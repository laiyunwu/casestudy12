import pandas as pd
import numpy as np
from load_data import load_data

def preprocess_data(df, product_info):
    """
    对销售数据进行预处理。
    
    参数:
    df (DataFrame): 销售数据
    product_info (dict): 产品信息
    
    返回:
    DataFrame: 预处理后的数据
    """
    # 复制数据以避免修改原始数据
    df_processed = df.copy()
    
    # 添加价格信息
    df_processed['Price'] = product_info['Price']
    
    # 添加周数信息（从1开始）
    df_processed['Week_Number'] = range(1, len(df_processed) + 1)
    
    return df_processed

def calculate_price_impact(target_price, reference_price, region):
    """
    计算价格差异对销量的影响系数
    
    参数:
    target_price (float): 目标产品价格
    reference_price (float): 参考产品价格
    region (str): 区域名称
    
    返回:
    float: 价格影响系数
    """
    # 根据区域设置价格弹性
    price_elasticity = {
        'AMR': -1.0,
        'Europe': -0.5,
        'PAC': -1.5
    }.get(region, -0.5)  # 默认值为-0.5
    
    price_ratio = target_price / reference_price
    return np.power(price_ratio, price_elasticity)

def predict_superman_plus_sales():
    """
    预测Superman Plus的销量
    
    返回:
    DataFrame: 预测的销量数据
    dict: Superman Plus的产品信息
    """
    # 加载历史数据
    princess_df, dwarf_df, product_info = load_data()
    
    # Superman Plus的产品信息
    superman_plus_info = {
        'Product': 'Superman Plus',
        'Price': 205,  # 价格为205
        'Launch': 'Year-3 Launch in SepWk3'
    }
    
    # 预处理数据
    princess_processed = preprocess_data(princess_df, product_info['Princess Plus'])
    dwarf_processed = preprocess_data(dwarf_df, product_info['Dwarf Plus'])
    
    # 计算价格影响系数
    price_impact_princess = calculate_price_impact(superman_plus_info['Price'], 
                                                 product_info['Princess Plus']['Price'], 'AMR')
    price_impact_dwarf = calculate_price_impact(superman_plus_info['Price'], 
                                              product_info['Dwarf Plus']['Price'], 'AMR')
    
    # 使用加权平均方法预测销量
    # 假设Princess Plus的权重为0.6，Dwarf Plus的权重为0.4
    princess_weight = 0.7
    dwarf_weight = 0.3
    
    # 初始化预测结果DataFrame
    predicted_sales = pd.DataFrame()
    
    # 根据讨论结论，更新预测模型以反映价格敏感度、电池升级和上市时间差异的影响
    # 定义区域价格敏感度系数
    price_sensitivity = {
        'AMR': 1.0,  # 价格敏感度系数
        'Europe': 0.5,
        'PAC': 1.5
    }
    
    # 定义电池升级影响因子
    battery_upgrade_impact = 0.05  # +5% 的销量提升
    
    # 定义上市时间差异影响因子
    launch_time_impact = {
        'AMR': 0.05,  # 前4周销量平均高 +5%
        'Europe': 0.05,
        'PAC': 0.05
    }
    
    # 更新预测逻辑
    for region in ['AMR', 'Europe', 'PAC']:
        # 获取每个产品在该地区的销量
        princess_sales = princess_processed.loc[region, 'Sales'].values
        dwarf_sales = dwarf_processed.loc[region, 'Sales'].values
        
        # 计算价格调整因子
        price_adjustment_factor_princess = 1 - (superman_plus_info['Price']/product_info['Princess Plus']['Price']-1) * price_sensitivity[region]
        price_adjustment_factor_dwarf = 1 - (superman_plus_info['Price']/product_info['Dwarf Plus']['Price']-1) * price_sensitivity[region]
        
        # 计算预测销量
        predicted_region_sales = (
            princess_sales * princess_weight * calculate_price_impact(superman_plus_info['Price'], product_info['Princess Plus']['Price'], region)*price_adjustment_factor_princess +
            dwarf_sales * dwarf_weight * calculate_price_impact(superman_plus_info['Price'], product_info['Dwarf Plus']['Price'], region)*price_adjustment_factor_dwarf
        )  * (1 + battery_upgrade_impact)
        
        # 考虑上市时间差异影响
        if len(predicted_region_sales) <= 4:
            predicted_region_sales *= (1 + launch_time_impact[region])
    
        # 添加到预测结果中
        predicted_sales[region] = predicted_region_sales
    
    # 添加周数信息
    predicted_sales['Weeks'] = [f'{month} wk{week}' for month in ['Sep', 'Oct', 'Nov', 'Dec', 'Jan'] for week in range(1, 5)][2:2+len(predicted_sales)]
    predicted_sales_melted = predicted_sales.melt(id_vars=['Weeks'], var_name='Region', value_name='Sales')
    predicted_sales_melted = predicted_sales_melted.set_index(['Region', 'Weeks'])
    
    # 验证输出数据结构
    if not isinstance(predicted_sales_melted.index, pd.MultiIndex) or \
       predicted_sales_melted.index.names != ['Region', 'Weeks']:
        raise ValueError('预测数据格式异常，索引必须包含Region和Weeks')
    
    if 'Sales' not in predicted_sales_melted.columns:
        raise ValueError('预测数据必须包含Sales列')
    
    return predicted_sales_melted.rename_axis(['Region', 'Week']), superman_plus_info

if __name__ == '__main__':
    # 进行预测
    predicted_sales, superman_plus_info = predict_superman_plus_sales()
    
    # 打印预测结果
    print("\nSuperman Plus 预测销量:")
    print(predicted_sales)
    print("\nSuperman Plus 产品信息:")
    print(superman_plus_info)
    
    # 打印基本统计信息
    print("\nSuperman Plus 销量统计:")
    print(predicted_sales.groupby('Region')['Sales'].describe())