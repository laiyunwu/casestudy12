# 数据科学案例分析与可视化应用

本项目包含两个数据科学案例的分析和可视化：
1. **销量预测分析**：基于历史数据预测产品未来15周的销量
2. **供应分配优化**：在有限供应下实现多产品、多渠道、多地区的最优分配

## 项目结构

```
project/
├── case1/                     # 销量预测案例
│   ├── notebooks/             # 分析笔记本
│   ├── models/                # 预测模型
│   └── data/                  
│       └── case1_example.xlsx # 标准化示例数据
├── case2/                     # 供应分配案例
│   ├── notebooks/             # 分析笔记本
│   ├── models/                # 优化模型
│   └── data/
│       └── case2_example.xlsx # 标准化示例数据
├── app/                       # Streamlit应用
│   ├── app.py                 # 主应用入口
│   ├── pages/                 # 多页面应用
│   │   ├── case1_app.py       # 销量预测页面
│   │   └── case2_app.py       # 供应分配页面
│   └── utils/                 # 共用函数
├── requirements.txt           # 项目依赖
└── README.md                  # 项目说明
```

## 安装与运行

1. 克隆仓库:
```bash
git clone <repository-url>
cd <repository-name>
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 运行应用:
```bash
cd project
streamlit run app/app.py
```

## 功能亮点

- **数据可视化仪表盘**：直观展示分析结果和预测
- **交互式参数调整**：允许用户调整模型参数和优化策略
- **文件上传功能**：用户可以上传自己的数据
- **情景模拟**：测试不同假设下的预测和分配结果
- **自动生成洞察**：提供关键发现和建议

## 案例说明

### Case 1: 销量预测
分析历史销售数据，预测新产品在不同地区未来15周的销量。考虑价格变化、新技术特性和季节性因素。

### Case 2: 供应分配优化
在有限资源条件下，优化三个产品线（Superman, Superman Plus, Superman Mini）在三个销售渠道和三个地区的供应分配，同时满足特定约束条件。

## 联系方式

请联系 [您的邮箱] 获取更多信息。 