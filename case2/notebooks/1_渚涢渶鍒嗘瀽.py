#!/usr/bin/env python
# coding: utf-8

# # Case 2: 供应分配优化 - 供需分析
# 
# 本脚本进行供应链数据的探索性分析，分析供需差距，为资源分配优化提供依据。

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 设置绘图样式
plt.style.use('ggplot')
sns.set(style="whitegrid")
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 加载数据
def load_data(file_path):
    """加载供应链数据"""
    # 在实际项目中，我们会从Excel文件加载数据
    # 这里我们直接从CSV格式创建DataFrame
    
    # 使用文本文件模拟不同sheet
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 分割不同的表格数据
    tables = {}
    current_table = None
    table_content = []
    
    for line in content.split('\n'):
        line = line.strip()
        
        # 跳过空行和注释行
        if not line or line.startswith('#'):
            continue
        
        # 检测表名
        if 'sheet)' in line:
            if current_table:
                tables[current_table] = '\n'.join(table_content)
                table_content = []
            
            current_table = line.split('(')[1].split(' ')[0]
        else:
            table_content.append(line)
    
    # 添加最后一个表格
    if current_table and table_content:
        tables[current_table] = '\n'.join(table_content)
    
    # 将每个表格内容转换为DataFrame
    data_dict = {}
    for table_name, content in tables.items():
        import io
        data_dict[table_name] = pd.read_csv(io.StringIO(content))
    
    return data_dict

# 数据预处理
def preprocess_data(data_dict):
    """预处理供应链数据"""
    processed_data = {}
    
    # 重命名和处理数据框
    if 'total_supply' in data_dict:
        ts = data_dict['total_supply'].copy()
        processed_data['total_supply'] = ts
    
    if 'actual_build' in data_dict:
        ab = data_dict['actual_build'].copy()
        processed_data['actual_build'] = ab
    
    if 'demand_forecast' in data_dict:
        df = data_dict['demand_forecast'].copy()
        processed_data['demand_forecast'] = df
    
    if 'customer_demand' in data_dict:
        cd = data_dict['customer_demand'].copy()
        processed_data['customer_demand'] = cd
    
    return processed_data

# 供需分析
def analyze_supply_demand(data):
    """分析供应和需求的差距"""
    supply_demand_analysis = {}
    
    # 1. 总供应量 vs 总需求量 - 按周
    if 'total_supply' in data and 'demand_forecast' in data:
        total_supply = data['total_supply'].copy()
        demand_forecast = data['demand_forecast'].copy()
        
        # 计算每周的总需求 (所有产品)
        total_demand_by_week = {}
        for col in demand_forecast.columns:
            if col != 'product':  # 跳过产品列
                total_demand_by_week[col] = demand_forecast[col].sum()
        
        # 创建供需对比数据框
        supply_vs_demand = pd.DataFrame({
            'week': total_supply['week'],
            'total_supply': total_supply['total_supply'],
            'total_demand': [total_demand_by_week.get(week, 0) for week in total_supply['week']]
        })
        
        # 计算差距和满足率
        supply_vs_demand['gap'] = supply_vs_demand['total_supply'] - supply_vs_demand['total_demand']
        supply_vs_demand['satisfaction_rate'] = np.where(
            supply_vs_demand['total_demand'] > 0,
            np.minimum(1, supply_vs_demand['total_supply'] / supply_vs_demand['total_demand']),
            1
        )
        
        supply_demand_analysis['weekly_supply_vs_demand'] = supply_vs_demand
    
    # 2. 每个产品的需求 - 按周
    if 'demand_forecast' in data:
        demand_forecast = data['demand_forecast'].copy()
        
        # 将产品行转换为列的格式
        product_demand = demand_forecast.melt(
            id_vars=['product'],
            var_name='week',
            value_name='demand'
        )
        
        supply_demand_analysis['product_demand'] = product_demand
    
    # 3. 渠道和地区需求 - 按周
    if 'customer_demand' in data:
        customer_demand = data['customer_demand'].copy()
        
        # 将数据转换为长格式
        channel_region_demand = customer_demand.melt(
            id_vars=['channel', 'region'],
            var_name='week',
            value_name='demand'
        )
        
        supply_demand_analysis['channel_region_demand'] = channel_region_demand
    
    # 4. 累计生产量 vs 需求
    if 'actual_build' in data and 'demand_forecast' in data:
        actual_build = data['actual_build'].copy()
        demand_forecast = data['demand_forecast'].copy()
        
        # 前面假设我们只有第一周的实际产量数据
        if 'Jan-Wk1' in actual_build.columns:
            initial_build = pd.DataFrame({
                'product': actual_build['product'],
                'initial_production': actual_build['Jan-Wk1']
            })
            
            # 将初始产量与未来需求合并
            product_supply_vs_demand = pd.merge(
                initial_build,
                demand_forecast,
                on='product',
                how='inner'
            )
            
            supply_demand_analysis['product_supply_vs_demand'] = product_supply_vs_demand
    
    return supply_demand_analysis

