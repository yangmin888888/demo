<template>
  <el-card>
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="用户名/昵称/邮箱搜索"
        clearable
        style="width: 260px"
        @keyup.enter="search"
        @clear="search"
      >
        <template #append>
          <el-button :icon="Search" @click="search" />
        </template>
      </el-input>
      <el-button type="primary" :icon="Plus" @click="openDialog()">新增用户</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe border>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="nickname" label="昵称" min-width="120">
        <template #default="{ row }">{{ row.nickname || '-' }}</template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column label="角色" width="110">
        <template #default="{ row }">
          <el-tag :type="row.is_superuser ? 'danger' : 'info'">
            {{ row.is_superuser ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'warning'">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ row.created_at?.replace('T', ' ').slice(0, 19) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" :disabled="row.id === userStore.userInfo?.id" @click="onDelete(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="load"
        @size-change="onSizeChange"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑用户' : '新增用户'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="!!form.id" placeholder="至少 3 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" />
        </el-form-item>
        <el-form-item :label="form.id ? '重置密码' : '密码'" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            :placeholder="form.id ? '不修改请留空' : '至少 6 位'"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-switch
            v-model="form.is_superuser"
            active-text="管理员"
            inactive-text="普通用户"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import { getUserList, createUser, updateUser, deleteUser } from '@/api/user'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')

const dialogVisible = ref(false)
const formRef = ref()
const emptyForm = {
  id: null,
  username: '',
  email: '',
  nickname: '',
  password: '',
  is_active: true,
  is_superuser: false,
}
const form = reactive({ ...emptyForm })

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '3-50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!form.id && !value) return callback(new Error('请输入密码'))
        if (value && value.length < 6) return callback(new Error('密码至少 6 位'))
        callback()
      },
      trigger: 'blur',
    },
  ],
}

const load = async () => {
  loading.value = true
  try {
    const data = await getUserList({ page: page.value, size: size.value, keyword: keyword.value || undefined })
    list.value = data.items
    total.value = data.total
  } catch {
    // 错误提示已由全局拦截器统一给出，这里只需避免未捕获的 rejection
  } finally {
    loading.value = false
  }
}

const search = () => {
  page.value = 1
  load()
}

const onSizeChange = () => {
  page.value = 1
  load()
}

const openDialog = (row) => {
  Object.assign(form, emptyForm, row ? { ...row, password: '' } : {})
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

/**
 * 把后端 422 的字段级错误定位到具体表单项。
 * Element Plus 的 FormInstance 没有 setFields 之类的公开 API，
 * 因此这里用受支持的 scrollToField 把出错的字段滚动到可见区域，
 * 具体文案由全局拦截器以 toast 呈现。
 */
const focusServerError = (errors) => {
  const field = errors.find((e) => e.field && formRef.value)
  if (field) {
    formRef.value.scrollToField(field.field)
  }
}

const onSave = async () => {
  try {
    // 表单校验不通过时 validate() 也会 reject，同样需要接住
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    if (form.id) {
      const payload = { ...form }
      delete payload.id
      delete payload.username
      if (!payload.password) delete payload.password
      await updateUser(form.id, payload)
    } else {
      await createUser({ ...form })
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    load()
  } catch (err) {
    if (err.validationErrors?.length) {
      focusServerError(err.validationErrors)
    }
  } finally {
    saving.value = false
  }
}

const onDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    // 用户取消删除，ElMessageBox reject 的 'cancel' 必须吞掉
    return
  }
  try {
    await deleteUser(row.id)
    ElMessage.success('删除成功')
    load()
  } catch {
    // 提示已由全局拦截器给出
  }
}

onMounted(load)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
