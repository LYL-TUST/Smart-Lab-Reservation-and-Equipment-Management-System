<template>
  <div class="reservations">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>预约管理</span>
          <el-button 
            v-permission="'reservation:create'"
            type="primary" 
            :icon="Plus" 
            @click="handleCreate"
          >
            新建预约
          </el-button>
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

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="laboratoryName" label="实验室" />
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
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束时间" prop="endTime">
          <el-date-picker
            v-model="form.endTime"
            type="datetime"
            placeholder="选择结束时间"
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, View, Edit, Delete, Check } from '@element-plus/icons-vue'
import { getReservations, createReservation, updateReservation, deleteReservation } from '../api/reservation'
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

const handleSearch = async () => {
  loading.value = true
  try {
    const params = {
      current: pagination.page,
      size: pagination.size,
      laboratoryName: searchForm.laboratoryName || undefined,
      status: searchForm.status || undefined,
      startDate: searchForm.date?.[0] || undefined,
      endDate: searchForm.date?.[1] || undefined
    }
    const response = await getReservations(params)
    if (response.data) {
      tableData.value = response.data.records || response.data.list || response.data
      pagination.total = response.data.total || tableData.value.length
    }
  } catch (error) {
    console.error('获取预约列表失败:', error)
    ElMessage.error('获取预约列表失败')
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
    laboratoryId: row.laboratoryId,
    type: row.type,
    startTime: row.startTime,
    endTime: row.endTime,
    purpose: row.purpose,
    participantCount: row.participantCount
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

const handleApprove = (row) => {
  ElMessageBox.confirm('确定要审批此预约吗？', '审批预约', {
    confirmButtonText: '通过',
    cancelButtonText: '拒绝',
    distinguishCancelAndClose: true,
    type: 'info'
  }).then(() => {
    // 通过审批
    ElMessage.success('审批通过')
    row.status = 'APPROVED'
    handleSearch()
  }).catch((action) => {
    if (action === 'cancel') {
      // 拒绝审批
      ElMessage.info('已拒绝')
      row.status = 'REJECTED'
      handleSearch()
    }
  })
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        const submitData = {
          laboratoryId: form.laboratoryId,
          type: form.type,
          startTime: form.startTime,
          endTime: form.endTime,
          purpose: form.purpose,
          participantCount: form.participantCount
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
      } catch (error) {
        console.error('提交失败:', error)
        ElMessage.error(error.message || '操作失败')
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
</style>

