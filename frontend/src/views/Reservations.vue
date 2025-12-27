<template>
  <div class="reservations">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>预约管理</span>
          <div class="header-actions">
            <el-radio-group v-model="viewMode" size="small" style="margin-right: 10px;">
              <el-radio-button value="list">列表视图</el-radio-button>
              <el-radio-button value="calendar">日历视图</el-radio-button>
            </el-radio-group>
            <el-button 
              v-permission="'reservation:create'"
              type="primary" 
              :icon="Plus" 
              @click="handleCreate"
            >
              新建预约
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="实验室">
          <el-input v-model="searchForm.laboratoryName" placeholder="请输入实验室名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="待审核" value="PENDING" />
            <el-option label="已通过" value="APPROVED" />
            <el-option label="已拒绝" value="REJECTED" />
            <el-option label="已取消" value="CANCELLED" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="searchForm.date"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 列表视图 -->
      <div v-if="viewMode === 'list'">
        <!-- 表格 -->
        <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="实验室">
          <template #default="{ row }">
            {{ row.laboratoryName || '未知' }}
          </template>
        </el-table-column>
        <el-table-column prop="startTime" label="开始时间" width="180" />
        <el-table-column prop="endTime" label="结束时间" width="180" />
        <el-table-column prop="purpose" label="预约目的" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text :icon="View" @click="handleView(row)">
              查看
            </el-button>
            <el-button
              v-if="row.status === 'PENDING'"
              v-permission="'reservation:edit'"
              type="warning"
              text
              :icon="Edit"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="(row.status === 'PENDING' || row.status === 'APPROVED') && canCancelReservation(row)"
              v-permission="'reservation:delete'"
              type="danger"
              text
              :icon="Delete"
              @click="handleCancel(row)"
            >
              取消
            </el-button>
            <el-button
              v-if="row.status === 'PENDING'"
              v-permission="'reservation:approve'"
              type="success"
              text
              :icon="Check"
              @click="handleApprove(row)"
            >
              审批
            </el-button>
          </template>
        </el-table-column>
      </el-table>

        <!-- 分页 -->
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSearch"
          @current-change="handleSearch"
          class="pagination"
        />
      </div>

      <!-- 日历视图 -->
      <div v-if="viewMode === 'calendar'" class="calendar-container">
        <div class="calendar-filters">
          <el-form :inline="true" :model="calendarFilters" class="calendar-search-form">
            <el-form-item label="实验室">
              <el-select v-model="calendarFilters.labId" placeholder="全部实验室" clearable style="width: 200px" @change="loadCalendarEvents">
                <el-option
                  v-for="lab in laboratories"
                  :key="lab.id"
                  :label="lab.name"
                  :value="lab.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="calendarFilters.status" placeholder="全部状态" clearable style="width: 150px" @change="loadCalendarEvents">
                <el-option label="待审核" value="PENDING" />
                <el-option label="已通过" value="APPROVED" />
                <el-option label="已完成" value="COMPLETED" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
        <div class="calendar-wrapper" v-loading="calendarLoading">
          <FullCalendar :options="calendarOptions" />
        </div>
      </div>
    </el-card>

    <!-- 新建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="实验室" prop="laboratoryId">
          <el-select v-model="form.laboratoryId" placeholder="请选择实验室" style="width: 100%">
            <el-option
              v-for="lab in laboratories"
              :key="lab.id"
              :label="lab.name"
              :value="lab.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="预约类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="SINGLE">单次预约</el-radio>
            <el-radio value="RECURRING">多次预约</el-radio>
            <el-radio value="COURSE">课程预约</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始时间" prop="startTime">
          <el-date-picker
            v-model="form.startTime"
            type="datetime"
            placeholder="选择开始时间"
            :disabled-date="disabledStartDate"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间" prop="endTime">
          <el-date-picker
            v-model="form.endTime"
            type="datetime"
            placeholder="选择结束时间"
            :disabled-date="disabledEndDate"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="预约目的" prop="purpose">
          <el-input
            v-model="form.purpose"
            type="textarea"
            :rows="3"
            placeholder="请输入预约目的"
          />
        </el-form-item>
        <el-form-item label="参与人数" prop="participantCount">
          <el-input-number v-model="form.participantCount" :min="1" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="预约详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="预约ID">{{ currentRow.id }}</el-descriptions-item>
        <el-descriptions-item label="实验室">{{ currentRow.laboratoryName }}</el-descriptions-item>
        <el-descriptions-item label="预约类型">{{ getTypeText(currentRow.type) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRow.status)">
            {{ getStatusText(currentRow.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="开始时间">{{ currentRow.startTime }}</el-descriptions-item>
        <el-descriptions-item label="结束时间">{{ currentRow.endTime }}</el-descriptions-item>
        <el-descriptions-item label="参与人数">{{ currentRow.participantCount }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ currentRow.createdAt }}</el-descriptions-item>
        <el-descriptions-item label="预约目的" :span="2">
          {{ currentRow.purpose }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, View, Edit, Delete, Check } from '@element-plus/icons-vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import zhCnLocale from '@fullcalendar/core/locales/zh-cn'
import { getReservations, createReservation, updateReservation, deleteReservation, approveReservation, getReservationCalendar } from '../api/reservation'
import { getLaboratories } from '../api/laboratory'
import { useUserStore } from '../stores/user'
import { hasPermission, ROLES } from '../config/permissions'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const dialogTitle = ref('新建预约')
const formRef = ref(null)
const currentRow = ref({})
const userStore = useUserStore()
const viewMode = ref('list') // 'list' 或 'calendar'
const calendarLoading = ref(false)
const calendarEvents = ref([])

// 计算当前用户角色
const userRole = computed(() => userStore.userInfo?.role)
const currentUserId = computed(() => userStore.userInfo?.id)

// 判断是否可以取消预约（学生只能取消自己的预约，管理员和教师可以取消所有预约）
const canCancelReservation = (row) => {
  const role = userRole.value
  if (role === ROLES.ADMIN || role === ROLES.TEACHER) {
    return true // 管理员和教师可以取消所有预约
  }
  // 学生只能取消自己的预约
  return row.userId === currentUserId.value
}

const searchForm = reactive({
  laboratoryName: '',
  status: '',
  date: []
})

const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

const tableData = ref([])

const laboratories = ref([])

const calendarFilters = reactive({
  labId: null,
  status: null
})

// FullCalendar 配置
const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, timeGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay'
  },
  locale: zhCnLocale,
  height: 'auto',
  events: calendarEvents.value,
  eventClick: handleCalendarEventClick,
  datesSet: handleCalendarDatesSet,
  eventDisplay: 'block',
  eventTimeFormat: {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  },
  slotMinTime: '06:00:00',
  slotMaxTime: '24:00:00',
  allDaySlot: false,
  weekends: true,
  editable: false,
  selectable: false,
  dayMaxEvents: true,
  moreLinkClick: 'popover'
}))

