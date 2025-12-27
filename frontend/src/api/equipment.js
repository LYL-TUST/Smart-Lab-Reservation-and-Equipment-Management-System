import request from './request'

export const getEquipment = (params) => {
    return request({
        url: '/equipment/page',
        method: 'get',
        params
    })
}

export const createEquipment = (data) => {
    return request({
        url: '/equipment',
        method: 'post',
        data
    })
}

export const updateEquipment = (id, data) => {
    return request({
        url: `/equipment/${id}`,
        method: 'put',
        data
    })
}

export const deleteEquipment = (id) => {
    return request({
        url: `/equipment/${id}`,
        method: 'delete'
    })
}

