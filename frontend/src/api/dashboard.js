import request from './request'

export const getDashboardStats = () => {
    return request({
        url: '/dashboard/stats',
        method: 'get'
    })
}