const form = reactive({
  laboratoryId: null,
  type: 'SINGLE',
  startTime: '',
  endTime: '',
  purpose: '',
  participantCount: 1
})

const rules = {
  laboratoryId: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  type: [{ required: true, message: '请选择预约类型', trigger: 'change' }],
  startTime: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  endTime: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  purpose: [{ required: true, message: '请输入预约目的', trigger: 'blur' }],
  participantCount: [{ required: true, message: '请输入参与人数', trigger: 'blur' }]
}

const getStatusType = (status) => {
  const typeMap = {
    'PENDING': 'warning',
    'APPROVED': 'success',
    'REJECTED': 'danger',
    'CANCELLED': 'info'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'PENDING': '待审核',
    'APPROVED': '已通过',
    'REJECTED': '已拒绝',
    'CANCELLED': '已取消'
  }
  return textMap[status] || status
}

const getTypeText = (type) => {
  const textMap = {
    'SINGLE': '单次预约',
    'RECURRING': '多次预约',
    'COURSE': '课程预约'
  }
  return textMap[type] || type
}

// 禁用过去的日期（开始时间）
const disabledStartDate = (time) => {
  return time.getTime() < Date.now() - 24 * 60 * 60 * 1000 // 禁用今天之前的日期
}

// 禁用过去的日期（结束时间）
const disabledEndDate = (time) => {
  if (form.startTime) {
    // 结束时间不能早于开始时间
    return time.getTime() < new Date(form.startTime).getTime()
  }
  return time.getTime() < Date.now() - 24 * 60 * 60 * 1000
}

