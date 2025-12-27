<template>
  <div class="courses">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>课程管理</span>
          <el-button 
            v-permission="'course:create'"
            type="primary" 
            :icon="Plus" 
            @click="handleCreate"
          >
            添加课程
          </el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="课程名称">
          <el-input v-model="searchForm.name" placeholder="请输入课程名称" clearable />
        </el-form-item>
        <el-form-item label="教师">
          <el-input v-model="searchForm.teacher" placeholder="请输入教师姓名" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="课程名称" />
        <el-table-column prop="code" label="课程代码" width="120" />
        <el-table-column prop="teacher" label="授课教师" />
        <el-table-column prop="semester" label="学期" width="120" />
        <el-table-column prop="studentCount" label="学生人数" width="100" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text :icon="View" @click="handleView(row)">
              查看
            </el-button>
            <el-button 
              v-permission="'course:edit'"
              type="warning" 
              text 
              :icon="Edit" 
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button 
              v-permission="'course:delete'"
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
        <el-form-item label="课程名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入课程名称" />
        </el-form-item>
        <el-form-item label="课程代码" prop="code">
          <el-input v-model="form.code" placeholder="请输入课程代码" />
        </el-form-item>
        <el-form-item label="授课教师" prop="teacher">
          <el-input v-model="form.teacher" placeholder="请输入授课教师" />
        </el-form-item>
        <el-form-item label="学期" prop="semester">
          <el-input v-model="form.semester" placeholder="如：2024-2025学年第一学期" />
        </el-form-item>
        <el-form-item label="学生人数" prop="studentCount">
          <el-input-number v-model="form.studentCount" :min="1" :max="200" />
        </el-form-item>
        <el-form-item label="课程描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入课程描述"
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
    <el-dialog v-model="detailVisible" title="课程详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="课程ID">{{ currentRow.id }}</el-descriptions-item>
        <el-descriptions-item label="课程名称">{{ currentRow.name }}</el-descriptions-item>
        <el-descriptions-item label="课程代码">{{ currentRow.code }}</el-descriptions-item>
        <el-descriptions-item label="授课教师">{{ currentRow.teacher }}</el-descriptions-item>
        <el-descriptions-item label="学期">{{ currentRow.semester }}</el-descriptions-item>
        <el-descriptions-item label="学生人数">{{ currentRow.studentCount }}</el-descriptions-item>
        <el-descriptions-item label="课程描述" :span="2">
          {{ currentRow.description }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, View, Edit, Delete } from '@element-plus/icons-vue'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const dialogTitle = ref('添加课程')
const formRef = ref(null)
const currentRow = ref({})

const searchForm = reactive({
  name: '',
  teacher: ''
})

const pagination = reactive({
  page: 1,
  size: 10,
  total: 30
})

const tableData = ref([
  {
    id: 1,
    name: 'Java程序设计',
    code: 'CS101',
    teacher: '张教授',
    semester: '2024-2025学年第一学期',
    studentCount: 45,
    description: '面向对象程序设计基础课程'
  },
  {
    id: 2,
    name: '数据结构与算法',
    code: 'CS102',
    teacher: '李教授',
    semester: '2024-2025学年第一学期',
    studentCount: 50,
    description: '计算机专业核心课程'
  },
  {
    id: 3,
    name: '大学物理实验',
    code: 'PHY201',
    teacher: '王老师',
    semester: '2024-2025学年第一学期',
    studentCount: 40,
    description: '物理实验基础课程'
  }
])

const form = reactive({
  name: '',
  code: '',
  teacher: '',
  semester: '',
  studentCount: 30,
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入课程代码', trigger: 'blur' }],
  teacher: [{ required: true, message: '请输入授课教师', trigger: 'blur' }],
  semester: [{ required: true, message: '请输入学期', trigger: 'blur' }],
  studentCount: [{ required: true, message: '请输入学生人数', trigger: 'blur' }]
}

const handleSearch = () => {
  loading.value = true
  setTimeout(() => {
    loading.value = false
  }, 500)
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.teacher = ''
  handleSearch()
}

const handleCreate = () => {
  dialogTitle.value = '添加课程'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑课程'
  currentRow.value = row
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleView = (row) => {
  currentRow.value = row
  detailVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm('确定要删除此课程吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('删除成功')
    handleSearch()
  }).catch(() => {})
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        await new Promise(resolve => setTimeout(resolve, 1000))
        ElMessage.success(dialogTitle.value === '添加课程' ? '添加成功' : '更新成功')
        dialogVisible.value = false
        handleSearch()
      } catch (error) {
        console.error(error)
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

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>

