import request from './request'

export const getCourses = (params) => {
    return request({
        url: '/course/page',
        method: 'get',
        params
    })
}

export const createCourse = (data) => {
    return request({
        url: '/course',
        method: 'post',
        data
    })
}

export const updateCourse = (id, data) => {
    return request({
        url: `/course/${id}`,
        method: 'put',
        data
    })
}

export const deleteCourse = (id) => {
    return request({
        url: `/course/${id}`,
        method: 'delete'
    })
}