const handleSearch = async () => {
  loading.value = true
  try {
    const params = {
      current: pagination.page,
      size: pagination.size,
      laboratoryName: searchForm.laboratoryName || undefined,
      status: searchForm.status || undefined
    }
    
    // 处理日期范围
    if (searchForm.date && searchForm.date.length === 2) {
      // 格式化日期为字符串
      const startDate = new Date(searchForm.date[0])
      const endDate = new Date(searchForm.date[1])
      params.startDate = startDate.toISOString().split('T')[0]
      params.endDate = endDate.toISOString().split('T')[0]
    }
    
    const response = await getReservations(params)
    console.log('预约数据响应:', response)
    if (response && response.data) {
      const pageData = response.data
      if (pageData.records && pageData.records.length > 0) {
        tableData.value = pageData.records
        pagination.total = pageData.total || 0
      } else if (Array.isArray(pageData)) {
        tableData.value = pageData
        pagination.total = pageData.length
      } else {
        tableData.value = []
        pagination.total = 0
      }
    } else {
      tableData.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('获取预约列表失败:', error)
    ElMessage.error('获取预约列表失败: ' + (error.message || '未知错误'))
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.laboratoryName = ''
  searchForm.status = ''
  searchForm.date = []
  handleSearch()
}

const handleCreate = () => {
  dialogTitle.value = '新建预约'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑预约'
  currentRow.value = row
  Object.assign(form, {
    laboratoryId: row.labId || row.laboratoryId,
    type: row.type,
    startTime: row.startTime ? new Date(row.startTime) : '',
    endTime: row.endTime ? new Date(row.endTime) : '',
    purpose: row.purpose,
    participantCount: row.participantCount || 1
  })
  dialogVisible.value = true
}

const handleView = (row) => {
  currentRow.value = row
  detailVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要取消此预约吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteReservation(row.id)
    ElMessage.success('取消成功')
    await handleSearch()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('取消预约失败:', error)
      ElMessage.error('取消预约失败')
    }
  }
}

const handleCancel = (row) => {
  handleDelete(row)
}

