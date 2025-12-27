/**
 * 权限配置文件
 * 定义不同角色的权限和功能访问控制
 */

// 角色定义
export const ROLES = {
    ADMIN: 'ADMIN',      // 管理员
    TEACHER: 'TEACHER',  // 教师
    STUDENT: 'STUDENT'   // 学生
}

// 权限定义
export const PERMISSIONS = {
    // 仪表盘
    DASHBOARD_VIEW: 'dashboard:view',

    // 预约管理
    RESERVATION_VIEW: 'reservation:view',      // 查看预约
    RESERVATION_CREATE: 'reservation:create',  // 创建预约
    RESERVATION_EDIT: 'reservation:edit',      // 编辑自己的预约
    RESERVATION_DELETE: 'reservation:delete',  // 删除自己的预约
    RESERVATION_APPROVE: 'reservation:approve', // 审批预约
    RESERVATION_MANAGE: 'reservation:manage',  // 管理所有预约

    // 实验室管理
    LAB_VIEW: 'lab:view',          // 查看实验室
    LAB_CREATE: 'lab:create',      // 创建实验室
    LAB_EDIT: 'lab:edit',          // 编辑实验室
    LAB_DELETE: 'lab:delete',      // 删除实验室
    LAB_MANAGE: 'lab:manage',      // 管理实验室

    // 设备管理
    EQUIPMENT_VIEW: 'equipment:view',          // 查看设备
    EQUIPMENT_CREATE: 'equipment:create',      // 创建设备
    EQUIPMENT_EDIT: 'equipment:edit',          // 编辑设备
    EQUIPMENT_DELETE: 'equipment:delete',      // 删除设备
    EQUIPMENT_MAINTAIN: 'equipment:maintain',  // 设备维护

    // 课程管理
    COURSE_VIEW: 'course:view',        // 查看课程
    COURSE_CREATE: 'course:create',    // 创建课程
    COURSE_EDIT: 'course:edit',        // 编辑课程
    COURSE_DELETE: 'course:delete',    // 删除课程

    // 用户管理
    USER_VIEW: 'user:view',        // 查看用户
    USER_CREATE: 'user:create',    // 创建用户
    USER_EDIT: 'user:edit',        // 编辑用户
    USER_DELETE: 'user:delete',    // 删除用户
    USER_MANAGE: 'user:manage',    // 管理用户

    // 个人中心
    PROFILE_VIEW: 'profile:view',
    PROFILE_EDIT: 'profile:edit'
}

