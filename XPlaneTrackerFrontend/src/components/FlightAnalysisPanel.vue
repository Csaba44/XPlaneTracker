<script setup>
import { ref } from 'vue'
import ApproachAnalysisTab from './ApproachAnalysisTab.vue'
import GeneralDataTab from './GeneralDataTab.vue'

const props = defineProps({
  flightData: { type: Object, default: null },
})

const emit = defineEmits(['close'])

const activeTab = ref('general')

const tabs = [
  { key: 'general', label: 'General Data' },
  { key: 'departure', label: 'Departure Analysis' },
  { key: 'approach', label: 'Approach Analysis' },
]
</script>

<template>
  <div class="fixed inset-0 bg-flight-bg z-[2000] flex flex-col">
    <div class="flex items-center justify-between px-6 py-4 border-b border-flight-border flex-shrink-0">
      <div class="flex items-center gap-1">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          @click="activeTab = tab.key"
          :class="[
            'px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all border',
            activeTab === tab.key
              ? 'bg-flight-card border-flight-accent/60 text-white'
              : 'border-transparent text-flight-muted hover:text-white hover:bg-flight-card/50',
          ]"
        >
          {{ tab.label }}
        </button>
      </div>

      <button
        @click="emit('close')"
        class="text-slate-400 hover:text-white transition-colors p-2 rounded-lg hover:bg-flight-card"
      >
        <i class="fa-solid fa-xmark text-sm"></i>
      </button>
    </div>

    <div class="flex-grow overflow-hidden">
      <GeneralDataTab v-if="activeTab === 'general'" :flightData="flightData" class="h-full" />

      <div v-else-if="activeTab === 'departure'" class="flex items-center justify-center h-full">
        <p class="text-flight-muted text-sm">No data available</p>
      </div>

      <ApproachAnalysisTab v-else-if="activeTab === 'approach'" :flightData="flightData" class="h-full" />
    </div>
  </div>
</template>
