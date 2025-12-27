import request from './request'

export const getReservations = (params) => {
    return request({
        url: '/reservation/page',
        method: 'get',
        params
    })
}

export const createReservation = (data) => {
    return request({
        url: '/reservation/single',
        method: 'post',
        data
    })
}

export const updateReservation = (id, data) => {
    return request({
        url: `/reservation/${id}`,
        method: 'put',
        data
    })
}

export const deleteReservation = (id) => {
    return request({
        url: `/reservation/${id}/cancel`,
        method: 'put'
    })
}

export const checkConflict = (data) => {
    return request({
        url: '/reservation/check-conflict',
        method: 'post',
        data
    })
}

export const getReservationCalendar = (params) => {
    return request({
        url: '/reservation/calendar',
        method: 'get',
        params
    })
}