const handleApprove = async (row) => {
  try {
    const result = await ElMessageBox.confirm('确定要审批此预约吗？', '审批预约', {
      confirmButtonText: '通过',
      cancelButtonText: '拒绝',
      distinguishCancelAndClose: true,
      type: 'info'
    })
    
    // 通过审批
    await approveReservation(row.id, true, '')
    ElMessage.success('审批通过')
    await handleSearch()
  } catch (action) {
    if (action === 'cancel') {
      // 拒绝审批
      try {
        await approveReservation(row.id, false, '')
        ElMessage.info('已拒绝')
        await handleSearch()
      } catch (error) {
        console.error('拒绝审批失败:', error)
        ElMessage.error('拒绝审批失败')
      }
    }
  }
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        // 格式化日期时间为后端期望的格式 (yyyy-MM-dd HH:mm:ss)
        const formatDateTime = (date) => {
          if (!date) return null
          
          let dateObj
          if (typeof date === 'string') {
            // 如果是字符串，转换为Date对象
            dateObj = new Date(date)
            if (isNaN(dateObj.getTime())) {
              // 如果无法解析，尝试直接返回（可能是已格式化的字符串）
              return date
            }
          } else if (date instanceof Date) {
            dateObj = date
          } else {
            return date
          }
          
          // 格式化为 yyyy-MM-dd HH:mm:ss
          const year = dateObj.getFullYear()
          const month = String(dateObj.getMonth() + 1).padStart(2, '0')
          const day = String(dateObj.getDate()).padStart(2, '0')
          const hours = String(dateObj.getHours()).padStart(2, '0')
          const minutes = String(dateObj.getMinutes()).padStart(2, '0')
          const seconds = String(dateObj.getSeconds()).padStart(2, '0')
          return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
        }
        
        // 验证日期
        if (!form.startTime || !form.endTime) {
          ElMessage.error('请选择开始时间和结束时间')
          submitting.value = false
          return
        }
        
        const startTime = formatDateTime(form.startTime)
        const endTime = formatDateTime(form.endTime)
        
        // 验证时间逻辑
        if (new Date(form.startTime) >= new Date(form.endTime)) {
          ElMessage.error('结束时间必须晚于开始时间')
          submitting.value = false
          return
        }
        
        const submitData = {
          labId: form.laboratoryId,  // 后端期望的是labId，不是laboratoryId
          type: form.type || 'SINGLE',
          startTime: startTime,
          endTime: endTime,
          purpose: form.purpose,
          participantCount: form.participantCount || 1
        }
        
        console.log('提交预约数据:', JSON.stringify(submitData, null, 2))
        
        // 验证必填字段
        if (!submitData.labId) {
          ElMessage.error('请选择实验室')
          submitting.value = false
          return
        }
        if (!submitData.startTime || !submitData.endTime) {
          ElMessage.error('请选择开始时间和结束时间')
          submitting.value = false
          return
        }
        if (!submitData.purpose || submitData.purpose.trim() === '') {
          ElMessage.error('请输入预约目的')
          submitting.value = false
          return
        }
        
        if (dialogTitle.value === '新建预约') {
          await createReservation(submitData)
          ElMessage.success('创建成功')
        } else {
          await updateReservation(currentRow.value.id, submitData)
          ElMessage.success('更新成功')
        }
        
        dialogVisible.value = false
        // 重新加载列表数据
        await handleSearch()
        // 如果当前是日历视图，也重新加载日历数据
        if (viewMode.value === 'calendar') {
          loadCalendarEvents()
        }
      } catch (error) {
        console.error('提交失败:', error)
        console.error('错误详情:', {
          status: error.response?.status,
          statusText: error.response?.statusText,
          data: error.response?.data,
          message: error.message
        })
        // 打印完整的响应数据以便调试
        if (error.response?.data) {
          console.error('响应数据:', JSON.stringify(error.response.data, null, 2))
        }
        
        let errorMessage = '操作失败'
        if (error.response) {
          // 有响应但状态码不是2xx
          const responseData = error.response.data
          if (responseData) {
            // 优先使用message字段（我们的Result类格式）
            if (responseData.message) {
              errorMessage = responseData.message
            } 
            // 检查其他可能的错误字段
            else if (responseData.error) {
              errorMessage = responseData.error
            } 
            // 如果是字符串
            else if (typeof responseData === 'string') {
              errorMessage = responseData
            }
            // 如果是数组（验证错误可能是数组格式）
            else if (Array.isArray(responseData)) {
              errorMessage = responseData.join('; ')
            }
            // 尝试获取所有字段的错误
            else {
              const errorParts = []
              for (const key in responseData) {
                if (responseData.hasOwnProperty(key)) {
                  errorParts.push(`${key}: ${responseData[key]}`)
                }
              }
              if (errorParts.length > 0) {
                errorMessage = errorParts.join('; ')
              }
            }
          } else {
            errorMessage = `请求失败: ${error.response.status} ${error.response.statusText}`
          }
        } else if (error.request) {
          // 请求已发出但没有收到响应
          errorMessage = '网络错误，请检查后端服务是否运行'
        } else {
          // 请求配置出错
          errorMessage = error.message || '请求配置错误'
        }
        
        ElMessage.error(errorMessage)
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
  currentRow.value = {}
}

