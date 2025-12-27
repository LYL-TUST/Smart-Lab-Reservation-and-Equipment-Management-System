import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user'
import router from '../router'

const request = axios.create({
    baseURL: 'http://localhost:8080/api',
    timeout: 10000
})

// 请求拦截器
request.interceptors.request.use(
    config => {
        const userStore = useUserStore()
        if (userStore.token) {
            config.headers.Authorization = `Bearer ${userStore.token}`
        }
        return config
    },
    error => {
        return Promise.reject(error)
    }
)

// 响应拦截器
request.interceptors.response.use(
    response => {
        const res = response.data

        if (res.code !== 200) {
            ElMessage.error(res.message || '请求失败')
            return Promise.reject(new Error(res.message || '请求失败'))
        }

        return res
    },
    error => {
        if (error.response) {
            switch (error.response.status) {
                case 401:
                    ElMessage.error('未授权，请重新登录')
                    const userStore = useUserStore()
                    userStore.logout()
                    router.push('/login')
                    break
                case 403:
                    ElMessage.error('拒绝访问')
                    break
                case 404:
                    ElMessage.error('请求地址不存在')
                    break
                case 500:
                    ElMessage.error('服务器错误')
                    break
                case 400:
                    // 400错误可能是验证失败，显示详细错误信息
                    const errorData = error.response.data
                    if (errorData && errorData.message) {
                        ElMessage.error(errorData.message)
                    } else if (errorData && errorData.error) {
                        ElMessage.error(errorData.error)
                    } else {
                        ElMessage.error('请求参数错误，请检查输入的数据')
                    }
                    break
                default:
                    ElMessage.error(error.response.data?.message || error.response.data?.error || '请求失败')
            }
        } else {
            ElMessage.error('网络错误，请检查网络连接')
        }
        return Promise.reject(error)
    }
)

export default request