# 可视化分析结果
def visualize_analysis(analysis_data):
    """可视化供需分析结果"""
    # 1. 总供应 vs 总需求 - 按周
    if 'weekly_supply_vs_demand' in analysis_data:
        data = analysis_data['weekly_supply_vs_demand']
        
        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 2, 1)
        x = np.arange(len(data))
        width = 0.35
        
        plt.bar(x - width/2, data['total_supply'], width, label='总供应量')
        plt.bar(x + width/2, data['total_demand'], width, label='总需求量')
        
        plt.xlabel('周')
        plt.ylabel('数量')
        plt.title('总供应量 vs 总需求量')
        plt.xticks(x, data['week'])
        plt.legend()
        
        plt.subplot(1, 2, 2)
        plt.plot(data['week'], data['satisfaction_rate'] * 100, 'b-o')
        plt.axhline(y=100, color='r', linestyle='--')
        plt.xlabel('周')
        plt.ylabel('满足率 (%)')
        plt.title('需求满足率')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('../data/weekly_supply_vs_demand.png')
    
    # 2. 产品需求趋势
    if 'product_demand' in analysis_data:
        data = analysis_data['product_demand']
        
        plt.figure(figsize=(10, 6))
        
        for product in data['product'].unique():
            product_data = data[data['product'] == product]
            plt.plot(product_data['week'], product_data['demand'], 'o-', label=product)
        
        plt.xlabel('周')
        plt.ylabel('需求量')
        plt.title('产品需求趋势')
        plt.grid(True)
        plt.legend()
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig('../data/product_demand_trend.png')
    
    # 3. 渠道和地区需求热图
    if 'channel_region_demand' in analysis_data:
        data = analysis_data['channel_region_demand']
        
        weeks = data['week'].unique()
        
        for week in weeks:
            week_data = data[data['week'] == week]
            
            # 创建渠道-地区需求热图
            pivot = week_data.pivot(index='channel', columns='region', values='demand')
            
            plt.figure(figsize=(10, 6))
            sns.heatmap(pivot, annot=True, cmap='YlGnBu', fmt='g')
            plt.title(f'{week} 渠道-地区需求分布')
            plt.tight_layout()
            plt.savefig(f'../data/{week}_channel_region_heatmap.png')
    
    # 4. 特殊约束：PAC地区Reseller Partner在第4周的需求
    if 'channel_region_demand' in analysis_data:
        data = analysis_data['channel_region_demand']
        
        # 筛选PAC地区Reseller Partner在第4周的数据
        pac_reseller_week4 = data[(data['region'] == 'PAC') & 
                                 (data['channel'] == 'Reseller Partners') & 
                                 (data['week'] == 'Jan-Wk4')]
        
        if not pac_reseller_week4.empty:
            demand_value = pac_reseller_week4['demand'].iloc[0]
            
            # 突出显示这个特殊约束
            plt.figure(figsize=(8, 6))
            plt.barh(['PAC Reseller Week 4'], [demand_value], color='red')
            plt.xlabel('需求量')
            plt.title('特殊约束：PAC地区Reseller Partner在第4周的需求')
            plt.grid(True, axis='x')
            plt.tight_layout()
            plt.savefig('../data/pac_reseller_week4_constraint.png')
    
    # 5. 需求分布
    if 'channel_region_demand' in analysis_data:
        data = analysis_data['channel_region_demand']
        
        # 按渠道汇总
        channel_summary = data.groupby('channel')['demand'].sum().reset_index()
        
        # 按地区汇总
        region_summary = data.groupby('region')['demand'].sum().reset_index()
        
        plt.figure(figsize=(12, 6))
        
        plt.subplot(1, 2, 1)
        plt.pie(channel_summary['demand'], labels=channel_summary['channel'], autopct='%1.1f%%')
        plt.title('渠道需求分布')
        
        plt.subplot(1, 2, 2)
        plt.pie(region_summary['demand'], labels=region_summary['region'], autopct='%1.1f%%')
        plt.title('地区需求分布')
        
        plt.tight_layout()
        plt.savefig('../data/demand_distribution_pie.png')
    
    # 6. 产品需求对比和缺口
    if 'product_supply_vs_demand' in analysis_data:
        data = analysis_data['product_supply_vs_demand']
        
        # 假设第一周的生产量是用于整个预测期间
        for product in data['product']:
            product_row = data[data['product'] == product].iloc[0]
            initial_prod = product_row['initial_production']
            future_demand = {col: product_row[col] for col in product_row.index if col.startswith('Jan-Wk') and col != 'Jan-Wk1'}
            
            weeks = list(future_demand.keys())
            demands = list(future_demand.values())
            
            plt.figure(figsize=(10, 6))
            plt.bar(weeks, demands, color='blue', label='需求')
            plt.axhline(y=initial_prod, color='red', linestyle='--', label=f'生产量 ({initial_prod})')
            
            plt.title(f'{product} 需求 vs 生产量')
            plt.xlabel('周')
            plt.ylabel('数量')
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            plt.savefig(f'../data/{product}_demand_vs_production.png')
    
    return

