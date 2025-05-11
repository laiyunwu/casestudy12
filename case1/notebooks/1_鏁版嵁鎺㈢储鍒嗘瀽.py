#!/usr/bin/env python
# coding: utf-8

# # Case 1: 销量预测 - 数据探索分析
# 
# 本脚本进行销售数据的探索性分析，用于理解产品销售模式，为预测模型选择提供依据。

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
import re

# 设置绘图样式
plt.style.use('ggplot')
sns.set(style="whitegrid")
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 加载数据
def load_data(file_path):
    """加载销售数据"""
    # 在实际项目中，我们会从Excel文件加载数据
    # 这里我们直接从CSV格式创建DataFrame
    data = pd.read_csv(file_path, header=0)
    return data

# 如果是CSV文件，需要将其转换为DataFrame
def csv_to_df(file_path):
    """从CSV文件创建DataFrame"""
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 找到标题行
    for i, line in enumerate(lines):
        if 'date,region,product,price,sales' in line:
            header_index = i
            break
    
    # 从标题行开始创建DataFrame
    data_lines = lines[header_index:]
    import io
    data = pd.read_csv(io.StringIO(''.join(data_lines)))
    return data

# 数据处理和特征工程
def preprocess_data(df):
    """预处理数据并创建特征"""
    # 复制数据以避免修改原始数据
    data = df.copy()
    
    # 提取时间特征
    data['month'] = data['date'].apply(lambda x: x.split('-')[0])
    data['week'] = data['date'].apply(lambda x: int(re.findall(r'wk(\d+)', x)[0]) if re.findall(r'wk(\d+)', x) else 0)
    
    # 创建连续周数特征
    month_map = {'Sept': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12, 'Jan': 1}
    data['month_num'] = data['month'].map(month_map)
    data['year'] = data['month_num'].apply(lambda x: 2023 if x >= 9 else 2024)  # 假设9-12月是2023年，1月是2024年
    
    # 创建连续周数 (从1到最大周数)
    data['continuous_week'] = (data['year'] - 2023) * 52 + (data['month_num'] - 9) * 4 + data['week']
    
    # 创建技术特性标记 (Princess Plus 有新技术, Dwarf Plus 没有)
    data['has_new_tech'] = data['product'].apply(lambda x: 1 if x == 'Princess Plus' else 0)
    
    return data

# 探索性数据分析
def exploratory_analysis(data):
    """进行探索性数据分析并可视化关键发现"""
    # 1. 基本统计信息
    print("数据基本信息:")
    print(data.info())
    print("\n基本统计量:")
    print(data.describe())
    
    # 2. 按产品和地区分析销量
    region_product_sales = data.groupby(['region', 'product'])['sales'].mean().reset_index()
    pivot_sales = region_product_sales.pivot(index='region', columns='product', values='sales')
    
    plt.figure(figsize=(10, 6))
    pivot_sales.plot(kind='bar')
    plt.title('不同地区和产品的平均销量')
    plt.ylabel('平均销量')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('../data/region_product_sales.png')
    
    # 3. 时间趋势分析
    plt.figure(figsize=(12, 6))
    
    for product in data['product'].unique():
        product_data = data[data['product'] == product]
        pivot_df = product_data.pivot_table(
            index='continuous_week', 
            columns='region', 
            values='sales', 
            aggfunc='mean'
        ).reset_index()
        
        # 确保连续周数是有序的
        pivot_df = pivot_df.sort_values('continuous_week')
        
        plt.subplot(1, 2, 1 if product == 'Princess Plus' else 2)
        for region in ['AMR', 'Europe', 'PAC']:
            if region in pivot_df.columns:
                plt.plot(pivot_df['continuous_week'], pivot_df[region], label=region)
        
        plt.title(f'{product} 销量时间趋势')
        plt.xlabel('周数')
        plt.ylabel('销量')
        plt.legend()
    
    plt.tight_layout()
    plt.savefig('../data/time_trends.png')
    
    # 4. 价格对销量的影响
    plt.figure(figsize=(10, 6))
    sns.boxplot(x='product', y='sales', data=data)
    plt.title('不同价格产品的销量分布')
    plt.xlabel('产品 (价格)')
    plt.ylabel('销量')
    plt.tight_layout()
    plt.savefig('../data/price_impact.png')
    
    # 5. 季节性分析
    plt.figure(figsize=(10, 6))
    monthly_sales = data.groupby(['month', 'product'])['sales'].mean().reset_index()
    
    for product in data['product'].unique():
        product_monthly = monthly_sales[monthly_sales['product'] == product]
        # 按月份排序
        month_order = ['Sept', 'Oct', 'Nov', 'Dec', 'Jan']
        product_monthly['month'] = pd.Categorical(product_monthly['month'], categories=month_order, ordered=True)
        product_monthly = product_monthly.sort_values('month')
        
        plt.plot(product_monthly['month'], product_monthly['sales'], marker='o', label=product)
    
    plt.title('月度销量趋势')
    plt.xlabel('月份')
    plt.ylabel('平均销量')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('../data/monthly_trends.png')
    
    # 6. 周内销量模式
    plt.figure(figsize=(10, 6))
    weekly_sales = data.groupby(['week', 'product'])['sales'].mean().reset_index()
    
    for product in data['product'].unique():
        product_weekly = weekly_sales[weekly_sales['product'] == product]
        product_weekly = product_weekly.sort_values('week')
        
        plt.plot(product_weekly['week'], product_weekly['sales'], marker='o', label=product)
    
    plt.title('周销量模式')
    plt.xlabel('周数')
    plt.ylabel('平均销量')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig('../data/weekly_patterns.png')
    
    return region_product_sales

