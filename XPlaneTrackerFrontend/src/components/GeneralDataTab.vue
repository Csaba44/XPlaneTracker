<script setup>
import { computed, ref } from 'vue'
import FlightTimelineTab from './FlightTimelineTab.vue'

const props = defineProps({
  flightData: { type: Object, default: null },
})

const activeSubTab = ref('overview')

const meta = computed(() => props.flightData?.metadata ?? {})
const simbrief = computed(() => meta.value.simbrief ?? null)
const timing = computed(() => meta.value.timing ?? null)
const summary = computed(() => meta.value.summary ?? null)
const weights = computed(() => meta.value.weights ?? null)
const fuel = computed(() => meta.value.fuel ?? null)
const schemaVersion = computed(() => meta.value.schema_version ?? null)
const isV2 = computed(() => !!schemaVersion.value)

const fmtTime = (unixTs) => {
  if (unixTs == null) return null
  return new Date(unixTs * 1000).toUTCString().slice(17, 25)
}

const fmtDuration = (seconds) => {
  if (seconds == null) return null
  const abs = Math.abs(seconds)
  const h = Math.floor(abs / 3600)
  const m = Math.floor((abs % 3600) / 60)
  const s = Math.floor(abs % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

const fmtDelta = (plannedSec, actualSec) => {
  if (plannedSec == null || actualSec == null) return null
  return actualSec - plannedSec
}

const fmtDeltaStr = (deltaSec) => {
  if (deltaSec == null) return null
  const sign = deltaSec <= 0 ? '-' : '+'
  return `${sign}${fmtDuration(Math.abs(deltaSec))}`
}

const deltaClass = (deltaSec, positiveIsBad = true) => {
  if (deltaSec == null) return 'text-flight-muted'
  if (deltaSec === 0) return 'text-flight-muted'
  const bad = positiveIsBad ? deltaSec > 0 : deltaSec < 0
  return bad ? 'text-red-400' : 'text-green-400'
}

const fmtKg = (v) => (v != null ? `${v.toLocaleString()} kg` : null)
const fmtNm = (v) => (v != null ? `${v} nm` : null)
const fmtKts = (v) => (v != null ? `${v} kts` : null)
const fmtNumDelta = (planned, actual) => {
  if (planned == null || actual == null) return null
  return actual - planned
}
const fmtNumDeltaStr = (delta, unit = '') => {
  if (delta == null) return null
  const sign = delta >= 0 ? '+' : ''
  return `${sign}${delta.toLocaleString()}${unit ? ' ' + unit : ''}`
}
const numDeltaClass = (delta, positiveIsBad = false) => {
  if (delta == null) return 'text-flight-muted'
  if (delta === 0) return 'text-flight-muted'
  const bad = positiveIsBad ? delta > 0 : delta < 0
  return bad ? 'text-red-400' : 'text-green-400'
}

const sb = computed(() => simbrief.value)
const t = computed(() => timing.value)

const timingRows = computed(() => [
  {
    label: 'EOBT / Off Block',
    icon: 'fa-clock',
    planned: fmtTime(sb.value?.eobt),
    actual: fmtTime(t.value?.off_block),
    delta: fmtDeltaStr(fmtDelta(sb.value?.eobt, t.value?.off_block)),
    deltaClass: deltaClass(fmtDelta(sb.value?.eobt, t.value?.off_block)),
  },
  {
    label: 'Takeoff',
    icon: 'fa-plane-departure',
    planned: fmtTime(sb.value?.sched_off),
    actual: fmtTime(t.value?.takeoff),
    delta: fmtDeltaStr(fmtDelta(sb.value?.sched_off, t.value?.takeoff)),
    deltaClass: deltaClass(fmtDelta(sb.value?.sched_off, t.value?.takeoff)),
  },
  {
    label: 'Landing',
    icon: 'fa-plane-arrival',
    planned: fmtTime(sb.value?.sched_on),
    actual: fmtTime(t.value?.landing),
    delta: fmtDeltaStr(fmtDelta(sb.value?.sched_on, t.value?.landing)),
    deltaClass: deltaClass(fmtDelta(sb.value?.sched_on, t.value?.landing)),
  },
  {
    label: 'On Block',
    icon: 'fa-square-parking',
    planned: fmtTime(sb.value?.sched_in),
    actual: fmtTime(t.value?.on_block),
    delta: fmtDeltaStr(fmtDelta(sb.value?.sched_in, t.value?.on_block)),
    deltaClass: deltaClass(fmtDelta(sb.value?.sched_in, t.value?.on_block)),
  },
])

const durationRows = computed(() => [
  {
    label: 'Block Time',
    icon: 'fa-hourglass',
    planned: fmtDuration(sb.value?.sched_block_sec),
    actual: fmtDuration(t.value?.block_time_sec),
    delta: fmtDeltaStr(fmtDelta(sb.value?.sched_block_sec, t.value?.block_time_sec)),
    deltaClass: deltaClass(fmtDelta(sb.value?.sched_block_sec, t.value?.block_time_sec)),
  },
  {
    label: 'Flight Time',
    icon: 'fa-stopwatch',
    planned: fmtDuration(sb.value?.est_block_sec),
    actual: fmtDuration(t.value?.flight_time_sec),
    delta: fmtDeltaStr(fmtDelta(sb.value?.est_block_sec, t.value?.flight_time_sec)),
    deltaClass: deltaClass(fmtDelta(sb.value?.est_block_sec, t.value?.flight_time_sec)),
  },
  {
    label: 'Taxi Out',
    icon: 'fa-road',
    planned: null,
    actual: fmtDuration(t.value?.taxi_out_sec),
    delta: null,
    deltaClass: 'text-flight-muted',
  },
  {
    label: 'Taxi In',
    icon: 'fa-road',
    planned: null,
    actual: fmtDuration(t.value?.taxi_in_sec),
    delta: null,
    deltaClass: 'text-flight-muted',
  },
])

const distanceDelta = computed(() => fmtNumDelta(sb.value?.planned_distance_nm, summary.value?.distance_nm))

const weightRows = computed(() => [
  {
    label: 'OEW / Empty',
    planned: fmtKg(sb.value?.planned_oew),
    actual: fmtKg(weights.value?.empty),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_oew, weights.value?.empty), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_oew, weights.value?.empty)),
  },
  {
    label: 'ZFW',
    planned: fmtKg(sb.value?.planned_zfw),
    actual: fmtKg(weights.value?.zfw),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_zfw, weights.value?.zfw), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_zfw, weights.value?.zfw)),
  },
  {
    label: 'TOW',
    planned: fmtKg(sb.value?.planned_tow),
    actual: fmtKg(weights.value?.tow),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_tow, weights.value?.tow), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_tow, weights.value?.tow)),
  },
  {
    label: 'LDW',
    planned: fmtKg(sb.value?.planned_ldw),
    actual: fmtKg(weights.value?.ldw),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_ldw, weights.value?.ldw), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_ldw, weights.value?.ldw)),
  },
])

