# 智能实验室预约与设备管理系统 - 后端

## 项目简介
这是一个基于Spring Boot的智能实验室预约与设备管理系统后端服务，支持复杂规则校验的资源预约与管理。

## 技术栈
- **框架**: Spring Boot 2.7.18
- **数据库**: MySQL 8.0
- **ORM**: MyBatis-Plus 3.5.3.1
- **安全**: Spring Security + JWT
- **构建工具**: Maven
- **Java版本**: JDK 1.8

## 核心功能

### 1. 用户管理
- 三种角色：管理员、教师、学生
- JWT无状态认证
- 基于角色的访问控制（RBAC）

### 2. 实验室管理
- 实验室CRUD操作
- 状态机管理（空闲、已预约、使用中、维护中）
- 容量和设施管理

### 3. 设备管理
- 设备CRUD操作
- 设备状态管理
- 设备与实验室关联

### 4. 预约管理（核心功能）
- **单次预约**: 预约单个时间段
- **多次预约**: 批量预约多个时间段
- **课程绑定预约**: 教师为课程预约整学期实验室
- **冲突检测算法**: 多维度检测预约冲突
- 预约审批流程
- 签到签退功能

### 5. 课程管理
- 课程CRUD操作
- 课程与实验室绑定
- 学期管理

### 6. 冲突检测算法
智能检测以下维度的冲突：
- ✅ 时间冲突（区间重叠算法）
- ✅ 资源状态（维护中不可预约）
- ✅ 容量限制
- ✅ 维护期间冲突
- ✅ 时间有效性验证

## 项目结构
```
backend/
├── src/
│   ├── main/
│   │   ├── java/com/lab/management/
│   │   │   ├── common/          # 通用类（Result、PageResult）
│   │   │   ├── config/          # 配置类（Security、MyBatis-Plus、JWT）
│   │   │   ├── controller/      # 控制器层
│   │   │   ├── dto/             # 数据传输对象
│   │   │   ├── entity/          # 实体类
│   │   │   ├── enums/           # 枚举类
│   │   │   ├── mapper/          # MyBatis Mapper
│   │   │   ├── security/        # 安全相关类
│   │   │   ├── service/         # 业务逻辑层
│   │   │   └── util/            # 工具类
│   │   └── resources/
│   │       ├── application.yml  # 配置文件
│   │       └── schema.sql       # 数据库脚本
│   └── test/                    # 单元测试
└── pom.xml                      # Maven配置
```

## 快速开始

### 1. 环境要求
- JDK 1.8+
- Maven 3.6+
- MySQL 8.0+

### 2. 数据库配置
```bash
# 创建数据库
mysql -u root -p < src/main/resources/schema.sql
```

### 3. 修改配置
编辑 `src/main/resources/application.yml`，修改数据库连接信息：
```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/lab_management
    username: root
    password: your_password
```

### 4. 运行项目
```bash
# 编译
mvn clean package

# 运行
mvn spring-boot:run
```

访问: http://localhost:8080/api

### 5. 测试账号
```
管理员: admin / admin123
教师: teacher1 / teacher123
学生: student1 / student123
```

## API文档

### 认证接口
- `POST /auth/login` - 用户登录
- `POST /auth/register` - 用户注册

### 实验室接口
- `GET /laboratory/page` - 分页查询实验室
- `GET /laboratory/{id}` - 查询实验室详情
- `POST /laboratory` - 创建实验室（管理员）
- `PUT /laboratory/{id}` - 更新实验室（管理员）
- `DELETE /laboratory/{id}` - 删除实验室（管理员）
- `PUT /laboratory/{id}/status` - 更新状态（管理员）

### 设备接口
- `GET /equipment/page` - 分页查询设备
- `GET /equipment/{id}` - 查询设备详情
- `POST /equipment` - 创建设备（管理员）
- `PUT /equipment/{id}` - 更新设备（管理员）
- `DELETE /equipment/{id}` - 删除设备（管理员）

### 预约接口
- `GET /reservation/page` - 分页查询预约
- `GET /reservation/{id}` - 查询预约详情
- `POST /reservation/single` - 创建单次预约
- `POST /reservation/multiple` - 创建多次预约
- `POST /reservation/course` - 创建课程预约（教师）
- `PUT /reservation/{id}/approve` - 审批预约（管理员）
- `PUT /reservation/{id}/cancel` - 取消预约
- `PUT /reservation/{id}/checkin` - 签到
- `PUT /reservation/{id}/checkout` - 签退
- `GET /reservation/my` - 我的预约

### 课程接口
- `GET /course/page` - 分页查询课程
- `GET /course/{id}` - 查询课程详情
- `POST /course` - 创建课程（教师）
- `PUT /course/{id}` - 更新课程（教师）
- `DELETE /course/{id}` - 删除课程（管理员）
- `GET /course/my` - 我的课程（教师）

## 核心算法说明

### 时间冲突检测算法
```
两个时间区间 [start1, end1] 和 [start2, end2] 重叠的条件：
start1 < end2 AND start2 < end1

SQL实现：
SELECT * FROM reservation 
WHERE lab_id = ? 
  AND status IN ('PENDING', 'APPROVED')
  AND (
    (start_time <= ? AND end_time > ?) OR
    (start_time < ? AND end_time >= ?) OR
    (start_time >= ? AND end_time <= ?)
  )
```

### 状态机模型
```
实验室状态转换：
IDLE → RESERVED → IN_USE → IDLE
  ↓                           ↑
MAINTENANCE ←-----------------┘

设备状态转换：
IDLE → RESERVED → IN_USE → IDLE
  ↓                           ↑
MAINTENANCE ←-----------------┘
  ↓
SCRAPPED (终态)
```

## 测试

### 运行单元测试
```bash
mvn test
```

### 测试覆盖
- ✅ 冲突检测算法（15个测试用例）
- ✅ 边界情况测试
- ✅ 状态机转换测试

## 项目亮点

1. **智能冲突检测**: 多维度的预约冲突检测算法，覆盖时间、状态、容量等
2. **状态机模型**: 规范的资源状态管理，防止非法状态转换
3. **灵活的预约方式**: 支持单次、多次、课程绑定三种预约模式
4. **完善的权限控制**: 基于Spring Security的RBAC权限管理
5. **高测试覆盖率**: 核心算法有完整的单元测试

## 开发规范

- 使用Lombok简化代码
- 统一的Result响应格式
- 完善的日志记录
- 事务管理
- 异常处理

## 作者
Lab Management Team

## 许可证
MIT License