# 关系分析
def relationship_analysis(data):
    """分析价格弹性和产品关系"""
    # 1. 计算价格弹性
    products = data['product'].unique()
    prices = data.groupby('product')['price'].first().to_dict()
    avg_sales = data.groupby('product')['sales'].mean().to_dict()
    
    # 假设两个产品间的价格弹性
    if len(products) == 2:
        p1, p2 = products
        price_diff = prices[p1] - prices[p2]
        sales_diff_pct = (avg_sales[p1] - avg_sales[p2]) / avg_sales[p2]
        price_diff_pct = price_diff / prices[p2]
        
        price_elasticity = sales_diff_pct / price_diff_pct if price_diff_pct != 0 else 0
        print(f"\n价格弹性估计: {price_elasticity:.2f}")
        print(f"这意味着价格每上升1%，销量会变化约{price_elasticity:.2f}%")
    
    # 2. 产品销量相关性分析
    product_pivot = data.pivot_table(
        index=['date', 'region'], 
        columns='product', 
        values='sales'
    ).reset_index()
    
    correlation = product_pivot[products].corr()
    print("\n产品销量相关性:")
    print(correlation)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(correlation, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
    plt.title('产品销量相关性')
    plt.tight_layout()
    plt.savefig('../data/product_correlation.png')
    
    # 3. 地区销量模式比较
    plt.figure(figsize=(12, 8))
    
    regions = data['region'].unique()
    for i, region in enumerate(regions, 1):
        plt.subplot(len(regions), 1, i)
        
        region_data = data[data['region'] == region]
        for product in products:
            product_region = region_data[region_data['product'] == product]
            product_region = product_region.sort_values('continuous_week')
            
            plt.plot(product_region['continuous_week'], product_region['sales'], label=product)
        
        plt.title(f'{region} 地区销量趋势')
        plt.xlabel('周数')
        plt.ylabel('销量')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig('../data/region_trends.png')
    
    return correlation

# 主函数
def main():
    # 数据文件路径
    data_file = '../data/case1_example.xlsx'
    
    # 如果数据文件不存在，尝试使用CSV格式
    if not os.path.exists(data_file):
        # 尝试使用CSV格式
        csv_file = '../data/case1_example.xlsx'  # 实际上是CSV格式内容但扩展名为xlsx
        if os.path.exists(csv_file):
            data = csv_to_df(csv_file)
        else:
            print(f"错误: 找不到数据文件 {data_file} 或 {csv_file}")
            return
    else:
        data = load_data(data_file)
    
    # 数据预处理
    processed_data = preprocess_data(data)
    
    # 保存处理后的数据
    processed_data.to_csv('../data/processed_sales_data.csv', index=False)
    
    # 探索性分析
    region_product_sales = exploratory_analysis(processed_data)
    
    # 关系分析
    correlation = relationship_analysis(processed_data)
    
    print("\n数据分析完成。可视化结果已保存至 ../data/ 目录。")

if __name__ == "__main__":
    # 确保../data目录存在
    os.makedirs('../data', exist_ok=True)
    main() 