const fuelRows = computed(() => [
  {
    label: 'Block Fuel',
    planned: fmtKg(sb.value?.planned_block_fuel),
    actual: fmtKg(fuel.value?.block_fuel),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_block_fuel, fuel.value?.block_fuel), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_block_fuel, fuel.value?.block_fuel)),
  },
  {
    label: 'Takeoff Fuel',
    planned: fmtKg(sb.value?.planned_takeoff_fuel),
    actual: fmtKg(fuel.value?.takeoff_fuel),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_takeoff_fuel, fuel.value?.takeoff_fuel), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_takeoff_fuel, fuel.value?.takeoff_fuel)),
  },
  {
    label: 'Landing Fuel',
    planned: fmtKg(sb.value?.planned_landing_fuel),
    actual: fmtKg(fuel.value?.landing_fuel),
    delta: fmtNumDeltaStr(fmtNumDelta(sb.value?.planned_landing_fuel, fuel.value?.landing_fuel), 'kg'),
    deltaClass: numDeltaClass(fmtNumDelta(sb.value?.planned_landing_fuel, fuel.value?.landing_fuel)),
  },
  {
    label: 'Total Used',
    planned: null,
    actual: fmtKg(fuel.value?.total_used),
    delta: null,
    deltaClass: 'text-flight-muted',
  },
])
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center justify-center gap-2 py-3 border-b border-flight-border/50 bg-flight-sidebar flex-shrink-0">
      <button
        @click="activeSubTab = 'overview'"
        :class="[
          'px-6 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border',
          activeSubTab === 'overview'
            ? 'bg-flight-accent/20 border-flight-accent/50 text-flight-accent shadow-[0_0_15px_rgba(56,189,248,0.15)]'
            : 'border-transparent text-slate-400 hover:text-white hover:bg-flight-card'
        ]"
      >
        <i class="fa-solid fa-table-list mr-2"></i>Overview
      </button>
      <button
        @click="activeSubTab = 'timeline'"
        :class="[
          'px-6 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border',
          activeSubTab === 'timeline'
            ? 'bg-flight-accent/20 border-flight-accent/50 text-flight-accent shadow-[0_0_15px_rgba(56,189,248,0.15)]'
            : 'border-transparent text-slate-400 hover:text-white hover:bg-flight-card'
        ]"
      >
        <i class="fa-solid fa-timeline mr-2"></i>Timeline
      </button>
    </div>

    <div v-if="activeSubTab === 'overview'" class="flex-grow overflow-y-auto p-6 space-y-6">
      <div v-if="!isV2" class="flex items-center gap-3 bg-sky-500/10 border border-sky-500/30 rounded-xl px-4 py-3">
        <i class="fa-solid fa-circle-info text-sky-400 text-sm"></i>
        <p class="text-sky-300 text-xs font-medium">This flight was recorded with an older client. Update the desktop app for richer analysis.</p>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div class="bg-flight-card border border-flight-border rounded-xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 border-b border-flight-border flex items-center gap-2">
            <i class="fa-solid fa-clock text-flight-accent text-xs"></i>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Timestamps (UTC)</span>
          </div>
          <table class="w-full">
            <thead>
              <tr class="border-b border-flight-border/50">
                <th class="text-left px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Event</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-sky-600 uppercase tracking-widest w-1/4">Planned</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-400 uppercase tracking-widest w-1/4">Actual</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in timingRows" :key="row.label" class="border-b border-flight-border/30 last:border-0 hover:bg-white/[0.02]">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <i :class="['fa-solid', row.icon, 'text-flight-muted text-[10px] w-3']"></i>
                    <span class="text-xs text-slate-400">{{ row.label }}</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-sky-400/70">{{ row.planned ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-white">{{ row.actual ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs" :class="row.deltaClass">{{ row.delta ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bg-flight-card border border-flight-border rounded-xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 border-b border-flight-border flex items-center gap-2">
            <i class="fa-solid fa-stopwatch text-flight-accent text-xs"></i>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Durations</span>
          </div>
          <table class="w-full">
            <thead>
              <tr class="border-b border-flight-border/50">
                <th class="text-left px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Phase</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-sky-600 uppercase tracking-widest w-1/4">Planned</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-400 uppercase tracking-widest w-1/4">Actual</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in durationRows" :key="row.label" class="border-b border-flight-border/30 last:border-0 hover:bg-white/[0.02]">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <i :class="['fa-solid', row.icon, 'text-flight-muted text-[10px] w-3']"></i>
                    <span class="text-xs text-slate-400">{{ row.label }}</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-sky-400/70">{{ row.planned ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-white">{{ row.actual ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs" :class="row.deltaClass">{{ row.delta ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bg-flight-card border border-flight-border rounded-xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 border-b border-flight-border flex items-center gap-2">
            <i class="fa-solid fa-route text-flight-accent text-xs"></i>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Distance & Speed</span>
          </div>
          <table class="w-full">
            <thead>
              <tr class="border-b border-flight-border/50">
                <th class="text-left px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Metric</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-sky-600 uppercase tracking-widest w-1/4">Planned</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-400 uppercase tracking-widest w-1/4">Actual</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-flight-border/30 last:border-0 hover:bg-white/[0.02]">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <i class="fa-solid fa-globe text-flight-muted text-[10px] w-3"></i>
                    <span class="text-xs text-slate-400">Distance</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-sky-400/70">{{ fmtNm(simbrief?.planned_distance_nm) ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-white">{{ fmtNm(summary?.distance_nm) ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs" :class="numDeltaClass(distanceDelta)">{{ distanceDelta != null ? fmtNumDeltaStr(distanceDelta, 'nm') : '—' }}</td>
              </tr>
              <tr class="border-b border-flight-border/30 last:border-0 hover:bg-white/[0.02]">
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <i class="fa-solid fa-gauge text-flight-muted text-[10px] w-3"></i>
                    <span class="text-xs text-slate-400">Avg Groundspeed</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-sky-400/70">—</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-white">{{ fmtKts(summary?.avg_groundspeed_kts) ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-flight-muted">—</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bg-flight-card border border-flight-border rounded-xl overflow-hidden shadow-lg">
          <div class="px-4 py-3 border-b border-flight-border flex items-center gap-2">
            <i class="fa-solid fa-weight-scale text-flight-accent text-xs"></i>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Weights</span>
          </div>
          <table class="w-full">
            <thead>
              <tr class="border-b border-flight-border/50">
                <th class="text-left px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Weight</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-sky-600 uppercase tracking-widest w-1/4">Planned</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-400 uppercase tracking-widest w-1/4">Actual</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in weightRows" :key="row.label" class="border-b border-flight-border/30 last:border-0 hover:bg-white/[0.02]">
                <td class="px-4 py-2.5 text-xs text-slate-400">{{ row.label }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-sky-400/70">{{ row.planned ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-white">{{ row.actual ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs" :class="row.deltaClass">{{ row.delta ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="bg-flight-card border border-flight-border rounded-xl overflow-hidden shadow-lg xl:col-span-2">
          <div class="px-4 py-3 border-b border-flight-border flex items-center gap-2">
            <i class="fa-solid fa-droplet text-flight-accent text-xs"></i>
            <span class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Fuel</span>
          </div>
          <table class="w-full">
            <thead>
              <tr class="border-b border-flight-border/50">
                <th class="text-left px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Type</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-sky-600 uppercase tracking-widest w-1/4">Planned</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-400 uppercase tracking-widest w-1/4">Actual</th>
                <th class="text-right px-4 py-2 text-[9px] font-bold text-slate-600 uppercase tracking-widest w-1/4">Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in fuelRows" :key="row.label" class="border-b border-flight-border/30 last:border-0 hover:bg-white/[0.02]">
                <td class="px-4 py-2.5 text-xs text-slate-400">{{ row.label }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-sky-400/70">{{ row.planned ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs text-white">{{ row.actual ?? '—' }}</td>
                <td class="px-4 py-2.5 text-right font-mono text-xs" :class="row.deltaClass">{{ row.delta ?? '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="!isV2 && !timing && !simbrief" class="flex flex-col items-center justify-center py-16 text-center">
        <i class="fa-solid fa-chart-bar text-4xl text-slate-700 mb-4"></i>
        <p class="text-slate-500 text-sm font-medium">No flight data available</p>
        <p class="text-slate-600 text-xs mt-1">Record a new flight with the desktop app to see detailed statistics.</p>
      </div>
    </div>

    <FlightTimelineTab v-else-if="activeSubTab === 'timeline'" :flightData="flightData" class="flex-grow" />
  </div>
</template>
