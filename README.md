# 成本分析系统 (Cost Analyzer)

> 商业前期成本部门筹开规划专用工具
> Version: 1.0.0
> 开发时间：2025年10月

---

## 📖 项目简介

这是一个专为**商业地产前期成本部门**设计的智能化筹开规划系统，用于处理和分析装修工程清单中的成本数据。系统能够智能识别Excel表格结构，自动提取成本信息，并提供交互式可视化分析功能。

**主要应用场景：**
- 装修工程清单成本分析
- 筹开期成本规划与预算控制
- 成本项对比与异常检测
- 可视化报告生成

---

## ✨ 核心功能

### 1️⃣ 智能Excel解析
- **自动工作表检测** - 智能识别最佳数据源工作表
- **表头智能识别** - 基于关键词评分算法自动定位表头
- **多行表头处理** - 支持合并单元格和多层级表头
- **公式自动提取** - 识别并保存列中的计算公式（如：`B=c+(d+e+f)*(1+g)`）
- **代码映射管理** - 提取单字母代码与列名的对应关系
- **分层自动填充** - 自动识别分组行，创建L1/L2层级结构

### 2️⃣ 数据导入管理
- **三阶段安全导入流程**
  - 第一阶段：上传Excel文件
  - 第二阶段：预览解析结果
  - 第三阶段：确认提交或丢弃
- **高效数据存储** - 使用Parquet列式存储格式
- **会话自动保存** - 自动保存处理历史和会话状态
- **元数据索引** - JSON格式维护文件索引

### 3️⃣ 交互式可视化
- **6种图表类型**
  - 条形图（Bar Chart）- 支持聚合和钻取
  - 饼图（Pie Chart）
  - 散点图（Scatter Plot）
  - 折线图（Line Chart）
  - 直方图（Histogram）
  - 箱线图（Box Plot）
- **动态筛选功能**
  - 文本模糊搜索（基于thefuzz库）
  - 多条件组合筛选
  - 自动生成分类下拉菜单
- **数据钻取** - 点击图表查看明细数据
- **数据聚合** - 合并同类项功能
- **交互式报告** - 导出HTML交互式报告
- **静态图表** - 导出PNG格式图片

### 4️⃣ 系统功能
- **处理历史日志** - 查看所有历史处理记录
- **自动更新检测** - 集成GitHub Releases自动更新
- **可打包部署** - 支持PyInstaller打包成EXE

---

## 🏗️ 技术架构

### 技术栈
- **前端框架：** Dash 2.x + Dash Bootstrap Components
- **图表引擎：** Plotly Express
- **数据处理：** Pandas + NumPy
- **文件处理：** openpyxl (Excel读取)
- **数据存储：** Parquet (列式存储)
- **搜索引擎：** thefuzz (模糊匹配)
- **HTTP请求：** requests (更新检测)

### 架构模式
采用经典的**MVC架构**：
- **Model层：** `AppController` + `excel_parser` + Parquet数据
- **View层：** `tab_importer` + `tab_visualizer` + `gui_logger`
- **Controller层：** `app.py`回调函数 + 业务逻辑

### 设计模式
- **三阶段提交模式** - 防止误操作，数据可验证
- **统一可视化引擎** - `get_figure()`统一处理所有图表
- **模块化设计** - 清晰的职责分离，便于扩展

---

## 📁 项目结构

```
cost_analyzer/
├── app/                              # 核心应用包
│   ├── analysis/                     # 数据分析模块
│   │   ├── excel_parser.py          # Excel智能解析器 (149行)
│   │   ├── visualizer.py            # 可视化引擎 (106行)
│   │   └── analysis.py              # 分析流程示例
│   ├── gui_app/                      # GUI界面模块
│   │   ├── tab_importer.py          # 数据导入选项卡 (185行)
│   │   ├── tab_visualizer.py        # 可视化选项卡 (95行)
│   │   └── gui_logger.py            # 日志显示模块 (52行)
│   ├── data_processing/              # 数据处理模块（预留）
│   ├── app_controller.py             # 应用控制器 (142行)
│   ├── updater.py                    # 自动更新检测器 (65行)
│   └── utils.py                      # 工具函数 (23行)
├── data/                             # 数据目录
│   ├── autosave/                     # 自动保存的会话
│   ├── processed/                    # 已处理数据 (gitignore)
│   ├── temp/                         # 临时文件 (gitignore)
│   └── raw/                          # 原始数据 (gitignore)
├── output/                           # 输出文件目录
│   ├── boxplot_comparison/           # 箱线图对比
│   ├── ground_analysis/              # 地面分析图表
│   ├── *.png                         # 静态图表
│   └── interactive_report.html       # 交互式报告
├── scripts/                          # 脚本目录（预留）
├── tests/                            # 测试目录（预留）
├── app.py                            # Dash Web应用主入口 (109行)
├── main.py                           # Tkinter简单GUI入口 (81行)
├── .gitignore                        # Git忽略配置
└── README.md                         # 项目文档（本文件）
```