// 角色权限映射
export const ROLE_PERMISSIONS = {
    // 管理员：拥有所有权限
    [ROLES.ADMIN]: [
        PERMISSIONS.DASHBOARD_VIEW,

        PERMISSIONS.RESERVATION_VIEW,
        PERMISSIONS.RESERVATION_CREATE,
        PERMISSIONS.RESERVATION_EDIT,
        PERMISSIONS.RESERVATION_DELETE,
        PERMISSIONS.RESERVATION_APPROVE,
        PERMISSIONS.RESERVATION_MANAGE,

        PERMISSIONS.LAB_VIEW,
        PERMISSIONS.LAB_CREATE,
        PERMISSIONS.LAB_EDIT,
        PERMISSIONS.LAB_DELETE,
        PERMISSIONS.LAB_MANAGE,

        PERMISSIONS.EQUIPMENT_VIEW,
        PERMISSIONS.EQUIPMENT_CREATE,
        PERMISSIONS.EQUIPMENT_EDIT,
        PERMISSIONS.EQUIPMENT_DELETE,
        PERMISSIONS.EQUIPMENT_MAINTAIN,

        PERMISSIONS.COURSE_VIEW,
        PERMISSIONS.COURSE_CREATE,
        PERMISSIONS.COURSE_EDIT,
        PERMISSIONS.COURSE_DELETE,

        PERMISSIONS.USER_VIEW,
        PERMISSIONS.USER_CREATE,
        PERMISSIONS.USER_EDIT,
        PERMISSIONS.USER_DELETE,
        PERMISSIONS.USER_MANAGE,

        PERMISSIONS.PROFILE_VIEW,
        PERMISSIONS.PROFILE_EDIT
    ],

    // 教师：可以管理实验室、设备、课程，审批预约
    [ROLES.TEACHER]: [
        PERMISSIONS.DASHBOARD_VIEW,

        PERMISSIONS.RESERVATION_VIEW,
        PERMISSIONS.RESERVATION_CREATE,
        PERMISSIONS.RESERVATION_EDIT,
        PERMISSIONS.RESERVATION_DELETE,
        PERMISSIONS.RESERVATION_APPROVE,  // 教师可以审批预约

        PERMISSIONS.LAB_VIEW,
        PERMISSIONS.LAB_EDIT,  // 教师可以编辑实验室信息

        PERMISSIONS.EQUIPMENT_VIEW,
        PERMISSIONS.EQUIPMENT_EDIT,
        PERMISSIONS.EQUIPMENT_MAINTAIN,  // 教师可以维护设备

        PERMISSIONS.COURSE_VIEW,
        PERMISSIONS.COURSE_CREATE,  // 教师可以创建课程
        PERMISSIONS.COURSE_EDIT,
        PERMISSIONS.COURSE_DELETE,

        PERMISSIONS.PROFILE_VIEW,
        PERMISSIONS.PROFILE_EDIT
    ],

    // 学生：只能查看和预约，管理自己的预约
    [ROLES.STUDENT]: [
        PERMISSIONS.DASHBOARD_VIEW,

        PERMISSIONS.RESERVATION_VIEW,
        PERMISSIONS.RESERVATION_CREATE,  // 学生可以创建预约
        PERMISSIONS.RESERVATION_EDIT,    // 学生只能编辑自己的预约
        PERMISSIONS.RESERVATION_DELETE,  // 学生只能删除自己的预约

        PERMISSIONS.LAB_VIEW,            // 学生只能查看实验室

        PERMISSIONS.EQUIPMENT_VIEW,      // 学生只能查看设备

        PERMISSIONS.COURSE_VIEW,         // 学生只能查看课程

        PERMISSIONS.PROFILE_VIEW,
        PERMISSIONS.PROFILE_EDIT
    ]
}

// 路由权限配置
export const ROUTE_PERMISSIONS = {
    '/dashboard': [PERMISSIONS.DASHBOARD_VIEW],
    '/reservations': [PERMISSIONS.RESERVATION_VIEW],
    '/laboratories': [PERMISSIONS.LAB_VIEW],
    '/equipment': [PERMISSIONS.EQUIPMENT_VIEW],
    '/courses': [PERMISSIONS.COURSE_VIEW],
    '/users': [PERMISSIONS.USER_MANAGE],  // 只有管理员可以访问
    '/profile': [PERMISSIONS.PROFILE_VIEW]
}

/**
 * 检查用户是否有指定权限
 * @param {string} userRole - 用户角色
 * @param {string} permission - 权限标识
 * @returns {boolean}
 */
export function hasPermission(userRole, permission) {
    if (!userRole || !permission) return false
    const permissions = ROLE_PERMISSIONS[userRole] || []
    return permissions.includes(permission)
}

/**
 * 检查用户是否有任一权限
 * @param {string} userRole - 用户角色
 * @param {string[]} permissions - 权限标识数组
 * @returns {boolean}
 */
export function hasAnyPermission(userRole, permissions) {
    if (!userRole || !permissions || permissions.length === 0) return false
    return permissions.some(permission => hasPermission(userRole, permission))
}

/**
 * 检查用户是否有所有权限
 * @param {string} userRole - 用户角色
 * @param {string[]} permissions - 权限标识数组
 * @returns {boolean}
 */
export function hasAllPermissions(userRole, permissions) {
    if (!userRole || !permissions || permissions.length === 0) return false
    return permissions.every(permission => hasPermission(userRole, permission))
}

/**
 * 获取用户所有权限
 * @param {string} userRole - 用户角色
 * @returns {string[]}
 */
export function getUserPermissions(userRole) {
    return ROLE_PERMISSIONS[userRole] || []
}

