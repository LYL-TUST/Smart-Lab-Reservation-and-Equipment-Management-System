import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import { PERMISSIONS, ROLES, hasAnyPermission } from '../config/permissions'

const routes = [
    {
        path: '/login',
        name: 'Login',
        component: () => import('../views/Login.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/',
        component: () => import('../layouts/MainLayout.vue'),
        redirect: '/dashboard',
        meta: { requiresAuth: true },
        children: [
            {
                path: 'dashboard',
                name: 'Dashboard',
                component: () => import('../views/Dashboard.vue'),
                meta: { 
                    title: '仪表盘', 
                    icon: 'DataAnalysis',
                    permissions: [PERMISSIONS.DASHBOARD_VIEW]
                }
            },
            {
                path: 'reservations',
                name: 'Reservations',
                component: () => import('../views/Reservations.vue'),
                meta: { 
                    title: '预约管理', 
                    icon: 'Calendar',
                    permissions: [PERMISSIONS.RESERVATION_VIEW]
                }
            },
            {
                path: 'laboratories',
                name: 'Laboratories',
                component: () => import('../views/Laboratories.vue'),
                meta: { 
                    title: '实验室管理', 
                    icon: 'OfficeBuilding',
                    permissions: [PERMISSIONS.LAB_VIEW]
                }
            },
            {
                path: 'equipment',
                name: 'Equipment',
                component: () => import('../views/Equipment.vue'),
                meta: { 
                    title: '设备管理', 
                    icon: 'Monitor',
                    permissions: [PERMISSIONS.EQUIPMENT_VIEW]
                }
            },
            {
                path: 'courses',
                name: 'Courses',
                component: () => import('../views/Courses.vue'),
                meta: { 
                    title: '课程管理', 
                    icon: 'Reading',
                    permissions: [PERMISSIONS.COURSE_VIEW]
                }
            },
            {
                path: 'users',
                name: 'Users',
                component: () => import('../views/Users.vue'),
                meta: { 
                    title: '用户管理', 
                    icon: 'User',
                    roles: [ROLES.ADMIN],  // 只有管理员可以访问
                    permissions: [PERMISSIONS.USER_MANAGE]
                }
            },
            {
                path: 'profile',
                name: 'Profile',
                component: () => import('../views/Profile.vue'),
                meta: { 
                    title: '个人中心', 
                    icon: 'UserFilled',
                    hidden: true,  // 不在菜单中显示
                    permissions: [PERMISSIONS.PROFILE_VIEW]
                }
            }
        ]
    },
    {
        path: '/403',
        name: 'Forbidden',
        component: () => import('../views/403.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('../views/404.vue'),
        meta: { requiresAuth: false }
    }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

/**
 * 检查用户是否有访问路由的权限
 */
function hasRoutePermission(userRole, route) {
    // 如果路由指定了角色限制
    if (route.meta?.roles && route.meta.roles.length > 0) {
        return route.meta.roles.includes(userRole)
    }
    
    // 如果路由指定了权限要求
    if (route.meta?.permissions && route.meta.permissions.length > 0) {
        return hasAnyPermission(userRole, route.meta.permissions)
    }
    
    // 默认允许访问
    return true
}

// 路由守卫
router.beforeEach((to, from, next) => {
    const userStore = useUserStore()

    // 不需要认证的页面
    if (to.meta.requiresAuth === false) {
        // 如果已登录，访问登录页则跳转到首页
        if (to.path === '/login' && userStore.token) {
            next('/')
        } else {
            next()
        }
        return
    }

    // 需要认证的页面
    if (!userStore.token) {
        ElMessage.warning('请先登录')
        next('/login')
        return
    }

    // 检查权限
    const userRole = userStore.userInfo?.role
    if (!hasRoutePermission(userRole, to)) {
        ElMessage.error('您没有权限访问该页面')
        next('/403')
        return
    }

    next()
})

export default router

