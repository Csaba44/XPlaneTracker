<script setup>
import { toRef } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, ScatterChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent } from "echarts/components";
import VChart from "vue-echarts";
import { useRunwayProfile, buildProfileChartOption } from "../composables/useRunwayProfile";

use([CanvasRenderer, LineChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, MarkAreaComponent]);

const props = defineProps({
  flightData: { type: Object, default: null },
});

const { departures: profileRows, isLoading } = useRunwayProfile(toRef(props, "flightData"));

const fmtKt = (v) => v != null ? `${Math.round(v)} kts` : '—';
const fmtFpm = (v) => v != null ? `${v.toLocaleString()} fpm` : '—';
const fmtDeg = (v) => v != null ? `${v}°` : '—';
const fmtRoll = (v) => {
  if (v == null) return '—';
  const a = Math.abs(v);
  if (a < 0.5) return `${a.toFixed(1)}°`;
  return `${a.toFixed(1)}° ${v >= 0 ? 'Right' : 'Left'}`;
};
const fmtM = (v) => v != null ? `${v.toLocaleString()} m` : '—';
const fmtFtNm = (v) => v != null ? `${v.toLocaleString()} ft/NM` : '—';
const fmtDev = (v) => {
  if (v == null) return '—';
  return `${Math.abs(v)} m`;
};
</script>

<template>
  <div class="flex flex-col gap-6 p-6 h-full overflow-y-auto">
    <div v-if="isLoading" class="flex items-center justify-center flex-1">
      <div class="text-flight-muted text-sm">
        <i class="fa-solid fa-spinner fa-spin mr-2"></i>
        Loading departure data...
      </div>
    </div>

    <div v-else-if="!profileRows.length" class="flex items-center justify-center flex-1">
      <p class="text-flight-muted text-sm">No departure data available</p>
    </div>

    <template v-else>
      <div v-for="(row, idx) in profileRows" :key="idx" class="flex flex-col gap-3">
        <div class="flex items-center gap-3">
          <span class="text-[10px] font-black uppercase tracking-widest text-slate-400">{{ row.runwayLabel }}</span>
          <div class="flex-1 h-px bg-flight-border"></div>
        </div>

        <div v-if="row.error" class="flex items-center justify-center h-24 bg-flight-sidebar border border-flight-border rounded-xl">
          <p class="text-red-400 text-xs font-mono">{{ row.error }}</p>
        </div>

        <div v-else class="bg-flight-sidebar border border-flight-border rounded-xl p-4 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <span class="text-[9px] font-black uppercase tracking-widest text-slate-500">Runway Profile</span>
            <span class="text-[9px] text-slate-600 font-mono">
              {{ row.lengthM.toLocaleString() }}m × {{ row.widthM }}m
            </span>
          </div>
          <div style="height: 220px">
            <v-chart style="width: 100%; height: 100%" :option="buildProfileChartOption(row)" autoresize />
          </div>

          <div class="pt-3 border-t border-flight-border/60">
            <div class="text-[9px] font-black uppercase tracking-widest text-slate-500 mb-2">Liftoff Performance</div>
            <div class="grid grid-cols-8 gap-3">
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Liftoff Speed</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtKt(row.stats.liftoffSpeedKt ?? row.stats.gsKt) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Pitch</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtDeg(row.stats.pitch) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Roll</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtRoll(row.stats.roll) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Runway</span>
                <span class="text-sm font-bold text-white font-mono">RW{{ row.runwayIdent }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Takeoff Roll</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtM(row.stats.takeoffRollM) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Climb Gradient</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtFtNm(row.stats.climbGradientFtPerNm) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Climb Rate</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtFpm(row.stats.climbRateFpm) }}</span>
              </div>
              <div class="flex flex-col gap-0.5">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Max CL Dev</span>
                <span class="text-sm font-bold text-white font-mono">{{ fmtDev(row.stats.maxCenterlineDevM) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
