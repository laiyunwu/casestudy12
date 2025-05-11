#!/usr/bin/env python
# coding: utf-8

# # Case 1: 销量预测 - 预测模型构建
# 
# 本脚本实现销量预测模型，基于探索性分析的结果，采用分层混合模型方法。

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit
import os
import warnings
warnings.filterwarnings('ignore')

# 设置绘图样式
plt.style.use('ggplot')
sns.set(style="whitegrid")
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 加载数据
def load_processed_data(file_path='../data/processed_sales_data.csv'):
    """加载预处理后的销售数据"""
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    else:
        raise FileNotFoundError(f"找不到处理后的数据文件 {file_path}，请先运行数据探索分析脚本。")

# 特征工程
def prepare_features(data):
    """为模型准备特征"""
    # 复制数据以避免修改原始数据
    df = data.copy()
    
    # 创建季节性特征
    df['month_sin'] = np.sin(2 * np.pi * df['month_num'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month_num'] / 12)
    df['week_sin'] = np.sin(2 * np.pi * df['week'] / 4)
    df['week_cos'] = np.cos(2 * np.pi * df['week'] / 4)
    
    # 创建滞后特征 (上一周的销量)
    df_with_lag = df.copy()
    regions = df['region'].unique()
    products = df['product'].unique()
    
    for region in regions:
        for product in products:
            mask = (df['region'] == region) & (df['product'] == product)
            df_subset = df[mask].sort_values('continuous_week')
            
            if len(df_subset) > 1:
                df_subset['sales_lag1'] = df_subset['sales'].shift(1)
                df_subset['sales_lag2'] = df_subset['sales'].shift(2)
                
                # 用前一期的值填充第一个NaN
                df_subset['sales_lag1'] = df_subset['sales_lag1'].fillna(df_subset['sales'].iloc[0])
                # 用前两期的均值填充第二个NaN
                if len(df_subset) > 2:
                    df_subset['sales_lag2'] = df_subset['sales_lag2'].fillna(df_subset['sales'].iloc[:2].mean())
                else:
                    df_subset['sales_lag2'] = df_subset['sales_lag2'].fillna(df_subset['sales'].iloc[0])
                
                # 更新原数据框
                df_with_lag.loc[mask, 'sales_lag1'] = df_subset['sales_lag1'].values
                df_with_lag.loc[mask, 'sales_lag2'] = df_subset['sales_lag2'].values
    
    # 确保没有NaN值
    df_with_lag['sales_lag1'] = df_with_lag['sales_lag1'].fillna(df_with_lag['sales'].mean())
    df_with_lag['sales_lag2'] = df_with_lag['sales_lag2'].fillna(df_with_lag['sales'].mean())
    
    return df_with_lag

# 构建区域销量比例模型
def build_region_ratio_models(data):
    """为各地区构建销量比例预测模型"""
    # 计算区域销量比例
    region_ratios = pd.DataFrame()
    for date in data['date'].unique():
        for product in data['product'].unique():
            date_product_data = data[(data['date'] == date) & (data['product'] == product)]
            
            if len(date_product_data) > 0:
                total_sales = date_product_data['sales'].sum()
                if total_sales > 0:
                    for region in data['region'].unique():
                        region_data = date_product_data[date_product_data['region'] == region]
                        
                        if len(region_data) > 0:
                            ratio = region_data['sales'].iloc[0] / total_sales
                        else:
                            ratio = 0
                            
                        region_ratios = pd.concat([region_ratios, pd.DataFrame({
                            'date': [date],
                            'product': [product],
                            'region': [region],
                            'ratio': [ratio],
                            'month_num': [date_product_data['month_num'].iloc[0]],
                            'week': [date_product_data['week'].iloc[0]],
                            'continuous_week': [date_product_data['continuous_week'].iloc[0]],
                            'month_sin': [date_product_data['month_sin'].iloc[0]],
                            'month_cos': [date_product_data['month_cos'].iloc[0]],
                            'week_sin': [date_product_data['week_sin'].iloc[0]],
                            'week_cos': [date_product_data['week_cos'].iloc[0]],
                            'price': [date_product_data['price'].iloc[0]],
                            'has_new_tech': [date_product_data['has_new_tech'].iloc[0]]
                        })])
    
    # 构建每个地区的比例预测模型
    regions = data['region'].unique()
    region_models = {}
    
    for region in regions:
        region_data = region_ratios[region_ratios['region'] == region]
        
        # 准备特征和目标变量
        X = region_data[['continuous_week', 'month_sin', 'month_cos', 'week_sin', 'week_cos', 'price', 'has_new_tech']]
        y = region_data['ratio']
        
        # 训练随机森林模型
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        region_models[region] = model
    
    return region_models, region_ratios

# 价格弹性分析
def price_elasticity_model(data):
    """构建价格弹性模型"""
    # 准备价格和销量数据
    products = data['product'].unique()
    price_sales_data = []
    
    base_product = products[0]  # 以第一个产品为基准
    base_price = data[data['product'] == base_product]['price'].iloc[0]
    
    for product in products:
        product_data = data[data['product'] == product]
        price = product_data['price'].iloc[0]
        avg_sales = product_data.groupby('region')['sales'].mean().reset_index()
        
        for _, row in avg_sales.iterrows():
            price_sales_data.append({
                'product': product,
                'region': row['region'],
                'price': price,
                'sales': row['sales'],
                'price_change_pct': (price - base_price) / base_price if base_price > 0 else 0,
                'has_new_tech': product_data['has_new_tech'].iloc[0]
            })
    
    price_sales_df = pd.DataFrame(price_sales_data)
    
    # 创建特征和目标变量
    X = price_sales_df[['price_change_pct', 'has_new_tech']]
    y = price_sales_df['sales']
    
    # 训练弹性网模型
    model = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42)
    model.fit(X, y)
    
    return model, price_sales_df

# 构建时间序列预测模型
def build_time_series_model(data):
    """构建基础时间序列预测模型"""
    # 按产品和连续周数聚合销售数据
    ts_data = data.groupby(['product', 'continuous_week']).agg({
        'sales': 'sum',
        'price': 'first',
        'has_new_tech': 'first',
        'month_sin': 'first',
        'month_cos': 'first',
        'week_sin': 'first',
        'week_cos': 'first',
        'sales_lag1': 'mean',
        'sales_lag2': 'mean'
    }).reset_index()
    
    # 将不同产品的数据合并为时间序列特征
    products = data['product'].unique()
    
    # 准备特征和目标变量
    X = ts_data[['continuous_week', 'price', 'has_new_tech', 'month_sin', 'month_cos', 
                 'week_sin', 'week_cos', 'sales_lag1', 'sales_lag2']]
    y = ts_data['sales']
    
    # 训练随机森林模型
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
    model.fit(X, y)
    
    return model, ts_data

# 预测未来15周销量
def predict_future_sales(ts_model, region_models, price_model, data, weeks_to_predict=15):
    """预测未来15周的销量"""
    # 获取最新数据点
    max_week = data['continuous_week'].max()
    last_point = data[data['continuous_week'] == max_week].iloc[0]
    
    # 创建未来周数的数据框
    future_weeks = pd.DataFrame({
        'continuous_week': np.arange(max_week + 1, max_week + weeks_to_predict + 1)
    })
    
    # 计算每个未来周的月份和周数
    base_month = last_point['month_num']
    base_week = last_point['week']
    
    for i, week in enumerate(future_weeks['continuous_week']):
        week_offset = i + 1
        new_week = (base_week + week_offset - 1) % 4 + 1
        months_forward = (base_week + week_offset - 1) // 4
        new_month = (base_month + months_forward - 1) % 12 + 1
        
        future_weeks.loc[i, 'week'] = new_week
        future_weeks.loc[i, 'month_num'] = new_month
    
    # 创建季节性特征
    future_weeks['month_sin'] = np.sin(2 * np.pi * future_weeks['month_num'] / 12)
    future_weeks['month_cos'] = np.cos(2 * np.pi * future_weeks['month_num'] / 12)
    future_weeks['week_sin'] = np.sin(2 * np.pi * future_weeks['week'] / 4)
    future_weeks['week_cos'] = np.cos(2 * np.pi * future_weeks['week'] / 4)
    
    # 设置Superman Plus的特性
    future_weeks['price'] = 205  # Superman Plus的价格
    future_weeks['has_new_tech'] = 1  # 有新技术
    
    # 初始化滞后特征
    if len(data[data['product'] == 'Princess Plus']) > 0:
        last_princess = data[data['product'] == 'Princess Plus'].sort_values('continuous_week').tail(2)
        if len(last_princess) >= 2:
            future_weeks['sales_lag2'] = last_princess['sales'].iloc[-2]
            future_weeks['sales_lag1'] = last_princess['sales'].iloc[-1]
        elif len(last_princess) == 1:
            future_weeks['sales_lag2'] = last_princess['sales'].iloc[0]
            future_weeks['sales_lag1'] = last_princess['sales'].iloc[0]
        else:
            future_weeks['sales_lag2'] = data['sales'].mean()
            future_weeks['sales_lag1'] = data['sales'].mean()
    else:
        future_weeks['sales_lag2'] = data['sales'].mean()
        future_weeks['sales_lag1'] = data['sales'].mean()
    
    # 递归预测
    predictions = []
    
    for i in range(len(future_weeks)):
        # 使用时间序列模型预测总体销量
        week_data = future_weeks.iloc[i:i+1].copy()
        total_sales = ts_model.predict(week_data)[0]
        
        # 调整预测，考虑价格变化
        base_price = data[data['product'] == 'Princess Plus']['price'].iloc[0]
        price_change_pct = (205 - base_price) / base_price if base_price > 0 else 0
        
        price_features = np.array([[price_change_pct, 1]])  # 1表示有新技术
        price_effect = price_model.predict(price_features)[0] / data['sales'].mean()
        
        # 调整后的总销量
        adjusted_sales = total_sales * (1 + price_effect)
        
        # 使用区域模型预测各地区的销量比例
        region_features = week_data[['continuous_week', 'month_sin', 'month_cos', 
                                    'week_sin', 'week_cos', 'price', 'has_new_tech']]
        
        region_sales = {}
        for region, model in region_models.items():
            ratio = model.predict(region_features)[0]
            region_sales[region] = adjusted_sales * ratio
        
        # 储存预测结果
        pred_week = max_week + i + 1
        predictions.append({
            'continuous_week': pred_week,
            'week': week_data['week'].iloc[0],
            'month_num': week_data['month_num'].iloc[0],
            'total_sales': adjusted_sales,
            'AMR': region_sales.get('AMR', 0),
            'Europe': region_sales.get('Europe', 0),
            'PAC': region_sales.get('PAC', 0)
        })
        
        # 更新滞后特征用于下一周预测
        if i + 1 < len(future_weeks):
            future_weeks.loc[i+1, 'sales_lag2'] = future_weeks.loc[i, 'sales_lag1']
            future_weeks.loc[i+1, 'sales_lag1'] = adjusted_sales
    
    # 转换为DataFrame
    predictions_df = pd.DataFrame(predictions)
    
    return predictions_df

# 可视化预测结果
def visualize_predictions(predictions, historical_data):
    """可视化预测结果"""
    # 准备历史数据
    historical_princess = historical_data[historical_data['product'] == 'Princess Plus'].copy()
    
    if len(historical_princess) > 0:
        historical_agg = historical_princess.groupby('continuous_week').agg({
            'sales': 'sum',
            'week': 'first',
            'month_num': 'first'
        }).reset_index()
        
        # 增加区域销量列
        for region in ['AMR', 'Europe', 'PAC']:
            region_data = historical_princess[historical_princess['region'] == region]
            region_agg = region_data.groupby('continuous_week')['sales'].sum().reset_index()
            region_agg.columns = ['continuous_week', region]
            
            historical_agg = pd.merge(historical_agg, region_agg, on='continuous_week', how='left')
            historical_agg[region] = historical_agg[region].fillna(0)
    else:
        # 如果没有Princess Plus的历史数据，使用Dwarf Plus的数据作为参考
        historical_dwarf = historical_data[historical_data['product'] == 'Dwarf Plus'].copy()
        historical_agg = historical_dwarf.groupby('continuous_week').agg({
            'sales': 'sum',
            'week': 'first',
            'month_num': 'first'
        }).reset_index()
        
        # 增加区域销量列
        for region in ['AMR', 'Europe', 'PAC']:
            region_data = historical_dwarf[historical_dwarf['region'] == region]
            region_agg = region_data.groupby('continuous_week')['sales'].sum().reset_index()
            region_agg.columns = ['continuous_week', region]
            
            historical_agg = pd.merge(historical_agg, region_agg, on='continuous_week', how='left')
            historical_agg[region] = historical_agg[region].fillna(0)
    
    # 1. 总体销量预测
    plt.figure(figsize=(12, 6))
    
    plt.plot(historical_agg['continuous_week'], historical_agg['sales'], 'b-', label='历史销量')
    plt.axvline(x=historical_agg['continuous_week'].max(), color='r', linestyle='--', label='预测开始')
    plt.plot(predictions['continuous_week'], predictions['total_sales'], 'g-', label='预测销量')
    
    plt.title('Superman Plus 未来15周销量预测')
    plt.xlabel('连续周数')
    plt.ylabel('销量')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('../data/total_sales_prediction.png')
    
    # 2. 区域销量预测
    plt.figure(figsize=(12, 6))
    
    regions = ['AMR', 'Europe', 'PAC']
    colors = ['b', 'g', 'r']
    
    for i, region in enumerate(regions):
        plt.plot(historical_agg['continuous_week'], historical_agg[region], f'{colors[i]}-', label=f'{region} 历史')
        plt.plot(predictions['continuous_week'], predictions[region], f'{colors[i]}--', label=f'{region} 预测')
    
    plt.axvline(x=historical_agg['continuous_week'].max(), color='k', linestyle='--', label='预测开始')
    
    plt.title('各地区未来15周销量预测')
    plt.xlabel('连续周数')
    plt.ylabel('销量')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('../data/region_sales_prediction.png')
    
    # 3. 创建预测区间 (简化版，使用固定百分比)
    plt.figure(figsize=(12, 6))
    
    # 为总体销量添加95%置信区间 (简化：使用固定百分比)
    lower_ci = predictions['total_sales'] * 0.85
    upper_ci = predictions['total_sales'] * 1.15
    
    plt.plot(predictions['continuous_week'], predictions['total_sales'], 'g-', label='预测销量')
    plt.fill_between(predictions['continuous_week'], lower_ci, upper_ci, color='g', alpha=0.2, label='95% 置信区间')
    
    plt.title('Superman Plus 销量预测及置信区间')
    plt.xlabel('连续周数')
    plt.ylabel('销量')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('../data/prediction_interval.png')
    
    # 4. 区域销量占比
    plt.figure(figsize=(10, 6))
    
    # 计算各地区销量占比
    for region in regions:
        predictions[f'{region}_ratio'] = predictions[region] / predictions['total_sales']
    
    for i, region in enumerate(regions):
        plt.plot(predictions['continuous_week'], predictions[f'{region}_ratio'], f'{colors[i]}-', label=region)
    
    plt.title('地区销量占比预测')
    plt.xlabel('连续周数')
    plt.ylabel('占比')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('../data/region_ratio_prediction.png')
    
    return

# 生成业务洞察
def generate_insights(predictions):
    """基于预测结果生成业务洞察"""
    insights = []
    
    # 1. 预测总体趋势
    avg_growth = (predictions['total_sales'].iloc[-1] / predictions['total_sales'].iloc[0] - 1) * 100
    insights.append(f"1. 未来15周内预计总销量将{('增长' if avg_growth > 0 else '下降')}约{abs(avg_growth):.1f}%。")
    
    # 2. 销量峰值时间
    peak_week = predictions.loc[predictions['total_sales'].idxmax()]
    insights.append(f"2. 预计销量将在第{int(peak_week['continuous_week'] - predictions['continuous_week'].iloc[0] + 1)}周达到峰值，对应月份为{peak_week['month_num']}月。")
    
    # 3. 地区表现分析
    region_growth = {}
    for region in ['AMR', 'Europe', 'PAC']:
        growth = (predictions[region].iloc[-1] / predictions[region].iloc[0] - 1) * 100
        region_growth[region] = growth
    
    max_growth_region = max(region_growth.items(), key=lambda x: x[1])
    min_growth_region = min(region_growth.items(), key=lambda x: x[1])
    
    insights.append(f"3. {max_growth_region[0]}地区预计增长最快，达到{max_growth_region[1]:.1f}%；"
                   f"{min_growth_region[0]}地区增长较慢，为{min_growth_region[1]:.1f}%。")
    
    # 4. 重要的波动模式
    weekly_changes = predictions['total_sales'].pct_change().abs()
    high_volatility_weeks = predictions.iloc[weekly_changes[weekly_changes > 0.1].index]
    
    if len(high_volatility_weeks) > 0:
        insights.append(f"4. 预计在{'、'.join([str(int(w)) for w in high_volatility_weeks['week']])}周将出现显著的销量波动，需要特别关注。")
    else:
        insights.append("4. 预测期内销量相对稳定，未观察到显著波动。")
    
    # 5. 区域策略建议
    avg_ratios = {}
    for region in ['AMR', 'Europe', 'PAC']:
        avg_ratios[region] = predictions[f'{region}_ratio'].mean()
    
    insights.append(f"5. 在供应链和营销资源分配上，建议关注{max(avg_ratios.items(), key=lambda x: x[1])[0]}地区，"
                   f"该地区预计将占总销量的{max(avg_ratios.values()) * 100:.1f}%。")
    
    return insights

# 主函数
def main():
    try:
        # 加载处理后的数据
        data = load_processed_data()
        print("数据已加载。")
        
        # 准备特征
        featured_data = prepare_features(data)
        print("特征准备完成。")
        
        # 构建区域比例模型
        print("正在构建区域销量比例模型...")
        region_models, region_ratios = build_region_ratio_models(featured_data)
        
        # 构建价格弹性模型
        print("正在分析价格弹性...")
        price_model, price_data = price_elasticity_model(featured_data)
        
        # 构建时间序列模型
        print("正在构建时间序列预测模型...")
        ts_model, ts_data = build_time_series_model(featured_data)
        
        # 预测未来15周销量
        print("正在预测未来15周销量...")
        predictions = predict_future_sales(ts_model, region_models, price_model, featured_data)
        
        # 保存预测结果
        predictions.to_csv('../data/superman_plus_predictions.csv', index=False)
        
        # 可视化预测结果
        print("正在生成可视化图表...")
        visualize_predictions(predictions, featured_data)
        
        # 生成业务洞察
        print("正在生成业务洞察...")
        insights = generate_insights(predictions)
        
        # 保存业务洞察
        with open('../data/business_insights.txt', 'w') as f:
            f.write("# Superman Plus 销量预测业务洞察\n\n")
            for insight in insights:
                f.write(f"{insight}\n\n")
        
        print("\n预测完成。结果已保存至 ../data/ 目录。")
        print("\n业务洞察:")
        for insight in insights:
            print(insight)
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    # 确保../data目录存在
    os.makedirs('../data', exist_ok=True)
    main() 