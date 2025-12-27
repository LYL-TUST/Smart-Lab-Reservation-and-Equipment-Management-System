<template>
  <div class="dashboard">
    <!-- 欢迎卡片 -->
    <el-card class="welcome-card gradient-bg">
      <div class="welcome-content">
        <div class="welcome-text">
          <h2>欢迎回来，{{ userStore.userInfo.username }}！</h2>
          <p>今天是 {{ currentDate }}，祝您工作愉快</p>
        </div>
        <el-icon :size="80" color="rgba(255,255,255,0.3)">
          <TrophyBase />
        </el-icon>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card hover-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon gradient-bg-blue">
              <el-icon :size="30"><Calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalReservations }}</div>
              <div class="stat-label">总预约数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card hover-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon gradient-bg-green">
              <el-icon :size="30"><OfficeBuilding /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalLabs }}</div>
              <div class="stat-label">实验室数量</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :md="6">
        <el-card class="stat-card hover-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon gradient-bg-orange">
              <el-icon :size="30"><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalEquipment }}</div>
              <div class="stat-label">设备总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col v-permission="'user:manage'" :xs="24" :sm="12" :md="6">
        <el-card class="stat-card hover-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon gradient-bg-purple">
              <el-icon :size="30"><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.activeUsers }}</div>
              <div class="stat-label">活跃用户</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>预约趋势</span>
              <el-button type="primary" text>查看详情</el-button>
            </div>
          </template>
          <div ref="reservationChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>实验室使用率</span>
              <el-button type="primary" text>查看详情</el-button>
            </div>
          </template>
          <div ref="labUsageChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近预约 -->
    <el-row :gutter="20">
      <el-col :xs="24" :md="16">
        <el-card class="recent-card">
          <template #header>
            <div class="card-header">
              <span>最近预约</span>
              <el-button type="primary" text @click="$router.push('/reservations')">
                查看全部
              </el-button>
            </div>
          </template>
          <el-table :data="recentReservations" style="width: 100%">
            <el-table-column prop="laboratoryName" label="实验室" />
            <el-table-column prop="startTime" label="开始时间" />
            <el-table-column prop="endTime" label="结束时间" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card class="notice-card">
          <template #header>
            <div class="card-header">
              <span>系统公告</span>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="notice in notices"
              :key="notice.id"
              :timestamp="notice.time"
              placement="top"
            >
              <el-card>
                <h4>{{ notice.title }}</h4>
                <p>{{ notice.content }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { Calendar, OfficeBuilding, Monitor, User, TrophyBase } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { getDashboardStats } from '../api/dashboard'
import * as echarts from 'echarts'

const userStore = useUserStore()

const currentDate = ref(new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  weekday: 'long'
}))

const stats = reactive({
  totalReservations: 0,
  totalLabs: 0,
  totalEquipment: 0,
  activeUsers: 0
})

// 加载统计数据
const loadStats = async () => {
  try {
    const response = await getDashboardStats()
    if (response && response.data) {
      stats.totalReservations = response.data.totalReservations || 0
      stats.totalLabs = response.data.totalLabs || 0
      stats.totalEquipment = response.data.totalEquipment || 0
      stats.activeUsers = response.data.activeUsers || 0
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
    // 失败时保持默认值0，不显示错误提示
  }
}

const recentReservations = ref([
  {
    id: 1,
    laboratoryName: '计算机实验室A',
    startTime: '2024-12-24 14:00',
    endTime: '2024-12-24 16:00',
    status: 'APPROVED'
  },
  {
    id: 2,
    laboratoryName: '物理实验室B',
    startTime: '2024-12-25 09:00',
    endTime: '2024-12-25 11:00',
    status: 'PENDING'
  },
  {
    id: 3,
    laboratoryName: '化学实验室C',
    startTime: '2024-12-26 10:00',
    endTime: '2024-12-26 12:00',
    status: 'APPROVED'
  }
])

const notices = ref([
  {
    id: 1,
    title: '系统维护通知',
    content: '系统将于本周六进行维护升级',
    time: '2024-12-24 10:00'
  },
  {
    id: 2,
    title: '新功能上线',
    content: '预约系统新增智能推荐功能',
    time: '2024-12-23 15:30'
  },
  {
    id: 3,
    title: '假期安排',
    content: '元旦假期实验室开放时间调整',
    time: '2024-12-22 09:00'
  }
])

const reservationChartRef = ref(null)
const labUsageChartRef = ref(null)

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

const initReservationChart = () => {
  const chart = echarts.init(reservationChartRef.value)
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '预约数量',
        type: 'line',
        smooth: true,
        data: [12, 18, 15, 22, 19, 8, 5],
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.5)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ])
        },
        itemStyle: {
          color: '#409eff'
        }
      }
    ]
  }
  chart.setOption(option)
  
  window.addEventListener('resize', () => {
    chart.resize()
  })
}

const initLabUsageChart = () => {
  const chart = echarts.init(labUsageChartRef.value)
  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '使用率',
        type: 'pie',
        radius: '50%',
        data: [
          { value: 35, name: '计算机实验室' },
          { value: 28, name: '物理实验室' },
          { value: 22, name: '化学实验室' },
          { value: 15, name: '生物实验室' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  }
  chart.setOption(option)
  
  window.addEventListener('resize', () => {
    chart.resize()
  })
}

onMounted(async () => {
  await loadStats()
  nextTick(() => {
    initReservationChart()
    initLabUsageChart()
  })
})
</script>

<style scoped>
.dashboard {
  width: 100%;
}

.welcome-card {
  margin-bottom: 20px;
  border: none;
  color: white;
}

.welcome-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.welcome-text h2 {
  font-size: 28px;
  margin-bottom: 10px;
}

.welcome-text p {
  font-size: 16px;
  opacity: 0.9;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: var(--text-primary);
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.charts-row {
  margin-bottom: 20px;
}

.chart-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.recent-card,
.notice-card {
  margin-bottom: 20px;
}

@media (max-width: 768px) {
  .welcome-text h2 {
    font-size: 20px;
  }
  
  .welcome-text p {
    font-size: 14px;
  }
  
  .stat-value {
    font-size: 24px;
  }
  
  .chart-container {
    height: 250px;
  }
}
</style>

