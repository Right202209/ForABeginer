# 代码可视化演示网站

这是一个用于C和Python代码可视化的Web应用，允许用户输入代码并生成对应的代码逻辑和内存状态的动态可视化模型。

## 功能特点

- 支持C和Python代码输入和分析
- 代码执行逻辑的可视化展示
- 内存状态的动态可视化（变量、数组、指针等）
- 代码执行的逐步演示功能
- 交互式用户界面

## 技术栈

- 前端：React、D3.js、CodeMirror
- 后端：Flask、Python解释器、C编译器

## 项目结构

```
├── frontend/            # React前端应用
├── backend/             # Flask后端服务
├── requirements.txt     # Python依赖
└── README.md           # 项目说明
```

## 安装与运行

### 前提条件

- Node.js 14+
- Python 3.8+
- C编译器（如GCC）

### 安装步骤

1. 克隆仓库
2. 安装后端依赖：`pip install -r requirements.txt`
3. 安装前端依赖：`cd frontend && npm install`
4. 启动后端服务：`python backend/app.py`
5. 启动前端服务：`cd frontend && npm start`

## 使用方法

1. 在代码编辑器中输入C或Python代码
2. 选择代码语言（C或Python）
3. 点击"运行"按钮执行代码
4. 使用控制面板逐步执行代码
5. 观察代码执行逻辑和内存状态的可视化展示