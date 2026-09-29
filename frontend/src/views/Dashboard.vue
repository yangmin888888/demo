<template>
  <div>
    <el-card>
      <template #header>欢迎回来</template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ userStore.userInfo?.username }}</el-descriptions-item>
        <el-descriptions-item label="昵称">{{ userStore.userInfo?.nickname || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ userStore.userInfo?.email }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="userStore.isSuperuser ? 'danger' : 'info'">
            {{ userStore.isSuperuser ? '超级管理员' : '普通用户' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDateTime(userStore.userInfo?.created_at) }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { useUserStore } from '@/stores/user'
import { formatDateTime } from '@/utils/datetime'

const userStore = useUserStore()
</script>