**代码规模：** 约1061行Python代码

---

## 📊 处理的数据结构

系统处理的装修工程清单数据包含以下典型字段：

### 分类字段
- `功能区_L1` - 一级功能区（如：装饰工程）
- `功能区_L2` - 二级功能区（如：地面、墙面、天花）
- `项目名称` - 具体项目名称

### 成本字段
- `不含税综合单价(元)` - 单价
- `不含税合价(元)` - 总价
- `工程量` - 数量
- `主材单价(元/单位)` - 主材价格
- `损耗率(%)` - 材料损耗率
- `人工费(元/单位)` - 人工成本
- `辅材费(元/单位)` - 辅助材料费
- `机械费(元/单位)` - 机械设备费
- `管理费率、利润率（含企业附加税）(%)` - 管理成本

### 描述字段
- `施工内容及主要做法` - 详细说明
- `计算规则` - 计费规则
- `供应方式或分包说明` - 采购信息
- `单位`、`品牌`、`规格`、`型号`、`备注`、`序号`

### 元数据示例
```json
{
  "formulas": {
    "不含税综合单价(元)": "B=c+(d+e+f)*(1+g)",
    "不含税合价(元)": "C=A*B",
    "主材单价(含损耗)": "c=a(1+b)"
  },
  "codes": {
    "a": "主材单价(元/单位)",
    "b": "损耗率(%)",
    "d": "人工费(元/单位)",
    "e": "辅材费(元/单位)",
    "f": "机械费(元/单位)",
    "g": "管理费率、利润率（含企业附加税）(%)"
  },
  "source_sheet": "【01】装饰工程(地下-2层）",
  "original_filename": "xxx项目精装修工程清单.xlsx"
}
```

---

## 🚀 使用说明

### 启动应用

**方式一：开发环境启动**
```bash
python app.py
```
然后在浏览器中访问：`http://127.0.0.1:8050`

**方式二：使用打包后的EXE（如果已打包）**
```bash
cost_analyzer.exe
```

### 使用流程

#### 第一步：导入数据
1. 切换到"数据导入"选项卡
2. 拖拽或点击上传Excel文件
3. 从下拉菜单选择要解析的工作表
4. 点击"解析并预览"
5. 查看解析结果，确认无误后点击"提交数据"

#### 第二步：可视化分析
1. 切换到"可视化分析"选项卡
2. 选择图表类型（条形图、饼图等）
3. 选择X轴和Y轴字段
4. 使用左侧筛选器过滤数据
5. 点击"更新图表"查看结果
6. 可点击图表元素查看明细数据

#### 第三步：查看历史
1. 切换到"处理历史"选项卡
2. 查看所有历史处理记录
3. 包含文件名、处理时间等信息

---

## 🔄 数据处理流程

```
原始Excel文件
    ↓
[上传文件] (拖拽或点击)
    ↓
[智能解析] (excel_parser.intelligent_read_excel)
    ├─ 自动检测最佳工作表
    ├─ 智能识别表头位置
    ├─ 处理多层级表头
    ├─ 提取公式和代码
    └─ 分层填充（L1/L2）
    ↓
[暂存预览] (AppController.staged_data)
    ├─ 显示DataFrame信息
    └─ 用户确认
    ↓
[提交保存] (AppController.commit_staged_data)
    ├─ 保存为Parquet格式
    ├─ 更新index.json元数据
    └─ 时间戳文件命名
    ↓
[数据加载] (AppController.get_latest_data)
    ↓
[可视化分析] (tab_visualizer)
    ├─ 应用筛选条件
    ├─ 数据聚合（可选）
    ├─ 生成图表
    └─ 支持钻取
    ↓
[输出结果]
    ├─ 交互式HTML报告
    └─ 静态图表（PNG）
```

