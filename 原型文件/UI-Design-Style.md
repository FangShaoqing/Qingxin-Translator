# 科技感设计风格指南

## 设计哲学

一种现代、精致、富有科技感的UI设计风格。核心特征是**深色背景**、**半透明层次**、**发光强调色**和**精细的微交互**。适用于任何需要呈现专业、现代、科技感的应用。

---

## 色彩系统

### 核心色彩逻辑

| 角色 | 深色模式 | 浅色模式 |
|------|----------|----------|
| 背景 | #0b0f17 | #f8f9fc |
| 表面 | rgba(255,255,255,.04) | rgba(0,0,0,.03) |
| 边框 | rgba(255,255,255,.07) | rgba(0,0,0,.08) |
| 主文字 | #eef2f9 | #1a1d26 |
| 次文字 | #9aa3b5 | #6b7280 |
| 辅助文字 | #5b6478 | #9ca3af |

### 品牌色板

```
主色 (Primary):     #2fe0c0  → 活力、信任、科技感
主色深:             #19b89c
主色亮:             #34e7c4
主色发光:           rgba(47,224,192,.6)

辅助色:
  紫色 (Violet):    #9d8cff  → 创造力、高级感
  琥珀 (Amber):     #ffb454  → 警示、温暖
  酸橙 (Lime):      #7fd99a  → 成功、增长
  蓝色 (Blue):      #6ea8ff  → 信息、稳定
  珊瑚 (Coral):     #ff7a6b  → 错误、危险
```

### 颜色使用原则
- 主色用于核心交互元素（按钮、进度条、选中态）
- 辅助色用于状态区分和数据可视化
- 背景使用极低透明度的白色叠加，创造层次感

---

## 字体系统

### 字体栈

```css
/* 无衬线字体（正文） */
--font-sans: "HarmonyOS Sans SC", "PingFang SC", "Hiragino Sans GB", 
             "Microsoft YaHei", system-ui, -apple-system, "Segoe UI", sans-serif;

/* 等宽字体（数据、代码） */
--font-mono: "Cascadia Code", "JetBrains Mono", "SF Mono", 
             "HarmonyOS Sans SC", ui-monospace, Consolas, monospace;
```

### 字号阶梯

| 角色 | 字号 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| Display | clamp(26px,7cqw,44px) | 800 | 1 | 核心大数字 |
| H1 | clamp(20px,4cqw,32px) | 700 | 1.2 | 页面标题 |
| H2 | clamp(16px,2.5cqw,22px) | 700 | 1.3 | 区块标题 |
| Body | 14px | 400 | 1.55 | 正文内容 |
| Caption | 12px | 600 | 1.4 | 辅助说明 |
| Label | 10.5px | 700 | 1 | 标签、徽章 |
| Micro | 9.5px | 600 | 1.4 | 极小文字 |

### 字体特性
- **数字等宽**：`font-variant-numeric: tabular-nums` 确保数字对齐
- **字母间距**：标签和小字使用 `letter-spacing: .1em-.3em` 增加可读性
- **大写标签**：`text-transform: uppercase` 用于分类标签

---

## 组件规范

### 卡片 (Card)

```css
.card {
  border-radius: 16px;
  padding: 18px 22px;
  background: linear-gradient(180deg, 
    rgba(255,255,255,.04), 
    rgba(255,255,255,.013));
  border: 1px solid rgba(255,255,255,.07);
  box-shadow: 0 14px 34px -18px rgba(0,0,0,.7),
              inset 0 1px 0 rgba(255,255,255,.05);
  transition: transform .25s, box-shadow .25s;
}

/* 悬浮效果 */
.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 46px -20px rgba(0,0,0,.8),
              inset 0 1px 0 rgba(255,255,255,.08);
}
```

### 按钮

