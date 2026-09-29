<template>
  <el-card>
    <div class="toolbar">
      <el-select v-model="filters.table_name" placeholder="业务表" clearable style="width: 160px">
        <el-option v-for="t in tables" :key="t" :label="TABLE_LABELS[t] || t" :value="t" />
      </el-select>
      <el-select v-model="filters.action" placeholder="操作类型" clearable style="width: 120px">
        <el-option v-for="(label, value) in ACTION_LABELS" :key="value" :label="label" :value="value" />
      </el-select>
      <el-input v-model="filters.username" placeholder="操作人" clearable style="width: 140px" @keyup.enter="search" />
      <el-input-number v-model="filters.record_id" placeholder="记录ID" :min="1" controls-position="right" style="width: 140px" />
      <el-date-picker
        v-model="range"
        type="datetimerange"
        range-separator="至"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        style="width: 360px"
      />
      <el-button type="primary" :icon="Search" @click="search">查询</el-button>
      <el-button :icon="Refresh" @click="reset">重置</el-button>
      <div class="spacer" />
      <el-button :icon="Download" :loading="exporting" @click="onExport">导出 CSV</el-button>
    </div>

    <el-alert
      type="info"
      show-icon
      :closable="false"
      class="tip"
      title="审计追踪记录所有数据的创建、修改与删除（含操作人、时间、修改前后值），记录不可修改、不可删除。"
    />

    <el-table v-loading="loading" :data="list" border stripe>
      <el-table-column prop="created_at" label="时间" width="165">
        <template #default="{ row }">{{ row.created_at?.replace('T', ' ') }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="ACTION_TAG[row.action] || 'info'" size="small">{{ ACTION_LABELS[row.action] || row.action }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="业务表" width="110">
        <template #default="{ row }">{{ TABLE_LABELS[row.table_name] || row.table_name }}</template>
      </el-table-column>
      <el-table-column prop="record_id" label="记录ID" width="80" align="center">
        <template #default="{ row }">{{ row.record_id ?? '-' }}</template>
      </el-table-column>
      <el-table-column prop="username" label="操作人" width="110" />
      <el-table-column label="修改字段" width="130">
        <template #default="{ row }">
          <el-tag v-if="row.field_name === '*'" type="info" size="small">{{ row.action === 'delete' ? '整行(删除)' : '整行(新增)' }}</el-tag>
          <template v-else>{{ fieldLabel(row.table_name, row.field_name) }}</template>
        </template>
      </el-table-column>
      <el-table-column label="修改前" min-width="200">
        <template #default="{ row }">
          <el-tooltip :content="fmtValue(row.old_value, row.table_name)" placement="top" :show-after="300">
            <div class="cell-val">{{ fmtValue(row.old_value, row.table_name) }}</div>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="修改后" min-width="200">
        <template #default="{ row }">
          <el-tooltip :content="fmtValue(row.new_value, row.table_name)" placement="top" :show-after="300">
            <div class="cell-val">{{ fmtValue(row.new_value, row.table_name) }}</div>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="operation_id" label="操作ID" width="130" show-overflow-tooltip />
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="load"
        @size-change="onSizeChange"
      />
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { getAuditTables, getAuditLogs, getAuditLabels, exportAuditLogs } from '@/api/audit'

// 兜底字典：接口未返回前先用英文原文占位，避免模板访问 undefined
const ACTION_LABELS = ref({ insert: '新增', update: '修改', delete: '删除' })
const ACTION_TAG = { insert: 'success', update: 'warning', delete: 'danger' }
const TABLE_LABELS = ref({})
const FIELD_LABELS = ref({})

const fieldLabel = (table, field) => FIELD_LABELS.value[table]?.[field] || field

const loading = ref(false)
const exporting = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const tables = ref([])

const emptyFilters = () => ({
  table_name: null,
  action: null,
  username: '',
  record_id: null,
  start_time: null,
  end_time: null,
})
const filters = reactive(emptyFilters())
const range = ref(null)

/** tableName 必须取行自身的 table_name，不能用筛选条件——否则未筛选时拿不到字典 */
const fmtValue = (value, tableName) => {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'object') {
    return Object.entries(value)
      .filter(([k, v]) => v !== '' && v !== null && v !== undefined)
      .map(([k, v]) => `${fieldLabel(tableName, k)}: ${String(v)}`)
      .join('\n')
  }
  return String(value)
}

const buildParams = () => ({
  page: page.value,
  size: size.value,
  table_name: filters.table_name || undefined,
  action: filters.action || undefined,
  username: filters.username || undefined,
  record_id: filters.record_id || undefined,
  start_time: range.value?.[0] ? range.value[0].toISOString() : undefined,
  end_time: range.value?.[1] ? range.value[1].toISOString() : undefined,
})

const load = async () => {
  loading.value = true
  try {
    const data = await getAuditLogs(buildParams())
    list.value = data.items
    total.value = data.total
  } catch {
    // 提示已由全局拦截器统一给出
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  load()
}

const reset = () => {
  Object.assign(filters, emptyFilters())
  range.value = null
  search()
}

const onSizeChange = () => {
  page.value = 1
  load()
}

const onExport = async () => {
  exporting.value = true
  try {
    const { data, headers } = await exportAuditLogs(buildParams())
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_logs_${new Date().toISOString().slice(0, 19).replace(/[-:]/g, '')}.csv`
    link.click()
    URL.revokeObjectURL(url)

    // 后端超上限时会截断，必须让用户知道拿到的不是全部数据
    if (headers['x-export-truncated'] === 'true') {
      const matched = Number(headers['x-export-matched'])
      const exported = Number(headers['x-export-exported'])
      ElMessage.warning(
        `数据量超过导出上限，仅导出最早的 ${exported} 条（共命中 ${matched} 条），请收窄筛选条件后重试`,
      )
    } else {
      ElMessage.success('导出成功')
    }
  } catch {
    // 提示已由全局拦截器统一给出
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  try {
    const [labelDict, tableList] = await Promise.all([getAuditLabels(), getAuditTables()])
    ACTION_LABELS.value = labelDict.actions || ACTION_LABELS.value
    TABLE_LABELS.value = labelDict.tables || {}
    FIELD_LABELS.value = labelDict.fields || {}
    tables.value = tableList
  } catch {
    // 字典拿不到时保留兜底值，列表仍可查看
  }
  load()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.spacer {
  flex: 1;
}
.tip {
  margin: 16px 0;
}
.cell-val {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>