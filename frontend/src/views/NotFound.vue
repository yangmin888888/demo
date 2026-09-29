<template>
  <el-result icon="warning" title="404" :sub-title="`找不到页面 ${route.fullPath}`">
    <template #extra>
      <el-button type="primary" @click="goHome">返回首页</el-button>
      <el-button @click="goBack">返回上一页</el-button>
    </template>
  </el-result>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const goHome = () => router.push('/dashboard')
const goBack = () => (window.history.length > 1 ? router.back() : router.push('/dashboard'))
</script>
