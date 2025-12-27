<template>
  <div class="laboratories">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>实验室管理</span>
          <el-button 
            v-permission="'lab:create'"
            type="primary" 
            :icon="Plus" 
            @click="handleCreate"
          >
            添加实验室
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="实验室名称">
          <el-input v-model="searchForm.name" placeholder="请输入实验室名称" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="空闲" value="IDLE" />
            <el-option label="已预约" value="RESERVED" />
            <el-option label="使用中" value="IN_USE" />
            <el-option label="维护中" value="MAINTENANCE" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 卡片视图 -->
      <el-row :gutter="20">
        <el-col
          v-for="lab in tableData"
          :key="lab.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <el-card class="lab-card hover-card" shadow="hover">
            <div class="lab-image">
              <el-image :src="lab.image" fit="cover">
                <template #error>
                  <div class="image-slot">
                    <el-icon :size="50"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <el-tag :type="getStatusType(lab.status)" class="status-tag">
                {{ getStatusText(lab.status) }}
              </el-tag>
            </div>
            <div class="lab-info">
              <h3>{{ lab.name }}</h3>
              <p class="lab-location">
                <el-icon><Location /></el-icon>
                {{ lab.location }}
              </p>
              <div class="lab-stats">
                <div class="stat-item">
                  <el-icon><User /></el-icon>
                  <span>容量: {{ lab.capacity }}人</span>
                </div>
                <div class="stat-item">
                  <el-icon><Monitor /></el-icon>
                  <span>设备: {{ lab.equipmentCount }}台</span>
                </div>
              </div>
              <div class="lab-actions">
                <el-button type="primary" text :icon="View" @click="handleView(lab)">
                  查看
                </el-button>
                <el-button 
                  v-permission="'lab:edit'"
                  type="warning" 
                  text 
                  :icon="Edit" 
                  @click="handleEdit(lab)"
                >
                  编辑
                </el-button>
                <el-button 
                  v-permission="'lab:delete'"
                  type="danger" 
                  text 
                  :icon="Delete" 
                  @click="handleDelete(lab)"
                >
                  删除
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[8, 16, 24, 32]"
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
        <el-form-item label="实验室名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入实验室名称" />
        </el-form-item>
        <el-form-item label="位置" prop="location">
          <el-input v-model="form.location" placeholder="请输入位置" />
        </el-form-item>
        <el-form-item label="容量" prop="capacity">
          <el-input-number v-model="form.capacity" :min="1" :max="200" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="空闲" value="IDLE" />
            <el-option label="已预约" value="RESERVED" />
            <el-option label="使用中" value="IN_USE" />
            <el-option label="维护中" value="MAINTENANCE" />
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

    <!-- 查看详情对话框 -->
    <el-dialog v-model="detailVisible" title="实验室详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="实验室ID">{{ currentRow.id }}</el-descriptions-item>
        <el-descriptions-item label="名称">{{ currentRow.name }}</el-descriptions-item>
        <el-descriptions-item label="位置">{{ currentRow.location }}</el-descriptions-item>
        <el-descriptions-item label="容量">{{ currentRow.capacity }}人</el-descriptions-item>
        <el-descriptions-item label="设备数量">{{ currentRow.equipmentCount }}台</el-descriptions-item>
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
import { Plus, Search, Refresh, View, Edit, Delete, Picture, Location, User, Monitor } from '@element-plus/icons-vue'
import { getLaboratories, createLaboratory, updateLaboratory, deleteLaboratory } from '../api/laboratory'
import defaultLabImage from '../assets/img/实验室.jpg'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const dialogTitle = ref('添加实验室')
const formRef = ref(null)
const currentRow = ref({})

const searchForm = reactive({
  name: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  size: 8,
  total: 12
})

const tableData = ref([
  {
    id: 1,
    name: '计算机实验室A',
    location: '教学楼3楼301',
    capacity: 50,
    equipmentCount: 50,
    status: 'IDLE',
    description: '配备高性能计算机，适合编程实验',
    image: defaultLabImage
  },
  {
    id: 2,
    name: '物理实验室B',
    location: '实验楼2楼201',
    capacity: 40,
    equipmentCount: 30,
    status: 'IN_USE',
    description: '配备各类物理实验设备',
    image: defaultLabImage
  },
  {
    id: 3,
    name: '化学实验室C',
    location: '实验楼3楼302',
    capacity: 35,
    equipmentCount: 25,
    status: 'MAINTENANCE',
    description: '配备化学实验器材和通风设备',
    image: defaultLabImage
  }
])

const form = reactive({
  name: '',
  location: '',
  capacity: 30,
  status: 'IDLE',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入位置', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容量', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }]
}

const getStatusType = (status) => {
  const typeMap = {
    'IDLE': 'success',
    'RESERVED': 'info',
    'IN_USE': 'warning',
    'MAINTENANCE': 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    'IDLE': '空闲',
    'RESERVED': '已预约',
    'IN_USE': '使用中',
    'MAINTENANCE': '维护中'
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
    const response = await getLaboratories(params)
    console.log('实验室数据:', response)
    if (response && response.data) {
      const pageData = response.data
      // 如果后端有数据就用后端的
      if (pageData.records && pageData.records.length > 0) {
        tableData.value = pageData.records.map(lab => ({
          ...lab,
          equipmentCount: lab.equipmentCount || 0, // 使用后端返回的设备数量
          image: (lab.imageUrl && lab.imageUrl.trim()) ? lab.imageUrl : defaultLabImage
        }))
        pagination.total = pageData.total || 0
      } else {
        // 如果后端没数据，清空表格
        tableData.value = []
        pagination.total = 0
      }
    } else {
      tableData.value = []
      pagination.total = 0
    }
  } catch (error) {
    console.error('获取实验室列表失败:', error)
    // 出错时也保留静态数据，不清空
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
  dialogTitle.value = '添加实验室'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑实验室'
  currentRow.value = row
  Object.assign(form, {
    name: row.name,
    location: row.location,
    capacity: row.capacity,
    status: row.status,
    description: row.description
  })
  dialogVisible.value = true
}

const handleView = (row) => {
  currentRow.value = row
  detailVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此实验室吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteLaboratory(row.id)
    ElMessage.success('删除成功')
    await handleSearch()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除实验室失败:', error)
      ElMessage.error('删除实验室失败')
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
          location: form.location,
          capacity: form.capacity,
          status: form.status,
          description: form.description
        }
        
        if (dialogTitle.value === '添加实验室') {
          await createLaboratory(submitData)
          ElMessage.success('添加成功')
        } else {
          await updateLaboratory(currentRow.value.id, submitData)
          ElMessage.success('更新成功')
        }
        
        dialogVisible.value = false
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

onMounted(() => {
  handleSearch()
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

.lab-card {
  margin-bottom: 20px;
  overflow: hidden;
}

.lab-image {
  position: relative;
  height: 180px;
  overflow: hidden;
}

.lab-image :deep(.el-image) {
  width: 100%;
  height: 100%;
}

.image-slot {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
  background: var(--bg-color);
  color: var(--text-secondary);
}

.status-tag {
  position: absolute;
  top: 10px;
  right: 10px;
}

.lab-info {
  padding: 15px 0;
}

.lab-info h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
  color: var(--text-primary);
}

.lab-location {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 15px;
}

.lab-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  color: var(--text-regular);
}

.lab-actions {
  display: flex;
  justify-content: space-around;
  padding-top: 15px;
  border-top: 1px solid var(--border-color);
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