**基础按钮 (Ghost)**
```css
.btn-ghost {
  padding: 9px 14px;
  border-radius: 9px;
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.07);
  color: #9aa3b5;
  font: 600 12px/1 var(--font-sans);
  cursor: pointer;
  transition: .18s;
}

.btn-ghost:hover {
  color: #eef2f9;
  border-color: rgba(255,255,255,.13);
  background: rgba(255,255,255,.07);
  transform: translateY(-1px);
}
```

**主按钮 (Primary)**
```css
.btn-primary {
  padding: 9px 14px;
  border-radius: 9px;
  background: linear-gradient(150deg, #2fe0c0, #19b89c);
  border: none;
  color: #04201d;
  font: 800 12px/1 var(--font-sans);
  box-shadow: 0 8px 20px -10px rgba(47,224,192,.8);
  cursor: pointer;
  transition: .18s;
}

.btn-primary:hover {
  transform: translateY(-1px);
  filter: brightness(1.06);
}
```

### 输入框 (Input)

```css
.input {
  padding: 11px 14px;
  background: rgba(0,0,0,.22);
  border: 1px solid rgba(255,255,255,.07);
  border-radius: 10px;
  color: #eef2f9;
  font: 12px/1.45 var(--font-mono);
  outline: none;
  transition: border-color .15s;
}

.input:focus {
  border-color: #2fe0c0;
}

.input::placeholder {
  color: #5b6478;
}
```

### 标签/徽章 (Badge)

```css
.badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border-radius: 20px;
  font: 700 9.5px/1 var(--font-mono);
  letter-spacing: .12em;
}

.badge-success {
  background: rgba(47,224,192,.13);
  color: #2fe0c0;
}

.badge-warning {
  background: rgba(255,122,107,.14);
  color: #ff7a6b;
}

.badge-neutral {
  background: rgba(255,255,255,.05);
  color: #9aa3b5;
}
```

### 模态框 (Modal)

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(4,6,10,.66);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background: #0c1018;
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 15px;
  padding: 18px;
  box-shadow: 0 30px 80px -30px #000;
}
```

---

## 视觉效果

### 毛玻璃 (Glassmorphism)

```css
.glass {
  background: rgba(255,255,255,.04);
  backdrop-filter: saturate(120%) blur(6px);
  -webkit-backdrop-filter: saturate(120%) blur(6px);
  border: 1px solid rgba(255,255,255,.07);
}
```

### 发光效果 (Glow)

```css
.glow {
  box-shadow: 0 0 10px var(--glow-color, rgba(47,224,192,.6));
}

/* 内发光 */
.glow-inner {
  box-shadow: inset 0 0 10px rgba(47,224,192,.3);
}
```

### 鼠标追踪光效

```css
.card::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  opacity: 0;
  transition: opacity .35s;
  background: radial-gradient(
    220px circle at var(--mouse-x, 50%) var(--mouse-y, 0%),
    rgba(125,255,225,.07),
    rgba(125,200,255,.03) 40%,
    transparent 65%
  );
  mix-blend-mode: screen;
}

.card:hover::before {
  opacity: 1;
}
```

### 渐变边框

```css
.gradient-border {
  position: relative;
}

.gradient-border::after {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent-color, #2fe0c0);
  border-radius: 15px 0 0 15px;
  opacity: .9;
}
```

---

## 动画系统

### 缓动函数

```css
:root {
  --ease-out-expo: cubic-bezier(.2, .8, .2, 1);
  --ease-out-back: cubic-bezier(.34, 1.56, .64, 1);
  --ease-spring: cubic-bezier(.175, .885, .32, 1.275);
}
```

### 标准动画

| 动画 | 时长 | 缓动 | 用途 |
|------|------|------|------|
| 微交互 | 0.15-0.18s | ease | 按钮悬浮、状态切换 |
| 页面过渡 | 0.25-0.35s | --ease-out-expo | 卡片悬浮、展开收起 |
| 数据动画 | 0.9-1.3s | --ease-out-expo | 数字计数、进度变化 |
| 入场动画 | 0.5-0.7s | ease | 元素淡入、位移 |

### 入场动画示例

```css
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-in {
  animation: fadeInUp .5s var(--ease-out-expo) forwards;
  animation-delay: calc(var(--index, 0) * 55ms);
}
```

### 数字计数动画

```css
.number-animate {
  font-variant-numeric: tabular-nums;
}
```

### 减少动画偏好

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.001s !important;
    transition-duration: 0.001s !important;
  }
}
```

