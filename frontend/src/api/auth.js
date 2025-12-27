import request from './request'

export const login = (data) => {
    return request({
        url: '/auth/login',
        method: 'post',
        data
    })
}

export const register = (data) => {
    return request({
        url: '/auth/register',
        method: 'post',
        data
    })
}

export const getCurrentUser = () => {
    return request({
        url: '/auth/current',
        method: 'get'
    })
}

