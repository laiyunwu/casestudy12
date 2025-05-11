"""
供应分配优化模块
使用PuLP线性规划实现供应链分配优化
"""
from pulp import *
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
import streamlit as st

def optimize_supply_allocation(data: Dict[str, pd.DataFrame], 
                               product_priorities: Optional[Dict[str, int]] = None,
                               channel_priorities: Optional[Dict[str, int]] = None,
                               region_priorities: Optional[Dict[str, int]] = None,
                               special_constraints: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
    """
    执行供应分配优化
    
    Args:
        data: 包含总供应量、实际生产量、需求预测和客户需求的数据字典
        product_priorities: 产品优先级，键为产品名称，值为优先级权重
        channel_priorities: 渠道优先级，键为渠道名称，值为优先级权重
        region_priorities: 区域优先级，键为区域名称，值为优先级权重
        special_constraints: 特殊约束列表，每个约束是一个字典，包含产品、渠道、区域、周和满足率
        
    Returns:
        优化结果数据框
    """
    # 1. 提取数据
    total_supply_df = data['total_supply']
    actual_build_df = data['actual_build'] 
    # demand_forecast_df is likely empty or not structured as originally expected, given the new CSV.
    # We will primarily rely on customer_demand_df for demand specifics.
    demand_forecast_df = data.get('demand_forecast', pd.DataFrame()) # Handle if it's missing
    customer_demand_df = data['customer_demand']
    
    # 2. 定义索引集
    # 从 customer_demand_df 和 actual_build_df 获取唯一的产品，确保覆盖所有相关产品
    products_from_demand = customer_demand_df['product'].unique().tolist() if not customer_demand_df.empty else []
    products_from_build = actual_build_df['product'].unique().tolist() if not actual_build_df.empty else []
    products = sorted(list(set(products_from_demand + products_from_build)))
    
    channels = customer_demand_df['channel'].unique().tolist() if not customer_demand_df.empty else []
    regions = customer_demand_df['region'].unique().tolist() if not customer_demand_df.empty else []
    
    # 提取周数据，从 customer_demand_df (优先) 或 total_supply_df
    if not customer_demand_df.empty:
        weeks = [col for col in customer_demand_df.columns if 'wk' in col.lower() or 'week' in col.lower() and col not in ['product', 'channel', 'region']]
    elif not total_supply_df.empty:
        weeks = total_supply_df['week'].unique().tolist()
    else: # Fallback if both are empty, though unlikely for a valid case
        weeks = [col for col in demand_forecast_df.columns if 'wk' in col.lower() or 'week' in col.lower() and col != 'product']

    # 确保 'Default' 存在于 channels 和 regions 列表中，用于后续的优先级处理
    if 'Default' not in channels: channels.append('Default')
    if 'Default' not in regions: regions.append('Default')
    channels = sorted(list(set(channels)))
    regions = sorted(list(set(regions)))
    
    # 3. 设置默认优先级
    if product_priorities is None:
        # 默认产品优先级 - 可根据业务需求调整
        product_priorities = {product: 5 for product in products}
        # 示例：提高某些产品的优先级
        for product in products:
            if 'plus' in product.lower():
                product_priorities[product] = 8  # 高端产品优先级更高
            elif 'mini' in product.lower():
                product_priorities[product] = 3  # 低端产品优先级较低
    
    if channel_priorities is None:
        # 默认渠道优先级
        channel_priorities = {
            'Default': 1,
            'Online Store': 7,
            'Retail Store': 5,
            'Reseller Partners': 8
        }
    
    if region_priorities is None:
        # 默认区域优先级 - 通常所有区域平等，但可根据业务需求调整
        region_priorities = {region: 1 for region in regions}
    
    # 4. 转换数据为优化模型所需格式
    # 总供应量 - 转为字典
    total_supply = {
        row['week']: row['total_supply'] 
        for _, row in total_supply_df.iterrows()
    }
    
    # 实际生产量 - 转为字典
    cumulative_build = {
        (row['product'], row['week']): row['actual_build']
        for _, row in actual_build_df.iterrows()
    }
    
    # 预处理需求数据 - 创建需求字典
    demand = {}

    # 初始化所有可能的 (p, c, r, w) 组合的需求为0
    # 这确保了即使CSV中没有某个组合，模型变量也有对应的需求值(0)
    # 从而避免在目标函数中因缺少键或除以0而出错
    for p_iter in products:
        for c_iter in channels:
            for r_iter in regions:
                for w_iter in weeks:
                    demand[(p_iter, c_iter, r_iter, w_iter)] = 0.0

    # 直接从 customer_demand_df (Table 4) 填充需求数据
    # 这个表现在是详细需求的主要来源
    if not customer_demand_df.empty:
        for _, row in customer_demand_df.iterrows():
            product = row['product']
            channel = row['channel']
            region = row['region']
            for week_col in weeks:
                if week_col in row.index and pd.notna(row[week_col]):
                    try:
                        demand_value = float(row[week_col])
                        # 修改为累加需求，而不是覆盖
                        current_demand = demand.get((product, channel, region, week_col), 0.0)
                        demand[(product, channel, region, week_col)] = current_demand + demand_value
                    except ValueError:
                        st.warning(f"无法将需求值 '{row[week_col]}' 转换为浮点数，在 {product}, {channel}, {region}, {week_col}. 跳过此条目.")
                        # 如果转换失败，保持原有值（可能为0）或可以记录为错误，但不要改变累加逻辑
                        # demand[(product, channel, region, week_col)] = demand.get((product, channel, region, week_col), 0.0)
    
    # 5. 创建优化问题
    prob = LpProblem("Supply_Allocation", LpMaximize)
    
    # 6. 定义决策变量
    x = LpVariable.dicts("allocation", 
                        [(p, c, r, w) for p in products 
                                        for c in channels 
                                        for r in regions 
                                        for w in weeks],
                        lowBound=0, 
                        cat='Continuous')
    
    # 7. 计算复合优先级
    priority = {}
    for p in products:
        for c in channels:
            for r in regions:
                p_priority = product_priorities.get(p, 5)
                c_priority = channel_priorities.get(c, 1)
                r_priority = region_priorities.get(r, 1)
                priority[(p,c,r)] = p_priority * c_priority * r_priority
    
    # 8. 定义目标函数: 最大化优先级加权的满足率
    objective_terms = []
    for p in products:
        for c in channels:
            for r in regions:
                for w in weeks:
                    if (p,c,r,w) in demand and demand[(p,c,r,w)] > 0:
                        objective_terms.append(
                            priority[(p,c,r)] * x[(p,c,r,w)] / demand[(p,c,r,w)]
                        )
    
    if objective_terms:
        prob += lpSum(objective_terms)
    
    # 9. 添加约束条件
    
    # 约束1: 每周总分配量不超过总供应量
    for w in weeks:
        if w in total_supply:
            prob += lpSum([x[(p,c,r,w)] for p in products 
                                       for c in channels 
                                       for r in regions]) <= total_supply[w]
    
    # 约束2: 分配量不超过需求量
    for p in products:
        for c in channels:
            for r in regions:
                for w in weeks:
                    if (p,c,r,w) in demand:
                        prob += x[(p,c,r,w)] <= demand[(p,c,r,w)]
    
    # 约束3: 添加特殊约束
    if special_constraints:
        for constraint in special_constraints:
            p = constraint.get('product')
            c = constraint.get('channel')
            r = constraint.get('region')
            w = constraint.get('week')
            satisfaction_rate = constraint.get('satisfaction_rate', 1.0)  # 默认100%满足
            
            if all([p, c, r, w]) and (p,c,r,w) in demand and demand[(p,c,r,w)] > 0:
                prob += x[(p,c,r,w)] >= satisfaction_rate * demand[(p,c,r,w)]
    
    # 10. 求解优化问题
    prob.solve(PULP_CBC_CMD(msg=False))  # 静默求解
    
    # 11. 处理结果
    if LpStatus[prob.status] == "Optimal":
        # 创建结果数据框
        results = []
        for p in products:
            for c in channels:
                for r in regions:
                    for w in weeks:
                        if (p,c,r,w) in demand and demand[(p,c,r,w)] > 0:
                            allocation = x[(p,c,r,w)].value()
                            if allocation is not None and allocation > 0:
                                results.append({
                                    "product": p,
                                    "channel": c,
                                    "region": r,
                                    "week": w,
                                    "demand": demand[(p,c,r,w)],
                                    "allocation": allocation,
                                    "satisfaction": allocation / demand[(p,c,r,w)] if demand[(p,c,r,w)] > 0 else 1,
                                    "priority": priority.get((p,c,r), 1)
                                })
        
        # 转换为DataFrame
        if results:
            return pd.DataFrame(results)
        else:
            return pd.DataFrame(columns=["product", "channel", "region", "week", 
                                       "demand", "allocation", "satisfaction", "priority"])
    else:
        st.error(f"未找到最优解，状态: {LpStatus[prob.status]}")
        return pd.DataFrame(columns=["product", "channel", "region", "week", 
                                   "demand", "allocation", "satisfaction", "priority"])

def get_summary_stats(result_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    计算优化结果的汇总统计信息
    
    Args:
        result_df: 优化结果数据框
        
    Returns:
        包含不同维度汇总结果的字典
    """
    summary = {}
    
    # 1. 按产品汇总
    if not result_df.empty:
        product_summary = result_df.groupby("product").agg({
            "demand": "sum",
            "allocation": "sum"
        })
        product_summary["satisfaction"] = product_summary["allocation"] / product_summary["demand"]
        summary["product"] = product_summary
        
        # 2. 按产品和周汇总
        product_week_summary = result_df.groupby(["product", "week"]).agg({
            "demand": "sum",
            "allocation": "sum"
        })
        product_week_summary["satisfaction"] = product_week_summary["allocation"] / product_week_summary["demand"]
        summary["product_week"] = product_week_summary
        
        # 3. 按产品、渠道和区域汇总
        channel_region_summary = result_df.groupby(["product", "channel", "region"]).agg({
            "demand": "sum",
            "allocation": "sum"
        })
        channel_region_summary["satisfaction"] = channel_region_summary["allocation"] / channel_region_summary["demand"]
        summary["channel_region"] = channel_region_summary
        
        # 4. 按周汇总
        week_summary = result_df.groupby("week").agg({
            "demand": "sum",
            "allocation": "sum"
        })
        week_summary["satisfaction"] = week_summary["allocation"] / week_summary["demand"]
        summary["week"] = week_summary
    
    return summary 