// 加载日历事件
const loadCalendarEvents = async (start, end) => {
  calendarLoading.value = true
  try {
    const params = {}
    
    // 如果提供了日期范围，使用提供的；否则使用当前视图的日期范围
    if (start && end) {
      params.start = start.split('T')[0]
      params.end = end.split('T')[0]
    }
    
    if (calendarFilters.labId) {
      params.labId = calendarFilters.labId
    }
    
    if (calendarFilters.status) {
      params.status = calendarFilters.status
    }
    
    const response = await getReservationCalendar(params)
    
    if (response && response.data) {
      // 转换数据格式为 FullCalendar 需要的格式
      calendarEvents.value = response.data.map(event => ({
        id: event.id.toString(),
        title: event.title || `${event.laboratoryName || '未知实验室'} - ${event.purpose || '预约'}`,
        start: event.start,
        end: event.end,
        backgroundColor: event.backgroundColor || event.color,
        borderColor: event.borderColor || event.color,
        textColor: event.textColor || '#000',
        extendedProps: {
          labId: event.labId,
          laboratoryName: event.laboratoryName,
          status: event.status,
          type: event.type,
          purpose: event.purpose,
          reservationId: event.id
        }
      }))
    } else {
      calendarEvents.value = []
    }
  } catch (error) {
    console.error('加载日历事件失败:', error)
    ElMessage.error('加载日历事件失败: ' + (error.message || '未知错误'))
    calendarEvents.value = []
  } finally {
    calendarLoading.value = false
  }
}

// 日历日期范围变化
const handleCalendarDatesSet = (info) => {
  const start = info.start.toISOString().split('T')[0]
  const end = info.end.toISOString().split('T')[0]
  loadCalendarEvents(start, end)
}

// 日历事件点击
const handleCalendarEventClick = (info) => {
  const event = info.event
  const extendedProps = event.extendedProps
  
  // 查找对应的预约数据
  const reservation = {
    id: extendedProps.reservationId,
    laboratoryName: extendedProps.laboratoryName,
    startTime: event.start.toISOString(),
    endTime: event.end ? event.end.toISOString() : '',
    status: extendedProps.status,
    type: extendedProps.type,
    purpose: extendedProps.purpose
  }
  
  handleView(reservation)
}

// 监听视图模式变化
watch(viewMode, (newMode) => {
  if (newMode === 'calendar') {
    // 切换到日历视图时，加载日历数据
    loadCalendarEvents()
  }
})

onMounted(async () => {
  // 加载实验室列表
  try {
    const response = await getLaboratories({ current: 1, size: 100 })
    if (response.data) {
      laboratories.value = response.data.records || response.data.list || response.data
    }
  } catch (error) {
    console.error('获取实验室列表失败:', error)
  }
  
  // 加载预约列表
  await handleSearch()
  
  // 如果默认是日历视图，加载日历数据
  if (viewMode.value === 'calendar') {
    loadCalendarEvents()
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.search-form {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.header-actions {
  display: flex;
  align-items: center;
}

.calendar-container {
  margin-top: 20px;
}

.calendar-filters {
  margin-bottom: 20px;
}

.calendar-search-form {
  margin-bottom: 0;
}

.calendar-wrapper {
  min-height: 600px;
}

/* FullCalendar 样式调整 */
:deep(.fc) {
  font-family: inherit;
}

:deep(.fc-event) {
  cursor: pointer;
  border-radius: 4px;
}

:deep(.fc-event:hover) {
  opacity: 0.8;
}

:deep(.fc-daygrid-event) {
  white-space: normal;
  word-wrap: break-word;
}

:deep(.fc-timegrid-event) {
  border-radius: 4px;
}
</style>