---

## 🧠 核心算法

### 智能表头识别算法

基于**关键词评分系统**识别表头位置：

```python
def get_row_score(row):
    """
    评分标准：
    1. 关键词匹配（项目、名称、单价、数量、总价等）
    2. 非空单元格比例
    3. 字符串类型占比
    4. 单元格唯一性
    """
    keywords = ['项目', '名称', '单价', '数量', '总价',
                '合计', '单位', '品牌', '规格', '型号',
                '备注', '序号', '类别']
    # 评分逻辑...
    return score
```

### 分层填充算法

自动识别分组行，向下填充创建层级结构：

```python
# 识别功能区分组
if '功能区' in df.columns:
    # 创建L1（一级分类）
    # 创建L2（二级分类）
    # 向下填充层级信息
```

---

## 📦 依赖环境

### Python版本
- Python 3.8+

### 主要依赖库
```
dash>=2.0.0
dash-bootstrap-components
plotly
pandas
numpy
openpyxl
pyarrow  # Parquet支持
thefuzz  # 模糊搜索
requests
packaging
```

**注意：** 项目当前缺少`requirements.txt`，建议后续创建。

---

## 🎯 已实现功能清单

- ✅ 拖拽/点击上传Excel文件
- ✅ 自动检测最佳工作表
- ✅ 智能多行表头识别
- ✅ 公式和代码提取
- ✅ 分层功能区处理（L1/L2）
- ✅ 三阶段导入流程（上传→预览→提交）
- ✅ Parquet格式高效存储
- ✅ 精确匹配筛选
- ✅ 模糊匹配搜索（基于thefuzz）
- ✅ 多条件组合筛选
- ✅ 动态筛选器生成
- ✅ 6种图表类型（条形、饼图、散点、折线、直方图、箱线）
- ✅ 交互式图表（Plotly）
- ✅ 数据聚合（合并同类项）
- ✅ 数据钻取（点击查看明细）
- ✅ 自定义悬停信息
- ✅ 导出交互式HTML报告
- ✅ 导出静态PNG图表
- ✅ 会话自动保存
- ✅ 处理历史日志
- ✅ 自动更新检测（GitHub集成）
- ✅ PyInstaller打包支持
- ✅ 可移植路径处理

---

## 🔮 未来扩展方向

### 待开发模块
- `data_processing/` - 高级数据处理功能
- `scripts/` - 批处理脚本
- `tests/` - 单元测试和集成测试

### 功能建议
1. **数据分析增强**
   - 成本趋势分析
   - 异常值自动检测
   - 成本预测模型
   - 多项目对比分析

2. **报告功能**
   - Word/PDF报告自动生成
   - 自定义报告模板
   - 批量导出功能

3. **协作功能**
   - 多用户支持
   - 数据版本控制
   - 审批工作流

4. **性能优化**
   - 大文件处理优化
   - 图表渲染性能提升
   - 缓存机制

5. **系统增强**
   - 日志系统完善
   - 配置文件管理
   - 插件系统
   - API接口

---

## 📝 开发历史

```
97c5b81 - Update .gitignore to exclude data/raw and untrack large files (4周前)
e687b99 - Apply .gitignore and clean file tracking (4周前)
33e5cdf - Save all current work before applying gitignore (4周前)
4e025e4 - 完成表头阅读和表格输出功能 (4周前)
894de82 - Initial commit (4周前)
```

---

## 🔑 关键文件路径速查

### 入口文件
- `D:\Coding\cost_analyzer\app.py` - Dash Web应用主入口
- `D:\Coding\cost_analyzer\main.py` - Tkinter简易版入口

### 核心模块
- `app\app_controller.py` - 应用控制器（数据管理）
- `app\analysis\excel_parser.py` - Excel智能解析器
- `app\analysis\visualizer.py` - 可视化引擎
- `app\analysis\analysis.py` - 分析流程示例

### GUI模块
- `app\gui_app\tab_importer.py` - 数据导入界面
- `app\gui_app\tab_visualizer.py` - 可视化分析界面
- `app\gui_app\gui_logger.py` - 处理历史日志界面

### 工具模块
- `app\utils.py` - 路径工具（PyInstaller支持）
- `app\updater.py` - GitHub自动更新检测

---


---



---



---

**最后更新时间：** 2025年11月25日
**文档版本：** 1.0.0