---

## 布局系统

### 网格

```css
/* 12列网格 */
.grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 18px;
}

/* 响应式列跨度 */
.span-4 { grid-column: span 4; }
.span-6 { grid-column: span 6; }
.span-12 { grid-column: span 12; }

@media (max-width: 768px) {
  .grid {
    gap: 12px;
  }
  .span-4, .span-6 {
    grid-column: span 12;
  }
}
```

### Flex 布局模式

```css
/* 水平居中对齐 */
.flex-center {
  display: flex;
  align-items: center;
  gap: 14px;
}

/* 垂直堆叠 */
.flex-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 自动留白 */
.spacer {
  flex: 1;
}
```

### 间距系统

```css
:root {
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 12px;
  --space-lg: 16px;
  --space-xl: 20px;
  --space-2xl: 24px;
}
```

---

## 交互模式

### 悬浮状态

```css
/* 基础悬浮 */
.hover-lift {
  transition: transform .25s, box-shadow .25s;
}

.hover-lift:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 46px -20px rgba(0,0,0,.8);
}

/* 按钮悬浮 */
.hover-lift-sm:hover {
  transform: translateY(-1px);
}
```

### 点击反馈

```css
:active {
  transform: scale(0.98);
}
```

### 焦点样式

```css
:focus-visible {
  outline: 2px solid #2fe0c0;
  outline-offset: 2px;
}
```

### 脉冲动画

```css
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(47,224,192,.5); }
  70% { box-shadow: 0 0 0 7px rgba(47,224,192,0); }
  100% { box-shadow: 0 0 0 0 rgba(47,224,192,0); }
}

.pulse {
  animation: pulse 2.2s infinite;
}
```

---

## 状态指示

### 颜色语义

| 状态 | 颜色 | 用途 |
|------|------|------|
| 正常/成功 | #2fe0c0 (Teal) | 在线、完成、可用 |
| 警告 | #ffb454 (Amber) | 注意、即将到期 |
| 错误/危险 | #ff7a6b (Coral) | 错误、离线、紧急 |
| 信息 | #6ea8ff (Blue) | 提示、链接 |
| 增长 | #7fd99a (Lime) | 正向指标 |
| 高级 | #9d8cff (Violet) | 专业版、高级功能 |

### 状态图标

```css
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-color, #2fe0c0);
}

.status-online {
  animation: pulse 2.2s infinite;
}
```

---

## 响应式设计

### 断点

```css
/* 平板 */
@media (max-width: 1100px), (max-height: 760px) {
  /* 简化布局，增加垂直空间 */
}

/* 手机 */
@media (max-width: 768px) {
  /* 单列布局，增大触控区域 */
  .card {
    padding: 14px 16px;
  }
  
  .grid {
    gap: 12px;
  }
}
```

### 安全区域

```css
body {
  padding: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
}
```

---

## 适用场景

此设计风格适用于：

- **仪表盘**：数据监控、分析面板、管理后台
- **工具应用**：代码编辑器、文件管理、系统设置
- **内容平台**：文档阅读、笔记应用、知识库
- **协作工具**：项目管理、任务追踪、团队协作
- **创意工具**：设计软件、视频编辑、音乐制作
- **企业应用**：CRM、ERP、项目管理系统

## 设计原则

1. **克制**：装饰服务于功能，不喧宾夺主
2. **层次**：通过透明度、阴影、间距建立清晰的视觉层次
3. **一致**：保持组件样式、间距、动效的全局统一
4. **可及**：高对比度、焦点样式、减少动画偏好支持
5. **精致**：注重细节，微交互提升品质感