"""
Qingxin Translator - Terminology Table
术语表：对常见专有名词进行替换
"""

from typing import Dict, Tuple

# 术语表：中文 -> 英文
# 格式：(中文, 英文) -> (替换后的英文)
TERMINOLOGY: Dict[str, str] = {
    # ==================== 日常生活 ====================
    # 社交应用
    "微信": "WeChat",
    "支付宝": "Alipay",
    "淘宝": "Taobao",
    "京东": "JD.com",
    "抖音": "TikTok",
    "微博": "Weibo",
    "小红书": "Xiaohongshu",
    "美团": "Meituan",
    "饿了么": "Ele.me",
    "拼多多": "Pinduoduo",
    "滴滴": "DiDi",
    "高德地图": "Amap",
    "百度地图": "Baidu Maps",
    "哔哩哔哩": "Bilibili",
    "知乎": "Zhihu",
    "豆瓣": "Douban",
    
    # 品牌
    "华为": "Huawei",
    "小米": "Xiaomi",
    "联想": "Lenovo",
    "海尔": "Haier",
    "格力": "Gree",
    "美的": "Midea",
    "比亚迪": "BYD",
    "蔚来": "NIO",
    "理想": "Li Auto",
    "小鹏": "XPeng",
    
    # 食物
    "饺子": "dumplings",
    "包子": "steamed buns",
    "馒头": "steamed bread",
    "豆腐": "tofu",
    "火锅": "hot pot",
    "炒饭": "fried rice",
    "炒面": "chow mein",
    "春卷": "spring rolls",
    "月饼": "mooncake",
    "粽子": "zongzi",
    "油条": "youtiao",
    "豆浆": "soy milk",
    "奶茶": "milk tea",
    
    # 节日
    "春节": "Chinese New Year",
    "中秋节": "Mid-Autumn Festival",
    "端午节": "Dragon Boat Festival",
    "元宵节": "Lantern Festival",
    "清明节": "Qingming Festival",
    "重阳节": "Double Ninth Festival",
    "国庆节": "National Day",
    "劳动节": "Labor Day",
    
    # 称谓
    "爷爷": "grandfather",
    "奶奶": "grandmother",
    "外公": "maternal grandfather",
    "外婆": "maternal grandmother",
    "叔叔": "uncle",
    "阿姨": "aunt",
    "表哥": "cousin (older male)",
    "表姐": "cousin (older female)",
    
    # ==================== 计算机 ====================
    # 编程语言
    "Python": "Python",
    "Java": "Java",
    "JavaScript": "JavaScript",
    "TypeScript": "TypeScript",
    "C++": "C++",
    "C#": "C#",
    "Go": "Go",
    "Rust": "Rust",
    "Swift": "Swift",
    "Kotlin": "Kotlin",
    "Ruby": "Ruby",
    "PHP": "PHP",
    "Scala": "Scala",
    "R语言": "R",
    
    # 技术概念
    "人工智能": "Artificial Intelligence",
    "机器学习": "Machine Learning",
    "深度学习": "Deep Learning",
    "神经网络": "Neural Network",
    "自然语言处理": "Natural Language Processing",
    "计算机视觉": "Computer Vision",
    "强化学习": "Reinforcement Learning",
    "迁移学习": "Transfer Learning",
    "联邦学习": "Federated Learning",
    "生成对抗网络": "Generative Adversarial Network",
    "卷积神经网络": "Convolutional Neural Network",
    "循环神经网络": "Recurrent Neural Network",
    "变换器": "Transformer",
    "注意力机制": "Attention Mechanism",
    "大语言模型": "Large Language Model",
    "微调": "Fine-tuning",
    "提示工程": "Prompt Engineering",
    "向量数据库": "Vector Database",
    "嵌入": "Embedding",
    
    # Web开发
    "前端": "Frontend",
    "后端": "Backend",
    "全栈": "Full Stack",
    "响应式设计": "Responsive Design",
    "单页应用": "Single Page Application",
    "渐进式Web应用": "Progressive Web Application",
    "RESTful": "RESTful",
    "GraphQL": "GraphQL",
    "WebSocket": "WebSocket",
    "微服务": "Microservices",
    "容器化": "Containerization",
    "持续集成": "Continuous Integration",
    "持续部署": "Continuous Deployment",
    "DevOps": "DevOps",
    
    # 数据库
    "关系型数据库": "Relational Database",
    "非关系型数据库": "NoSQL Database",
    "缓存": "Cache",
    "索引": "Index",
    "主键": "Primary Key",
    "外键": "Foreign Key",
    "事务": "Transaction",
    "分库分表": "Sharding",
    "读写分离": "Read-Write Splitting",
    "数据库迁移": "Database Migration",
    
    # 云服务
    "云计算": "Cloud Computing",
    "云原生": "Cloud Native",
    "服务器": "Server",
    "虚拟机": "Virtual Machine",
    "负载均衡": "Load Balancing",
    "内容分发网络": "Content Delivery Network",
    "对象存储": "Object Storage",
    "消息队列": "Message Queue",
    "服务网格": "Service Mesh",
    "无服务器": "Serverless",
    
    # 安全
    "网络安全": "Cybersecurity",
    "防火墙": "Firewall",
    "加密": "Encryption",
    "解密": "Decryption",
    "身份验证": "Authentication",
    "授权": "Authorization",
    "漏洞": "Vulnerability",
    "渗透测试": "Penetration Testing",
    "零信任": "Zero Trust",
    
    # ==================== 数据分析 ====================
    # 基础概念
    "数据分析": "Data Analysis",
    "数据科学": "Data Science",
    "数据挖掘": "Data Mining",
    "数据仓库": "Data Warehouse",
    "数据湖": "Data Lake",
    "数据治理": "Data Governance",
    "数据质量": "Data Quality",
    "数据清洗": "Data Cleaning",
    "数据转换": "Data Transformation",
    "数据可视化": "Data Visualization",
    "探索性数据分析": "Exploratory Data Analysis",
    
    # 统计学
    "均值": "Mean",
    "中位数": "Median",
    "众数": "Mode",
    "标准差": "Standard Deviation",
    "方差": "Variance",
    "协方差": "Covariance",
    "相关系数": "Correlation Coefficient",
    "正态分布": "Normal Distribution",
    "泊松分布": "Poisson Distribution",
    "假设检验": "Hypothesis Testing",
    "置信区间": "Confidence Interval",
    "p值": "p-value",
    "回归分析": "Regression Analysis",
    "时间序列": "Time Series",
    "聚类分析": "Cluster Analysis",
    "主成分分析": "Principal Component Analysis",
    "因子分析": "Factor Analysis",
    "贝叶斯": "Bayesian",
    
    # 机器学习
    "监督学习": "Supervised Learning",
    "无监督学习": "Unsupervised Learning",
    "半监督学习": "Semi-supervised Learning",
    "分类": "Classification",
    "回归": "Regression",
    "聚类": "Clustering",
    "降维": "Dimensionality Reduction",
    "特征工程": "Feature Engineering",
    "特征选择": "Feature Selection",
    "过拟合": "Overfitting",
    "欠拟合": "Underfitting",
    "交叉验证": "Cross Validation",
    "网格搜索": "Grid Search",
    "随机搜索": "Random Search",
    "集成学习": "Ensemble Learning",
    "决策树": "Decision Tree",
    "随机森林": "Random Forest",
    "梯度提升": "Gradient Boosting",
    "支持向量机": "Support Vector Machine",
    "朴素贝叶斯": "Naive Bayes",
    "K近邻": "K-Nearest Neighbors",
    "逻辑回归": "Logistic Regression",
    "线性回归": "Linear Regression",
    
    # 深度学习框架
    "张量": "Tensor",
    "反向传播": "Backpropagation",
    "梯度下降": "Gradient Descent",
    "学习率": "Learning Rate",
    "批次大小": "Batch Size",
    "轮次": "Epoch",
    "损失函数": "Loss Function",
    "激活函数": "Activation Function",
    "优化器": "Optimizer",
    "正则化": "Regularization",
    "Dropout": "Dropout",
    "批归一化": "Batch Normalization",
    
    # 大数据
    "大数据": "Big Data",
    "分布式计算": "Distributed Computing",
    "流处理": "Stream Processing",
    "批处理": "Batch Processing",
    "ETL": "ETL",
    "数据管道": "Data Pipeline",
    "数据集成": "Data Integration",
    "实时处理": "Real-time Processing",
    
    # BI工具
    "商业智能": "Business Intelligence",
    "仪表盘": "Dashboard",
    "报表": "Report",
    "维度": "Dimension",
    "度量": "Measure",
    "KPI": "KPI",
    "数据透视表": "Pivot Table",
    
    # 常用工具
    "电子表格": "Spreadsheet",
    "结构化查询语言": "SQL",
    "数据框": "DataFrame",
    "数据集": "Dataset",
    "特征": "Feature",
    "标签": "Label",
    "目标变量": "Target Variable",
    "训练集": "Training Set",
    "测试集": "Test Set",
    "验证集": "Validation Set",
}


