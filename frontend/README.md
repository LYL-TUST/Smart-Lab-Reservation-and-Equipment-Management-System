# 智能实验室预约与设备管理系统 - 前端

一个现代化、智能化的实验室预约与设备管理系统前端项目，基于 Vue 3 + Element Plus 构建。

## ✨ 特性

- 🎨 **现代化UI设计** - 采用 Element Plus 组件库，界面美观大方
- 🌓 **暗黑模式** - 支持亮色/暗色主题切换
- 📱 **响应式布局** - 完美适配桌面端和移动端
- 📊 **数据可视化** - 使用 ECharts 展示统计数据
- 🔐 **权限管理** - 基于角色的访问控制（RBAC）
- 🚀 **性能优化** - 路由懒加载、组件按需引入
- 💫 **动画效果** - 流畅的页面切换和交互动画

## 🛠️ 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **UI组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP客户端**: Axios
- **图表库**: ECharts
- **图标**: Element Plus Icons

## 📦 安装依赖

```bash
cd frontend
npm install
```

需要安装的依赖包括：
```bash
npm install axios vue-router pinia @element-plus/icons-vue echarts vue-echarts
```

## 🚀 运行项目

### 开发环境

```bash
npm run dev
```

项目将在 `http://localhost:5173` 启动

### 生产构建

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 📁 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── api/            # API 接口
│   │   ├── auth.js
│   │   ├── course.js
│   │   ├── equipment.js
│   │   ├── laboratory.js
│   │   ├── request.js
│   │   └── reservation.js
│   ├── assets/         # 资源文件
│   ├── components/     # 公共组件
│   ├── layouts/        # 布局组件
│   │   └── MainLayout.vue
│   ├── router/         # 路由配置
│   │   └── index.js
│   ├── stores/         # 状态管理
│   │   ├── app.js
│   │   └── user.js
│   ├── views/          # 页面组件
│   │   ├── Dashboard.vue      # 仪表盘
│   │   ├── Reservations.vue   # 预约管理
│   │   ├── Laboratories.vue   # 实验室管理
│   │   ├── Equipment.vue      # 设备管理
│   │   ├── Courses.vue        # 课程管理
│   │   ├── Users.vue          # 用户管理
│   │   ├── Profile.vue        # 个人中心
│   │   └── Login.vue          # 登录页
│   ├── App.vue         # 根组件
│   ├── main.js         # 入口文件
│   └── style.css       # 全局样式
├── index.html
├── package.json
└── vite.config.js
```

## 🎯 功能模块

### 1. 登录注册
- ✅ 用户登录
- ✅ 用户注册
- ✅ 角色选择（学生/教师）
- ✅ 表单验证

### 2. 仪表盘
- ✅ 数据统计卡片
- ✅ 预约趋势图表
- ✅ 实验室使用率饼图
- ✅ 最近预约列表
- ✅ 系统公告

### 3. 预约管理
- ✅ 预约列表查询
- ✅ 新建预约（单次/多次/课程）
- ✅ 编辑预约
- ✅ 取消预约
- ✅ 预约详情查看
- ✅ 状态筛选

### 4. 实验室管理
- ✅ 实验室卡片展示
- ✅ 添加/编辑实验室
- ✅ 实验室状态管理
- ✅ 实验室详情查看
- ✅ 图片展示

### 5. 设备管理
- ✅ 设备列表管理
- ✅ 添加/编辑设备
- ✅ 设备状态管理
- ✅ 维护记录管理
- ✅ 设备详情查看

### 6. 课程管理
- ✅ 课程列表管理
- ✅ 添加/编辑课程
- ✅ 课程详情查看
- ✅ 学生人数统计

### 7. 用户管理（管理员）
- ✅ 用户列表管理
- ✅ 添加/编辑用户
- ✅ 角色分配
- ✅ 用户详情查看

### 8. 个人中心
- ✅ 个人信息展示
- ✅ 信息修改
- ✅ 密码修改
- ✅ 头像上传
- ✅ 统计数据

## 🎨 界面特色

### 1. 渐变背景
- 登录页采用紫色渐变背景
- 统计卡片使用多彩渐变
- 欢迎卡片渐变效果

### 2. 动画效果
- 页面切换淡入淡出
- 卡片悬浮效果
- 加载动画
- 背景浮动动画

### 3. 响应式设计
- 移动端适配
- 侧边栏折叠
- 表格自适应
- 卡片网格布局

### 4. 暗黑模式
- 一键切换主题
- 自动保存偏好
- 全局样式适配

## 🔧 配置说明

### API 基础地址

在 `src/api/request.js` 中配置：

```javascript
const request = axios.create({
  baseURL: 'http://localhost:8080/api',
  timeout: 10000
})
```

### 路由配置

在 `src/router/index.js` 中配置路由和权限：

```javascript
{
  path: '/users',
  name: 'Users',
  component: () => import('../views/Users.vue'),
  meta: { title: '用户管理', icon: 'User', roles: ['ADMIN'] }
}
```

## 🎭 默认账号

开发环境可使用以下测试账号：

- **管理员**: admin / 123456
- **教师**: teacher / 123456
- **学生**: student / 123456

## 📝 开发规范

### 代码风格
- 使用 Composition API
- 组件采用 `<script setup>` 语法
- 使用 reactive 和 ref 管理状态
- 遵循 Vue 3 最佳实践

### 命名规范
- 组件名：PascalCase
- 文件名：PascalCase.vue
- 变量名：camelCase
- 常量名：UPPER_CASE

### 提交规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- style: 代码格式调整
- refactor: 重构
- test: 测试相关
- chore: 构建/工具相关

## 🐛 常见问题

### 1. 依赖安装失败
```bash
# 清除缓存重新安装
rm -rf node_modules package-lock.json
npm install
```

### 2. 端口被占用
修改 `vite.config.js`：
```javascript
export default defineConfig({
  server: {
    port: 3000 // 修改为其他端口
  }
})
```

### 3. API 请求失败
- 检查后端服务是否启动
- 检查 API 基础地址配置
- 查看浏览器控制台错误信息

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 联系方式

如有问题，请联系开发团队。

---

**享受编码！** 🎉
