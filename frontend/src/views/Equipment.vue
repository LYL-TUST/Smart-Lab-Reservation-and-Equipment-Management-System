<template>
  <div class="equipment">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <el-button 
            v-permission="'equipment:create'"
            type="primary" 
            :icon="Plus" 
            @click="handleCreate"
          >
            添加设备
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="设备名称">
          <el-input v-model="searchForm.name" placeholder="请输入设备名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
            <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="空闲" value="IDLE" />
            <el-option label="已预约" value="RESERVED" />
            <el-option label="使用中" value="IN_USE" />
            <el-option label="维护中" value="MAINTENANCE" />
            <el-option label="报废" value="SCRAPPED" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="设备名称" />
        <el-table-column prop="model" label="型号" />
        <el-table-column prop="laboratoryName" label="所属实验室" />
        <el-table-column prop="purchaseDate" label="购买日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text :icon="View" @click="handleView(row)">
              查看
            </el-button>
            <el-button 
              v-permission="'equipment:edit'"
              type="warning" 
              text 
              :icon="Edit" 
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button 
              v-permission="'equipment:maintain'"
              type="info" 
              text 
              :icon="Tools" 
              @click="handleMaintenance(row)"
            >
              维护
            </el-button>
            <el-button 
              v-permission="'equipment:delete'"
              type="danger" 
              text 
              :icon="Delete" 
              @click="handleDelete(row)"
            >
              删除
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
        <el-form-item label="设备名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="型号" prop="model">
          <el-input v-model="form.model" placeholder="请输入型号" />
        </el-form-item>
        <el-form-item label="所属实验室" prop="laboratoryId">
          <el-select v-model="form.laboratoryId" placeholder="请选择实验室" style="width: 100%">
            <el-option
              v-for="lab in laboratories"
              :key="lab.id"
              :label="lab.name"
              :value="lab.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="购买日期" prop="purchaseDate">
          <el-date-picker
            v-model="form.purchaseDate"
            type="date"
            placeholder="选择购买日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="空闲" value="IDLE" />
            <el-option label="已预约" value="RESERVED" />
            <el-option label="使用中" value="IN_USE" />
            <el-option label="维护中" value="MAINTENANCE" />
            <el-option label="报废" value="SCRAPPED" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 维护记录对话框 -->
    <el-dialog v-model="maintenanceVisible" title="维护记录" width="700px">
      <el-button 
        v-permission="'equipment:maintain'"
        type="primary" 
        :icon="Plus" 
        @click="handleAddMaintenance" 
        style="margin-bottom: 15px"
      >
        添加维护记录
      </el-button>
      <el-timeline>
        <el-timeline-item
          v-for="record in maintenanceRecords"
          :key="record.id"
          :timestamp="record.date"
          placement="top"
        >
          <el-card>
            <h4>{{ record.type }}</h4>
            <p>{{ record.description }}</p>
            <p style="color: var(--text-secondary); font-size: 12px;">
              维护人员: {{ record.technician }}
            </p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="设备详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="设备ID">{{ currentRow.id }}</el-descriptions-item>
        <el-descriptions-item label="设备名称">{{ currentRow.name }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ currentRow.model }}</el-descriptions-item>
        <el-descriptions-item label="所属实验室">{{ currentRow.laboratoryName }}</el-descriptions-item>
        <el-descriptions-item label="购买日期">{{ currentRow.purchaseDate }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRow.status)">
            {{ getStatusText(currentRow.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          {{ currentRow.description }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, View, Edit, Delete, Tools } from '@element-plus/icons-vue'
import { getEquipment, createEquipment, updateEquipment, deleteEquipment } from '../api/equipment'
import { getLaboratories } from '../api/laboratory'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const maintenanceVisible = ref(false)
const dialogTitle = ref('添加设备')
const formRef = ref(null)
const currentRow = ref({})

const searchForm = reactive({
  name: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  size: 10,
  total: 50
})

const tableData = ref([])

const laboratories = ref([])

const maintenanceRecords = ref([
  {
    id: 1,
    type: '定期保养',
    description: '清洁设备，检查各部件运行状况',
    date: '2024-12-01 10:00',
    technician: '张工程师'
  },
  {
    id: 2,
    type: '故障维修',
    description: '更换损坏的电源模块',
    date: '2024-11-15 14:30',
    technician: '李技师'
  }
])

const form = reactive({
  name: '',
  model: '',
  laboratoryId: null,
  purchaseDate: '',
  status: 'IDLE',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  model: [{ required: true, message: '请输入型号', trigger: 'blur' }],
  laboratoryId: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  purchaseDate: [{ required: true, message: '请选择购买日期', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const getStatusType = (status) => {
  const typeMap = {
    'IDLE': 'success',
    'RESERVED': 'info',
    'IN_USE': 'warning',
    'MAINTENANCE': 'info',
    'SCRAPPED': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'IDLE': '空闲',
    'RESERVED': '已预约',
    'IN_USE': '使用中',
    'MAINTENANCE': '维护中',
    'SCRAPPED': '报废'
  }
  return textMap[status] || status
}

const handleSearch = async () => {
  loading.value = true
  try {
    const params = {
      current: pagination.page,
      size: pagination.size,
      name: searchForm.name || undefined,
      status: searchForm.status || undefined
    }
    const response = await getEquipment(params)
    console.log('设备数据:', response)
    if (response && response.data) {
      const pageData = response.data
      // 使用后端返回的数据
      tableData.value = pageData.records || []
      pagination.total = pageData.total || 0
    } else {
      tableData.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('获取设备列表失败:', error)
    ElMessage.error('获取设备列表失败')
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.status = ''
  pagination.page = 1
  handleSearch()
}

const handleCreate = () => {
  dialogTitle.value = '添加设备'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑设备'
  currentRow.value = row
  Object.assign(form, {
    name: row.name,
    model: row.model,
    laboratoryId: row.labId || row.laboratoryId,  // 后端返回的是labId
    purchaseDate: row.purchaseDate,
    status: row.status,
    description: row.description
  })
  dialogVisible.value = true
}

const handleView = (row) => {
  currentRow.value = row
  detailVisible.value = true
}

const handleMaintenance = (row) => {
  currentRow.value = row
  maintenanceVisible.value = true
}

const handleAddMaintenance = () => {
  ElMessage.info('添加维护记录功能开发中...')
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此设备吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteEquipment(row.id)
    ElMessage.success('删除成功')
    await handleSearch()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除设备失败:', error)
      ElMessage.error('删除设备失败')
    }
  }
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        const submitData = {
          name: form.name,
          model: form.model,
          labId: form.laboratoryId,  // 后端期望的是labId
          purchaseDate: form.purchaseDate,
          status: form.status,
          description: form.description
        }
        
        if (dialogTitle.value === '添加设备') {
          await createEquipment(submitData)
          ElMessage.success('添加成功')
        } else {
          await updateEquipment(currentRow.value.id, submitData)
          ElMessage.success('更新成功')
        }
        
        dialogVisible.value = false
        await handleSearch()
      } catch (error) {
        console.error('提交失败:', error)
        console.error('错误详情:', error.response?.data)
        // 显示后端返回的具体错误信息
        const errorMessage = error.response?.data?.message || error.response?.data?.error || error.message || '操作失败'
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
  
  // 加载设备列表
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

