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
        <el-table-column label="授课教师">
          <template #default="{ row }">
            {{ teachers.find(t => t.id === row.teacherId)?.name || row.teacherId || '未知' }}
          </template>
        </el-table-column>
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
        <el-form-item label="授课教师" prop="teacherId">
          <el-select v-model="form.teacherId" placeholder="请选择授课教师" style="width: 100%">
            <el-option
              v-for="teacher in teachers"
              :key="teacher.id"
              :label="teacher.name"
              :value="teacher.id"
            />
          </el-select>
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
        <el-descriptions-item label="授课教师">
          {{ teachers.find(t => t.id === currentRow.teacherId)?.name || currentRow.teacherId || '未知' }}
        </el-descriptions-item>
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
import { getCourses, createCourse, updateCourse, deleteCourse } from '../api/course'
import { getUsers } from '../api/user'

const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const detailVisible = ref(false)
const dialogTitle = ref('添加课程')
const formRef = ref(null)
const currentRow = ref({})
const teachers = ref([])

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
  teacherId: null,
  semester: '',
  studentCount: 30,
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入课程代码', trigger: 'blur' }],
  teacherId: [{ required: true, message: '请选择授课教师', trigger: 'change' }],
  semester: [{ required: true, message: '请输入学期', trigger: 'blur' }],
  studentCount: [{ required: true, message: '请输入学生人数', trigger: 'blur' }]
}

const handleSearch = async () => {
  loading.value = true
  try {
    const params = {
      current: pagination.page,
      size: pagination.size,
      name: searchForm.name || undefined,
      teacher: searchForm.teacher || undefined
    }
    const response = await getCourses(params)
    console.log('课程数据:', response)
    if (response && response.data) {
      const pageData = response.data
      // 如果后端有数据就用后端的，否则保留静态数据
      if (pageData.records && pageData.records.length > 0) {
        tableData.value = pageData.records
        pagination.total = pageData.total || 0
      }
    }
  } catch (error) {
    console.error('获取课程列表失败:', error)
    // 出错时保留静态数据
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  searchForm.name = ''
  searchForm.teacher = ''
  pagination.page = 1
  handleSearch()
}

const handleCreate = () => {
  dialogTitle.value = '添加课程'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑课程'
  currentRow.value = row
  Object.assign(form, {
    name: row.name,
    code: row.code,
    teacherId: row.teacherId,
    semester: row.semester,
    studentCount: row.studentCount,
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
    await ElMessageBox.confirm('确定要删除此课程吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteCourse(row.id)
    ElMessage.success('删除成功')
    await handleSearch()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除课程失败:', error)
      ElMessage.error('删除课程失败')
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
          code: form.code,
          teacherId: form.teacherId,
          semester: form.semester,
          studentCount: form.studentCount,
          description: form.description
        }
        
        if (dialogTitle.value === '添加课程') {
          await createCourse(submitData)
          ElMessage.success('添加成功')
        } else {
          await updateCourse(currentRow.value.id, submitData)
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
  Object.assign(form, {
    name: '',
    code: '',
    teacherId: null,
    semester: '',
    studentCount: 30,
    description: ''
  })
  currentRow.value = {}
}

// 加载教师列表
const loadTeachers = async () => {
  try {
    const response = await getUsers({ role: 'TEACHER', current: 1, size: 100 })
    if (response && response.data) {
      const pageData = response.data
      if (pageData.records && pageData.records.length > 0) {
        teachers.value = pageData.records
      } else if (Array.isArray(pageData)) {
        teachers.value = pageData.filter(u => u.role === 'TEACHER')
      }
    }
  } catch (error) {
    console.error('获取教师列表失败:', error)
  }
}

onMounted(async () => {
  await loadTeachers()
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