# 生成关键约束报告
def generate_constraint_report(analysis_data):
    """生成关键约束报告"""
    constraints = []
    
    # 1. 总体供需情况
    if 'weekly_supply_vs_demand' in analysis_data:
        data = analysis_data['weekly_supply_vs_demand']
        overall_satisfaction = data['satisfaction_rate'].mean() * 100
        
        constraints.append(f"1. 总体供需情况:")
        constraints.append(f"   - 平均需求满足率: {overall_satisfaction:.1f}%")
        
        weeks_short = data[data['gap'] < 0]
        if not weeks_short.empty:
            constraints.append(f"   - 供应短缺的周: {', '.join(weeks_short['week'])}")
        else:
            constraints.append("   - 总供应量足够满足总需求")
    
    # 2. 产品级别约束
    if 'product_supply_vs_demand' in analysis_data:
        data = analysis_data['product_supply_vs_demand']
        
        constraints.append("\n2. 产品级别约束:")
        
        for _, row in data.iterrows():
            product = row['product']
            initial_prod = row['initial_production']
            
            # 计算总需求
            future_demand_cols = [col for col in row.index if col.startswith('Jan-Wk') and col != 'Jan-Wk1']
            total_future_demand = sum(row[col] for col in future_demand_cols)
            
            constraints.append(f"   - {product}:")
            constraints.append(f"     * 生产量: {initial_prod}")
            constraints.append(f"     * 总未来需求: {total_future_demand}")
            
            if initial_prod < total_future_demand:
                deficit_pct = (1 - initial_prod / total_future_demand) * 100
                constraints.append(f"     * 缺口: {total_future_demand - initial_prod} ({deficit_pct:.1f}%)")
            else:
                surplus_pct = (initial_prod / total_future_demand - 1) * 100
                constraints.append(f"     * 盈余: {initial_prod - total_future_demand} ({surplus_pct:.1f}%)")
    
    # 3. 特殊约束
    if 'channel_region_demand' in analysis_data:
        data = analysis_data['channel_region_demand']
        
        # 筛选PAC地区Reseller Partner在第4周的数据
        pac_reseller_week4 = data[(data['region'] == 'PAC') & 
                                 (data['channel'] == 'Reseller Partners') & 
                                 (data['week'] == 'Jan-Wk4')]
        
        constraints.append("\n3. 特殊约束:")
        
        if not pac_reseller_week4.empty:
            demand_value = pac_reseller_week4['demand'].iloc[0]
            constraints.append(f"   - PAC地区Reseller Partner在第4周的需求: {demand_value} (必须100%满足)")
        else:
            constraints.append("   - 未找到PAC地区Reseller Partner在第4周的数据")
    
    return constraints

# 主函数
def main():
    # 数据文件路径
    data_file = '../data/case2_example.xlsx'
    
    try:
        # 加载数据
        data_dict = load_data(data_file)
        print("数据已加载。")
        
        # 数据预处理
        processed_data = preprocess_data(data_dict)
        print("数据预处理完成。")
        
        # 供需分析
        analysis_results = analyze_supply_demand(processed_data)
        print("供需分析完成。")
        
        # 保存分析数据
        for name, df in analysis_results.items():
            df.to_csv(f'../data/{name}.csv', index=False)
        
        # 可视化分析结果
        visualize_analysis(analysis_results)
        print("可视化图表已生成。")
        
        # 生成约束报告
        constraints = generate_constraint_report(analysis_results)
        
        # 保存约束报告
        with open('../data/constraint_report.txt', 'w') as f:
            f.write("# 供应链约束分析报告\n\n")
            for constraint in constraints:
                f.write(f"{constraint}\n")
        
        print("\n约束分析报告:")
        for constraint in constraints:
            print(constraint)
        
        print("\n分析完成。结果已保存至 ../data/ 目录。")
    
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    # 确保../data目录存在
    os.makedirs('../data', exist_ok=True)
    main() 