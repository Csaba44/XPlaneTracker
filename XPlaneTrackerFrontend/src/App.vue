<script setup>
import { Toaster } from "vue-sonner";
import "vue-sonner/style.css";
</script>
<template>
  <Toaster position="bottom-left" theme="dark" />

  <router-view />
</template>
