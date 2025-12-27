import request from './request'

export const getLaboratories = (params) => {
    return request({
        url: '/laboratory/page',
        method: 'get',
        params
    })
}

export const createLaboratory = (data) => {
    return request({
        url: '/laboratory',
        method: 'post',
        data
    })
}

export const updateLaboratory = (id, data) => {
    return request({
        url: `/laboratory/${id}`,
        method: 'put',
        data
    })
}

export const deleteLaboratory = (id) => {
    return request({
        url: `/laboratory/${id}`,
        method: 'delete'
    })
}

