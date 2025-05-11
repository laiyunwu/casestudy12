import pandas as pd
import numpy as np
import os
from typing import Dict, Tuple, List, Optional, Union
import streamlit as st
import io
from datetime import datetime

# 设置数据文件路径
CASE1_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "case1", "data", "case1_example.csv")
CASE2_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               "case2", "data", "case2_example.csv")

def load_case1_data(file_path: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    加载案例1销量预测数据
    
    Args:
        file_path: 数据文件路径，如未提供则使用默认示例数据
        
    Returns:
        包含数据表的字典
    """
    try:
        # 使用提供的路径或默认路径
        path = file_path if file_path else CASE1_DATA_PATH
        
        # 检查文件是否存在
        if not os.path.exists(path):
            st.error(f"文件不存在: {path}")
            # 如果文件不存在，使用生成的模拟数据
            return _generate_mock_case1_data()
            
        # 从CSV文件加载数据
        # 跳过CSV中的注释行(以#开头)
        df = pd.read_csv(path, comment='#')
        
        # 返回包含所有数据表的字典
        return {
            "historical_sales": df
        }
    except Exception as e:
        st.error(f"加载数据时出错: {str(e)}")
        # 发生错误时返回模拟数据
        return _generate_mock_case1_data()

def _generate_mock_case1_data() -> Dict[str, pd.DataFrame]:
    """
    生成案例1的模拟数据
    
    Returns:
        包含数据表的字典
    """
    # 创建历史销售数据
    products = ["Superman Plus", "Dwarf Plus", "Princess Plus"]
    regions = ["AMR", "Europe", "PAC"]
    dates = [f"Jan-wk{i}" for i in range(1, 5)] + [f"Dec-wk{i}" for i in range(1, 5)]
    
    data = []
    np.random.seed(42)  # 确保可重现性
    
    for product in products:
        for region in regions:
            for date in dates:
                # 生成一些随机销售数据，但保持一定的模式
                base_sales = 100
                if product == "Superman Plus":
                    base_sales += 50
                elif product == "Princess Plus" and region == "PAC":
                    base_sales += 70
                
                if region == "AMR":
                    base_sales += 30
                
                if "Dec" in date:
                    base_sales += 20  # 年末销售增长
                
                # 添加一些随机波动
                sales = int(base_sales + np.random.normal(0, 20))
                sales = max(10, sales)  # 确保销量为正
                
                # 添加价格数据
                if product == "Superman Plus":
                    price = 999
                elif product == "Dwarf Plus":
                    price = 699
                else:
                    price = 899
                
                # 添加一些随机价格波动
                price_variance = np.random.uniform(-50, 50)
                price = int(price + price_variance)
                
                # 是否有新技术特性
                new_tech = 1 if (product == "Superman Plus" and "Dec" in date) else 0
                
                data.append({
                    "date": date,
                    "product": product,
                    "region": region,
                    "sales": sales,
                    "price": price,
                    "new_tech": new_tech
                })
    
    # 创建DataFrame
    df = pd.DataFrame(data)
    
    # 返回包含所有数据表的字典
    return {
        "historical_sales": df
    }

def validate_case1_data(data: Dict[str, pd.DataFrame]) -> bool:
    """
    验证案例1数据格式是否正确
    
    Args:
        data: 包含数据表的字典
        
    Returns:
        数据格式是否有效
    """
    # 检查必要的数据集是否存在
    if "historical_sales" not in data:
        return False
    
    # 检查必要的列是否存在
    required_columns = ["date", "product", "region", "sales", "price"]
    if not all(col in data["historical_sales"].columns for col in required_columns):
        return False
    
    return True

def load_case2_data(file_path: Optional[str] = None) -> Dict[str, pd.DataFrame]:
    """
    加载案例2供应分配数据
    
    Args:
        file_path: 数据文件路径，如未提供则使用默认示例数据
        
    Returns:
        包含数据表的字典
    """
    # 强制清除 Streamlit 缓存
    try:
        st.cache_data.clear()
    except:
        pass
    
    # 打印当前时间戳，强制每次重新获取数据
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    st.write(f"数据加载时间: {current_time}")
    
    try:
        # 使用提供的路径或默认路径
        path = file_path if file_path else CASE2_DATA_PATH
        
        # 检查文件是否存在
        if not os.path.exists(path):
            st.error(f"文件不存在: {path}")
            # 如果文件不存在，使用生成的模拟数据
            return _generate_mock_case2_data()
        
        # 尝试手动逐行读取并解析CSV
        with open(path, 'r') as file:
            lines = file.readlines()
        
        # 处理总供应量表(Table 1)
        total_supply_data = []
        table1_started = False
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if 'week,total_supply' in line:
                table1_started = True
                continue
            
            if table1_started:
                # 检查是否进入了下一个表格
                if 'week,product,actual_build' in line:
                    break
                
                # 确保正确分割
                parts = line.split(',')
                if len(parts) >= 2:
                    try:
                        total_supply_data.append({
                            'week': parts[0],
                            'total_supply': int(parts[1])
                        })
                    except ValueError:
                        # 如果转换失败，保留原始字符串
                        total_supply_data.append({
                            'week': parts[0],
                            'total_supply': parts[1]
                        })
        
        # 处理实际生产量表(Table 2)
        actual_build_data = []
        table2_started = False
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if 'week,product,actual_build' in line:
                table2_started = True
                continue
            
            if table2_started:
                # 检查是否进入了下一个表格
                if 'product' in line and 'Jan-Wk' in line and 'week' not in line and 'actual_build' not in line:
                    break
                
                # 确保正确分割
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        actual_build_data.append({
                            'week': parts[0],
                            'product': parts[1],
                            'actual_build': int(parts[2])
                        })
                    except ValueError:
                        # 如果转换失败，保留原始字符串
                        actual_build_data.append({
                            'week': parts[0],
                            'product': parts[1],
                            'actual_build': parts[2]
                        })
        
        # 处理需求预测表(Table 3)
        demand_forecast_data = []
        table3_started = False
        header_cols = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if 'product' in line and 'Jan-Wk' in line and 'week' not in line and 'actual_build' not in line:
                table3_started = True
                header_cols = line.split(',')
                continue
            
            if table3_started:
                # 检查是否进入了下一个表格
                if 'channel,region' in line and 'Jan-Wk' in line:
                    break
                
                # 确保正确分割
                parts = line.split(',')
                if len(parts) >= len(header_cols):
                    row_data = {}
                    for i, col in enumerate(header_cols):
                        if i < len(parts):
                            # 将数字字符串转为整数
                            if i > 0:
                                try:
                                    row_data[col] = int(parts[i])
                                except ValueError:
                                    row_data[col] = parts[i]
                            else:
                                row_data[col] = parts[i]
                    demand_forecast_data.append(row_data)
        
        # 处理客户需求表(Table 4)
        customer_demand_data = []
        table4_started = False
        header_cols_t4 = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if 'product,channel,region' in line and 'Jan-Wk' in line:
                table4_started = True
                header_cols_t4 = line.split(',')
                continue
            
            if table4_started:
                # 确保正确分割
                parts = line.split(',')
                if len(parts) >= len(header_cols_t4):
                    row_data = {}
                    for i, col_name in enumerate(header_cols_t4):
                        if i < len(parts):
                            # 将数字字符串转为整数，注意列索引的调整
                            if i >= 3 and parts[i].strip().isdigit():
                                row_data[col_name] = int(parts[i].strip())
                            else:
                                row_data[col_name] = parts[i].strip()
                    customer_demand_data.append(row_data)
        
        # 将解析后的数据转换为DataFrame
        if total_supply_data and actual_build_data and demand_forecast_data and customer_demand_data:
            total_supply = pd.DataFrame(total_supply_data)
            actual_build = pd.DataFrame(actual_build_data)
            demand_forecast = pd.DataFrame(demand_forecast_data)
            customer_demand = pd.DataFrame(customer_demand_data)
            
            # 创建结果字典
            data_dict = {
                "total_supply": total_supply,
                "actual_build": actual_build,
                "demand_forecast": demand_forecast,
                "customer_demand": customer_demand
            }
            
            # 检查数据是否有效
            if validate_case2_data(data_dict):
                return data_dict
        
        # 如果上述方法失败，回退到模拟数据
        st.warning("无法完全解析CSV数据，使用模拟数据进行演示")
        return _generate_mock_case2_data()
    
    except Exception as e:
        st.error(f"加载数据时出错: {str(e)}")
        # 打印完整的堆栈跟踪
        import traceback
        st.error(f"详细错误: {traceback.format_exc()}")
        return _generate_mock_case2_data()

def _generate_mock_case2_data() -> Dict[str, pd.DataFrame]:
    """
    生成案例2的模拟数据
    
    Returns:
        包含数据表的字典
    """
    # 1. 总供应量
    weeks = ["Jan-Wk1", "Jan-Wk2", "Jan-Wk3", "Jan-Wk4", "Jan-Wk5"]
    total_supply_data = []
    
    np.random.seed(42)  # 确保可重现性
    for week in weeks:
        # 每周供应量在800-1000之间波动
        supply = np.random.randint(800, 1001)
        total_supply_data.append({
            "week": week,
            "total_supply": supply
        })
    
    total_supply = pd.DataFrame(total_supply_data)
    
    # 2. 实际生产量
    products = ["Superman Plus", "Dwarf Plus", "Princess Plus"]
    actual_build_data = []
    
    for week in weeks:
        for product in products:
            # 根据产品分配不同的生产量
            if product == "Superman Plus":
                build = np.random.randint(200, 301)
            elif product == "Dwarf Plus":
                build = np.random.randint(150, 251)
            else:  # Princess Plus
                build = np.random.randint(250, 351)
            
            actual_build_data.append({
                "week": week,
                "product": product,
                "actual_build": build
            })
    
    actual_build = pd.DataFrame(actual_build_data)
    
    # 3. 需求预测
    demand_forecast_data = []
    
    # 透视为宽格式
    for product in products:
        row = {"product": product}
        for week in weeks:
            # 每个产品在每个周的需求预测
            if product == "Superman Plus":
                demand = np.random.randint(280, 351)
            elif product == "Dwarf Plus":
                demand = np.random.randint(200, 281)
            else:  # Princess Plus
                demand = np.random.randint(300, 401)
            
            row[week] = demand
        
        demand_forecast_data.append(row)
    
    demand_forecast = pd.DataFrame(demand_forecast_data)
    
    # 4. 客户需求
    channels = ["Online Store", "Retail Store", "Reseller Partners"]
    regions = ["AMR", "Europe", "PAC"]
    customer_demand_data = []
    
    for channel in channels:
        for region in regions:
            row = {
                "channel": channel,
                "region": region
            }
            
            for week in weeks:
                # 根据渠道和地区生成不同的需求量
                base_demand = 100
                
                # 渠道调整
                if channel == "Online Store":
                    base_demand += 20
                elif channel == "Reseller Partners":
                    base_demand += 40
                
                # 地区调整
                if region == "AMR":
                    base_demand += 30
                elif region == "PAC":
                    base_demand += 50
                
                # 为PAC地区的第4周制造一个需求激增
                if week == "Jan-Wk4" and region == "PAC":
                    base_demand += 100
                
                # 添加随机波动
                demand = int(base_demand + np.random.normal(0, 10))
                demand = max(50, demand)  # 确保需求为正
                
                row[week] = demand
            
            customer_demand_data.append(row)
    
    customer_demand = pd.DataFrame(customer_demand_data)
    
    # 返回包含所有数据表的字典
    return {
        "total_supply": total_supply,
        "actual_build": actual_build,
        "demand_forecast": demand_forecast,
        "customer_demand": customer_demand
    }

def validate_case2_data(data: Dict[str, pd.DataFrame]) -> bool:
    """
    验证案例2数据格式是否正确
    
    Args:
        data: 包含数据表的字典
        
    Returns:
        数据格式是否有效
    """
    # 检查必要的数据集是否存在
    required_tables = ["total_supply", "actual_build", "demand_forecast", "customer_demand"]
    if not all(table in data for table in required_tables):
        return False
    
    # 获取所有列名（转为小写以便比较）
    total_supply_cols = [col.lower() for col in data["total_supply"].columns]
    actual_build_cols = [col.lower() for col in data["actual_build"].columns]
    demand_forecast_cols = [col.lower() for col in data["demand_forecast"].columns]
    customer_demand_cols = [col.lower() for col in data["customer_demand"].columns]
    
    # 检查总供应量表格式 - 需要包含week和total_supply列（不区分大小写）
    if not all(col.lower() in total_supply_cols for col in ["week", "total_supply"]):
        return False
    
    # 检查实际生产量表格式 - 需要包含week、product和actual_build列（不区分大小写）
    if not all(col.lower() in actual_build_cols for col in ["week", "product", "actual_build"]):
        return False
    
    # 检查需求预测表格式 - 需要包含product列（不区分大小写）
    if not any(col.lower() == "product" for col in demand_forecast_cols):
        return False
    
    # 检查客户需求表格式 - 需要包含channel和region列（不区分大小写）
    if not all(col.lower() in customer_demand_cols for col in ["channel", "region"]):
        return False
    
    return True 