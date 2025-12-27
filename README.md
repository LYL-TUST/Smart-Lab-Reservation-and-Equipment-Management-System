# 🎓 智能实验室预约与设备管理系统

一个功能完善、界面精美的实验室预约与设备管理系统，支持实验室预约、设备管理、课程管理等功能。

## 📸 项目预览

### 登录页面
- 现代化渐变背景设计
- 支持登录和注册
- 动画效果流畅

### 仪表盘
- 数据统计卡片
- ECharts 图表展示
- 最近预约和系统公告

### 功能页面
- 预约管理（支持单次/多次/课程预约）
- 实验室管理（卡片式展示）
- 设备管理（含维护记录）
- 课程管理
- 用户管理（管理员）
- 个人中心

## 🚀 快速开始

### 前置要求

- Node.js 16+ 
- npm 或 yarn
- Java 17+
- MySQL 8.0+

### 安装步骤

#### 1. 安装前端依赖

```bash
cd frontend
npm install
```

需要手动安装以下依赖：
```bash
npm install axios vue-router pinia @element-plus/icons-vue echarts vue-echarts
```

#### 2. 配置后端数据库

在 MySQL 中创建数据库：
```sql
CREATE DATABASE lab_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改 `backend/src/main/resources/application.yml` 中的数据库配置：
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/lab_management
    username: your_username
    password: your_password
```

#### 3. 启动后端服务

```bash
cd backend
mvn spring-boot:run
```

后端服务将在 `http://localhost:8080` 启动

#### 4. 启动前端服务

```bash
cd frontend
npm run dev
```

前端服务将在 `http://localhost:5173` 启动

## 🏗️ 项目结构

```
智能实验室预约与设备管理系统/
├── backend/                    # 后端项目（Spring Boot）
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/
│   │   │   │   └── com/lab/management/
│   │   │   │       ├── common/         # 公共类
│   │   │   │       ├── config/         # 配置类
│   │   │   │       ├── controller/     # 控制器
│   │   │   │       ├── dto/            # 数据传输对象
│   │   │   │       ├── entity/         # 实体类
│   │   │   │       ├── enums/          # 枚举类
│   │   │   │       ├── mapper/         # MyBatis Mapper
│   │   │   │       ├── security/       # 安全配置
│   │   │   │       ├── service/        # 服务层
│   │   │   │       └── util/           # 工具类
│   │   │   └── resources/
│   │   │       ├── application.yml     # 配置文件
│   │   │       └── schema.sql          # 数据库脚本
│   │   └── test/                       # 测试代码
│   └── pom.xml
│
└── frontend/                   # 前端项目（Vue 3）
    ├── src/
    │   ├── api/               # API 接口
    │   ├── assets/            # 静态资源
    │   ├── components/        # 公共组件
    │   ├── layouts/           # 布局组件
    │   ├── router/            # 路由配置
    │   ├── stores/            # 状态管理
    │   ├── views/             # 页面组件
    │   ├── App.vue
    │   ├── main.js
    │   └── style.css
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## ✨ 核心功能

### 1. 用户管理
- ✅ 用户注册/登录
- ✅ 角色管理（管理员/教师/学生）
- ✅ 权限控制
- ✅ 个人信息管理

### 2. 实验室管理
- ✅ 实验室信息维护
- ✅ 状态管理（空闲/使用中/维护中）
- ✅ 容量管理
- ✅ 设备统计

### 3. 设备管理
- ✅ 设备信息维护
- ✅ 状态管理（正常/使用中/维护中/损坏）
- ✅ 维护记录管理
- ✅ 设备分配

### 4. 预约管理
- ✅ 单次预约
- ✅ 多次预约
- ✅ 课程绑定预约
- ✅ 冲突检测
- ✅ 预约审核
- ✅ 预约取消

### 5. 课程管理
- ✅ 课程信息维护
- ✅ 学生管理
- ✅ 课程预约关联

### 6. 数据统计
- ✅ 预约趋势分析
- ✅ 实验室使用率
- ✅ 设备使用统计
- ✅ 用户活跃度

## 🎨 技术亮点

### 前端技术
- **Vue 3** - 最新的 Composition API
- **Element Plus** - 企业级 UI 组件库
- **Pinia** - 新一代状态管理
- **Vue Router** - 官方路由管理
- **Axios** - HTTP 请求库
- **ECharts** - 数据可视化
- **Vite** - 极速构建工具

### 后端技术
- **Spring Boot** - 快速开发框架
- **Spring Security** - 安全框架
- **JWT** - 身份认证
- **MyBatis Plus** - ORM 框架
- **MySQL** - 关系型数据库
- **Maven** - 项目管理工具

### 设计特色
- 🎨 现代化 UI 设计
- 🌓 暗黑模式支持
- 📱 响应式布局
- 💫 流畅动画效果
- 🎯 直观的用户体验

## 🔐 安全特性

- JWT Token 认证
- 密码加密存储
- 角色权限控制
- 请求拦截验证
- XSS 防护
- CSRF 防护

## 📊 数据库设计

### 核心表结构

- **users** - 用户表
- **laboratories** - 实验室表
- **equipment** - 设备表
- **courses** - 课程表
- **reservations** - 预约表
- **equipment_reservations** - 设备预约关联表
- **maintenance_records** - 维护记录表
- **system_logs** - 系统日志表

## 🎯 业务流程

### 预约流程
1. 用户选择实验室和时间
2. 系统检测时间冲突
3. 提交预约申请
4. 管理员审核
5. 预约确认/拒绝
6. 预约使用/取消

### 冲突检测算法
- 时间段重叠检测
- 实验室容量检测
- 设备可用性检测
- 课程时间冲突检测

## 📱 界面展示

### 主要特色
1. **登录页** - 渐变背景 + 玻璃态效果
2. **仪表盘** - 数据卡片 + 图表展示
3. **预约管理** - 表格 + 对话框
4. **实验室管理** - 卡片式布局
5. **设备管理** - 维护记录时间线
6. **个人中心** - 信息展示 + 编辑

## 🔧 配置说明

### 前端配置
- API 地址：`src/api/request.js`
- 路由配置：`src/router/index.js`
- 主题配置：`src/style.css`

### 后端配置
- 数据库：`application.yml`
- JWT 密钥：`application.yml`
- 端口配置：`application.yml`

## 📝 开发计划

- [x] 基础框架搭建
- [x] 用户认证系统
- [x] 实验室管理
- [x] 设备管理
- [x] 预约管理
- [x] 课程管理
- [x] 数据统计
- [ ] 日历视图
- [ ] 消息通知
- [ ] 数据导出
- [ ] 移动端优化

## 🐛 已知问题

暂无

## 📄 许可证

MIT License

## 👨‍💻 开发者

课程设计项目

## 🙏 致谢

感谢以下开源项目：
- Vue.js
- Element Plus
- Spring Boot
- MyBatis Plus
- ECharts

---

**如有问题，欢迎提 Issue！** 🎉