def apply_terminology(text: str, source_lang: str, target_lang: str) -> str:
    """
    应用术语表替换
    
    Args:
        text: 翻译后的文本
        source_lang: 源语言
        target_lang: 目标语言
        
    Returns:
        替换后的文本
    """
    if source_lang == "zh" and target_lang == "en":
        # 中译英：替换中文术语为英文
        for zh, en in TERMINOLOGY.items():
            if zh in text:
                # 检查翻译结果中是否包含错误翻译
                # 如果原文包含术语，但翻译结果不正确，则替换
                text = text.replace(zh, en)
    elif source_lang == "en" and target_lang == "zh":
        # 英译中：替换英文术语为中文
        en_to_zh = {v: k for k, v in TERMINOLOGY.items()}
        for en, zh in en_to_zh.items():
            if en.lower() in text.lower():
                # 不区分大小写匹配
                import re
                pattern = re.compile(re.escape(en), re.IGNORECASE)
                text = pattern.sub(zh, text)
    
    return text


def get_term_suggestions(text: str, lang: str) -> list:
    """
    获取术语建议
    
    Args:
        text: 输入文本
        lang: 语言
        
    Returns:
        匹配的术语列表
    """
    suggestions = []
    
    if lang == "zh":
        for zh in TERMINOLOGY.keys():
            if zh in text:
                suggestions.append((zh, TERMINOLOGY[zh]))
    else:
        en_to_zh = {v: k for k, v in TERMINOLOGY.items()}
        for en in en_to_zh.keys():
            if en.lower() in text.lower():
                suggestions.append((en, en_to_zh[en]))
    
    return suggestions
