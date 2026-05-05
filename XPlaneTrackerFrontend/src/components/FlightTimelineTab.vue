<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  flightData: { type: Object, default: null },
})

const activeFilter = ref('all')

const rawEvents = computed(() => props.flightData?.events ?? [])
const rawPhases = computed(() => props.flightData?.phases ?? [])

const fmtTime = (ts) => {
  if (ts == null) return '—'
  return new Date(ts * 1000).toISOString().slice(11, 19) + ' UTC'
}

const fmtDuration = (secs) => {
  if (!secs) return null
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = Math.floor(secs % 60)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

const EVENT_META = {
  engine_start:    { icon: 'fa-circle-play',          color: 'text-green-400',  bg: 'bg-green-500/10',   border: 'border-green-500/25',   label: 'Engine Start',    critical: false },
  engine_shutdown: { icon: 'fa-circle-stop',          color: 'text-red-400',    bg: 'bg-red-500/10',     border: 'border-red-500/25',     label: 'Engine Shutdown', critical: false },
  liftoff:         { icon: 'fa-plane-departure',      color: 'text-cyan-400',   bg: 'bg-cyan-500/10',    border: 'border-cyan-500/25',    label: 'Liftoff',         critical: false },
  touchdown:       { icon: 'fa-plane-arrival',        color: 'text-cyan-400',   bg: 'bg-cyan-500/10',    border: 'border-cyan-500/25',    label: 'Touchdown',       critical: false },
  gear_up:         { icon: 'fa-circle-chevron-up',    color: 'text-amber-400',  bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   label: 'Gear Up',         critical: false },
  gear_down:       { icon: 'fa-circle-chevron-down',  color: 'text-amber-400',  bg: 'bg-amber-500/10',   border: 'border-amber-500/25',   label: 'Gear Down',       critical: false },
  flaps_set:       { icon: 'fa-sliders',              color: 'text-violet-400', bg: 'bg-violet-500/10',  border: 'border-violet-500/25',  label: 'Flaps',           critical: false },
  stall:           { icon: 'fa-triangle-exclamation', color: 'text-red-400',    bg: 'bg-red-500/10',     border: 'border-red-500/25',     label: 'Stall Warning',   critical: true  },
  touch_and_go:    { icon: 'fa-repeat',               color: 'text-orange-400', bg: 'bg-orange-500/10',  border: 'border-orange-500/25',  label: 'Touch & Go',      critical: false },
  phase_change:    { icon: 'fa-arrow-right-arrow-left', color: 'text-slate-400', bg: 'bg-slate-500/10', border: 'border-slate-500/25',   label: 'Phase Change',    critical: false },
}

const PHASE_META = {
  taxi_out: { icon: 'fa-road',             color: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/25',  label: 'Taxi Out'  },
  climb:    { icon: 'fa-arrow-trend-up',   color: 'text-green-400',  bg: 'bg-green-500/10',  border: 'border-green-500/25',  label: 'Climb'     },
  cruise:   { icon: 'fa-minus',            color: 'text-sky-400',    bg: 'bg-sky-500/10',    border: 'border-sky-500/25',    label: 'Cruise'    },
  descent:  { icon: 'fa-arrow-trend-down', color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/25', label: 'Descent'   },
  approach: { icon: 'fa-plane-arrival',    color: 'text-violet-400', bg: 'bg-violet-500/10', border: 'border-violet-500/25', label: 'Approach'  },
  taxi_in:  { icon: 'fa-road',             color: 'text-amber-400',  bg: 'bg-amber-500/10',  border: 'border-amber-500/25',  label: 'Taxi In'   },
}

const buildDetail = (evt) => {
  const parts = []
  if (evt.alt != null)            parts.push(`${evt.alt.toLocaleString()} ft`)
  if (evt.ias != null)            parts.push(`${evt.ias} kts IAS`)
  if (evt.gs != null)             parts.push(`${evt.gs} kts GS`)
  if (evt.pitch != null)          parts.push(`Pitch ${evt.pitch}°`)
  if (evt.max_pitch_10s != null)  parts.push(`Max pitch ${evt.max_pitch_10s}°`)
  if (evt.roll != null && Math.abs(evt.roll) > 0.5) parts.push(`Roll ${evt.roll}°`)
  if (evt.landing_index != null)  parts.push(`Landing #${evt.landing_index + 1}`)
  return parts.join('  ·  ') || null
}

const allItems = computed(() => {
  const items = []

  rawPhases.value.forEach((phase) => {
    const cfg = PHASE_META[phase.type] ?? PHASE_META.cruise
    items.push({
      ts: phase.start,
      kind: 'phase',
      type: phase.type,
      label: cfg.label,
      icon: cfg.icon,
      color: cfg.color,
      bg: cfg.bg,
      border: cfg.border,
      detail: phase.peak_alt ? `Peak: ${phase.peak_alt.toLocaleString()} ft` : null,
      duration: phase.end != null ? phase.end - phase.start : null,
      critical: false,
    })
  })

  rawEvents.value.forEach((evt) => {
    const cfg = EVENT_META[evt.type] ?? EVENT_META.phase_change
    const engineSuffix = evt.engine != null ? ` #${evt.engine + 1}` : ''
    const flapSuffix = evt.type === 'flaps_set' && evt.index != null ? ` ${evt.index}` : ''
    items.push({
      ts: evt.ts,
      kind: 'event',
      type: evt.type,
      label: cfg.label + engineSuffix + flapSuffix,
      icon: cfg.icon,
      color: cfg.color,
      bg: cfg.bg,
      border: cfg.border,
      detail: buildDetail(evt),
      duration: null,
      critical: cfg.critical,
    })
  })

  return items.sort((a, b) => a.ts - b.ts)
})

const FILTERS = [
  { key: 'all',      label: 'All'      },
  { key: 'phases',   label: 'Phases'   },
  { key: 'events',   label: 'Events'   },
  { key: 'critical', label: 'Critical' },
]

const displayed = computed(() => {
  if (activeFilter.value === 'phases')   return allItems.value.filter((i) => i.kind === 'phase')
  if (activeFilter.value === 'events')   return allItems.value.filter((i) => i.kind === 'event')
  if (activeFilter.value === 'critical') return allItems.value.filter((i) => i.critical)
  return allItems.value
})

const hasData = computed(() => rawEvents.value.length > 0 || rawPhases.value.length > 0)
</script>

<template>
  <div class="h-full flex flex-col">
    <div class="flex items-center gap-1.5 px-6 py-3 border-b border-flight-border flex-shrink-0">
      <button
        v-for="f in FILTERS"
        :key="f.key"
        @click="activeFilter = f.key"
        :class="[
          'px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border',
          activeFilter === f.key
            ? 'bg-flight-accent/20 border-flight-accent/50 text-flight-accent'
            : 'border-transparent text-flight-muted hover:text-white hover:bg-flight-card/50',
        ]"
      >{{ f.label }}</button>

      <span v-if="hasData" class="ml-auto text-[10px] text-slate-600 font-mono">
        {{ displayed.length }} item{{ displayed.length !== 1 ? 's' : '' }}
      </span>
    </div>

    <div v-if="!hasData" class="flex-grow flex flex-col items-center justify-center text-center px-8">
      <i class="fa-solid fa-timeline text-4xl text-slate-700 mb-4"></i>
      <p class="text-slate-500 text-sm font-medium">No timeline data</p>
      <p class="text-slate-600 text-xs mt-1">Record a new flight with the updated desktop app to see events and phases.</p>
    </div>

    <div v-else-if="displayed.length === 0" class="flex-grow flex flex-col items-center justify-center text-center">
      <i class="fa-solid fa-filter text-3xl text-slate-700 mb-3"></i>
      <p class="text-slate-500 text-sm">No items match this filter</p>
    </div>

    <div v-else class="flex-grow overflow-y-auto px-6 py-5">
      <div class="relative ml-3">
        <div class="absolute left-[14px] top-2 bottom-2 w-px bg-flight-border/60"></div>

        <div class="space-y-0.5">
          <div
            v-for="(item, idx) in displayed"
            :key="idx"
            class="relative flex items-start gap-4 pl-10 py-2.5 rounded-xl group hover:bg-flight-card/50 transition-colors"
          >
            <div
              :class="[
                'absolute left-0 w-[28px] h-[28px] rounded-full border flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-110 z-10',
                item.bg, item.border,
              ]"
            >
              <i :class="['fa-solid text-[9px]', item.icon, item.color]"></i>
            </div>

            <div class="flex-grow min-w-0 pt-0.5">
              <div class="flex items-center gap-2 flex-wrap">
                <span :class="['text-xs font-bold leading-none', item.color]">{{ item.label }}</span>

                <span
                  v-if="item.critical"
                  class="text-[8px] font-black uppercase tracking-widest text-red-400 bg-red-400/10 border border-red-400/30 px-1.5 py-0.5 rounded-full"
                >Critical</span>

                <span
                  v-if="item.kind === 'phase'"
                  class="text-[8px] font-bold uppercase tracking-widest text-slate-500 bg-slate-700/40 border border-slate-600/30 px-1.5 py-0.5 rounded-full"
                >Phase</span>

                <span class="font-mono text-[10px] text-slate-600 ml-auto flex-shrink-0">{{ fmtTime(item.ts) }}</span>
              </div>

              <p v-if="item.detail" class="text-[11px] text-slate-400 font-mono mt-1 leading-relaxed">{{ item.detail }}</p>

              <p v-if="item.duration" class="text-[10px] text-slate-600 mt-0.5">
                Duration: {{ fmtDuration(item.duration) }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
