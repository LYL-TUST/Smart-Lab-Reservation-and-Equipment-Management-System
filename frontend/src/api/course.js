import request from './request'

export const getCourses = (params) => {
    return request({
        url: '/courses',
        method: 'get',
        params
    })
}

export const createCourse = (data) => {
    return request({
        url: '/courses',
        method: 'post',
        data
    })
}

export const updateCourse = (id, data) => {
    return request({
        url: `/courses/${id}`,
        method: 'put',
        data
    })
}

export const deleteCourse = (id) => {
    return request({
        url: `/courses/${id}`,
        method: 'delete'
    })
}

