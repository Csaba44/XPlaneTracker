<script setup>
import { ref, watch, toRef } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent } from "echarts/components";
import VChart from "vue-echarts";
import { useApproachAnalysis } from "../composables/useApproachAnalysis";
import { useRunwayProfile, buildProfileChartOption } from "../composables/useRunwayProfile";
import { ScatterChart } from "echarts/charts";
import { MarkAreaComponent } from "echarts/components";

use([CanvasRenderer, LineChart, ScatterChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent, MarkAreaComponent]);

const props = defineProps({
  flightData: { type: Object, default: null },
});

const { approachRows, isLoading, overrideRow, getRolloutCourse } = useApproachAnalysis(toRef(props, "flightData"));
const { arrivals: profileRows } = useRunwayProfile(toRef(props, "flightData"));

const showEvents = ref(true);

const fmtKt = (v) => v != null ? `${Math.round(v)} kts` : '—';
const fmtFpm = (v) => v != null ? `${v} fpm` : '—';
const fmtG = (v) => v != null ? `${v}G` : '—';
const fmtDeg = (v) => v != null ? `${v}°` : '—';
const fmtRoll = (v) => {
  if (v == null) return '—';
  const a = Math.abs(v);
  if (a < 0.5) return `${a.toFixed(1)}°`;
  return `${a.toFixed(1)}° ${v >= 0 ? 'R' : 'L'}`;
};
const fmtM = (v) => v != null ? `${v.toLocaleString()} m` : '—';

const overrideInputs = ref([]);
watch(
  approachRows,
  (rows) => {
    overrideInputs.value = rows.map((_, i) => overrideInputs.value[i] ?? { courseT: "", gsAngle: "" });
  },
  { immediate: true },
);

const applyOverride = (idx) => {
  const o = overrideInputs.value[idx];
  if (o) overrideRow(idx, o.courseT, o.gsAngle);
};

const fillFromRollout = (idx) => {
  const o = overrideInputs.value[idx];
  if (!o) return;
  const course = getRolloutCourse(idx);
  if (course == null) {
    o.courseT = "";
    return;
  }
  o.courseT = course.toFixed(2);
  applyOverride(idx);
};

const chartRefs = {};

const setChartRef = (rowIdx, chartIdx, el) => {
  if (!chartRefs[rowIdx]) chartRefs[rowIdx] = {};
  if (el) chartRefs[rowIdx][chartIdx] = el;
};

const resetChart = (rowIdx, chartIdx) => {
  chartRefs[rowIdx]?.[chartIdx]?.chart?.dispatchAction({ type: "restore" });
};

const FT_TO_M = 0.3048;
const AXIS_LABEL = { color: "#94a3b8", fontSize: 10 };
const SPLIT_LINE = { lineStyle: { color: "#334155", type: "dashed" } };
const TOOLTIP_BASE = {
  trigger: "axis",
  backgroundColor: "#1e293b",
  borderColor: "#475569",
  textStyle: { color: "#fff", fontSize: 11, fontFamily: "monospace" },
};
const LEGEND = { top: 8, textStyle: { color: "#94a3b8", fontSize: 10 }, itemHeight: 8, itemWidth: 14 };
const DATAZOOM = [{ type: "inside" }];

const getLateralOptions = (row) => {
  const lateralM = row.lateralPoints.map(p => [parseFloat((p[0] * FT_TO_M).toFixed(1)), p[1]]);
  const funnelLeftM = row.locFunnelLeft.map(p => [parseFloat((p[0] * FT_TO_M).toFixed(1)), p[1]]);
  const funnelRightM = row.locFunnelRight.map(p => [parseFloat((p[0] * FT_TO_M).toFixed(1)), p[1]]);

  const eventSeries = [];
  if (showEvents.value && row.approachEvents?.length) {
    eventSeries.push({
      name: "Events",
      type: "scatter",
      data: row.approachEvents.map(e => ({
        value: [parseFloat((e.devFt * FT_TO_M).toFixed(1)), e.nm],
        eventData: e
      })),
      symbolSize: 8,
      itemStyle: { color: "#f59e0b", borderColor: "#fff", borderWidth: 1 },
      z: 10,
      tooltip: {
        trigger: "item",
        formatter: (p) => {
          const e = p.data.eventData;
          return `${e.label}<br/>Dist: ${e.nm.toFixed(1)} NM<br/>Alt: ${e.alt} ft<br/>Speed: ${e.ias} kts`;
        }
      }
    });
  }

  return {
    backgroundColor: "transparent",
    grid: { left: "12%", right: "4%", top: "22%", bottom: "14%" },
    legend: LEGEND,
    dataZoom: DATAZOOM,
    xAxis: {
      type: "value",
      min: -900,
      max: 900,
      name: "Deviation (m)",
      nameLocation: "center",
      nameGap: 28,
      nameTextStyle: { color: "#94a3b8", fontSize: 10 },
      axisLabel: AXIS_LABEL,
      axisLine: { lineStyle: { color: "#475569" } },
      splitLine: SPLIT_LINE,
    },
    yAxis: {
      type: "value",
      inverse: true,
      min: 0,
      max: row.approachMaxNm,
      name: "NM to Threshold",
      nameRotate: 90,
      nameLocation: "center",
      nameGap: 38,
      nameTextStyle: { color: "#94a3b8", fontSize: 10 },
      axisLabel: AXIS_LABEL,
      axisLine: { lineStyle: { color: "#475569" } },
      splitLine: SPLIT_LINE,
    },
    tooltip: {
      ...TOOLTIP_BASE,
      trigger: "axis",
      axisPointer: {
        type: "line",
        axis: "y",
        lineStyle: { color: "#475569", type: "dashed", width: 1 },
      },
      formatter: (params) => {
        const yVal = params?.[0]?.axisValue;
        if (yVal == null || !lateralM.length) return "";
        let point = lateralM[0];
        for (const p of lateralM) {
          if (Math.abs(p[1] - yVal) < Math.abs(point[1] - yVal)) point = p;
        }
        const devM = Math.abs(point[0]);
        const devFt = Math.round(devM / FT_TO_M);
        const side = point[0] >= 0 ? "Right" : "Left";
        return `Dev: ${devM.toFixed(0)}m (${devFt}ft) ${side}<br/>Dist: ${point[1].toFixed(1)} NM`;
      },
    },
    series: [
      {
        name: "Aircraft Path",
        type: "line",
        smooth: false,
        symbol: "none",
        data: lateralM,
        lineStyle: { color: "#a855f7", width: 2 },
        markLine: {
          silent: true,
          symbol: "none",
          data: [{ xAxis: 0 }],
          lineStyle: { color: "#475569", type: "dashed", width: 1 },
          label: { show: false },
        },
      },
      {
        name: "LOC ±1 dot",
        type: "line",
        smooth: false,
        symbol: "none",
        data: funnelLeftM,
        lineStyle: { color: "#475569", type: "dashed", width: 1 },
      },
      {
        name: "LOC ±1 dot",
        type: "line",
        smooth: false,
        symbol: "none",
        data: funnelRightM,
        lineStyle: { color: "#475569", type: "dashed", width: 1 },
        legendHoverLink: false,
        tooltip: { show: false },
      },
      ...eventSeries
    ],
  };
};

const getVerticalOptions = (row) => {
  const maxAlt = Math.max(...row.verticalAlt.map((p) => p[1]));
  const altMax = Math.ceil((maxAlt + 1000) / 500) * 500;
  const maxGs = Math.max(...row.verticalGs.map((p) => p[1]));
  const gsMax = Math.ceil((maxGs + 30) / 50) * 50;

  const eventSeries = [];
  if (showEvents.value && row.approachEvents?.length) {
    eventSeries.push({
      name: "Events",
      type: "scatter",
      yAxisIndex: 0,
      data: row.approachEvents.map(e => ({
        value: [e.nm, e.alt],
        eventData: e
      })),
      symbolSize: 8,
      itemStyle: { color: "#f59e0b", borderColor: "#fff", borderWidth: 1 },
      z: 10,
      tooltip: {
        trigger: "item",
        formatter: (p) => {
          const e = p.data.eventData;
          return `${e.label}<br/>Dist: ${e.nm.toFixed(1)} NM<br/>Alt: ${e.alt} ft<br/>Speed: ${e.ias} kts`;
        }
      }
    });
  }

  return {
    backgroundColor: "transparent",
    grid: { left: "12%", right: "12%", top: "22%", bottom: "14%" },
    legend: LEGEND,
    dataZoom: DATAZOOM,
    xAxis: {
      type: "value",
      inverse: true,
      min: 0,
      max: row.approachMaxNm,
      name: "NM to Threshold",
      nameLocation: "center",
      nameGap: 28,
      nameTextStyle: { color: "#94a3b8", fontSize: 10 },
      axisLabel: AXIS_LABEL,
      axisLine: { lineStyle: { color: "#475569" } },
      splitLine: SPLIT_LINE,
    },
    yAxis: [
      {
        type: "value",
        name: "Altitude (ft)",
        nameRotate: 90,
        nameLocation: "center",
        nameGap: 46,
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        min: 0,
        max: altMax,
        interval: 500,
        axisLabel: AXIS_LABEL,
        axisLine: { lineStyle: { color: "#475569" } },
        splitLine: SPLIT_LINE,
      },
      {
        type: "value",
        name: "Groundspeed (kts)",
        nameRotate: -90,
        nameLocation: "center",
        nameGap: 46,
        nameTextStyle: { color: "#94a3b8", fontSize: 10 },
        position: "right",
        min: 0,
        max: gsMax,
        axisLabel: AXIS_LABEL,
        axisLine: { lineStyle: { color: "#475569" } },
        splitLine: { show: false },
      },
    ],
    tooltip: {
      ...TOOLTIP_BASE,
      formatter: (params) => {
        const xVal = params?.[0]?.axisValue;
        if (xVal == null || !row.verticalAlt?.length) return "";
        let altPoint = row.verticalAlt[0];
        for (const p of row.verticalAlt) {
          if (Math.abs(p[0] - xVal) < Math.abs(altPoint[0] - xVal)) altPoint = p;
        }
        let gsPoint = row.verticalGs[0];
        for (const p of row.verticalGs) {
          if (Math.abs(p[0] - xVal) < Math.abs(gsPoint[0] - xVal)) gsPoint = p;
        }
        const dev = altPoint[2] ?? 0;
        const devStr = dev >= 0 ? `+${dev}ft` : `${dev}ft`;
        return `Dist: ${altPoint[0].toFixed(1)} NM<br/>Alt: ${altPoint[1]} ft<br/>GS: ${gsPoint[1]} kts<br/>Dev: ${devStr}`;
      },
    },
    series: [
      {
        name: "Altitude (ft)",
        type: "line",
        yAxisIndex: 0,
        smooth: false,
        symbol: "none",
        data: row.verticalAlt,
        lineStyle: { color: "#3b82f6", width: 2 },
      },
      {
        name: "Groundspeed (kts)",
        type: "line",
        yAxisIndex: 1,
        smooth: false,
        symbol: "none",
        data: row.verticalGs,
        lineStyle: { color: "#ef4444", width: 2 },
      },
      {
        name: `${row.gsAngle ?? 3}° Glideslope`,
        type: "line",
        yAxisIndex: 0,
        smooth: false,
        symbol: "none",
        data: row.gsRefLine,
        lineStyle: { color: "#94a3b8", type: "dashed", width: 1 },
      },
      {
        name: "+1 Dot",
        type: "line",
        yAxisIndex: 0,
        smooth: false,
        symbol: "none",
        data: row.gsPlusDot,
        lineStyle: { color: "#22c55e", type: "dashed", width: 1 },
      },
      {
        name: "-1 Dot",
        type: "line",
        yAxisIndex: 0,
        smooth: false,
        symbol: "none",
        data: row.gsMinusDot,
        lineStyle: { color: "#22c55e", type: "dashed", width: 1 },
      },
      ...eventSeries
    ],
  };
};
</script>

<template>
  <div class="flex flex-col gap-6 p-6 h-full overflow-y-auto">
    <div v-if="isLoading" class="flex items-center justify-center flex-1">
      <div class="text-flight-muted text-sm">
        <i class="fa-solid fa-spinner fa-spin mr-2"></i>
        Loading approach data...
      </div>
    </div>

    <div v-else-if="!approachRows.length" class="flex items-center justify-center flex-1">
      <p class="text-flight-muted text-sm">No approach data available</p>
    </div>

    <template v-else>
      <div v-for="(row, idx) in approachRows" :key="idx" class="flex flex-col gap-3">
        <div class="flex items-center gap-3">
          <span class="text-[10px] font-black uppercase tracking-widest text-slate-400">{{ row.runwayLabel }}</span>
          <div class="flex-1 h-px bg-flight-border"></div>
        </div>

        <div v-if="row.error" class="flex items-center justify-center h-24 bg-flight-sidebar border border-flight-border rounded-xl">
          <p class="text-red-400 text-xs font-mono">{{ row.error }}</p>
        </div>

        <template v-else>
          <div class="flex justify-between items-end gap-3 flex-wrap">
            <div v-if="overrideInputs[idx]" class="flex items-end gap-3">
              <div class="flex flex-col gap-1">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest ml-1">Approach Course (°T)</span>
                <div class="flex items-center gap-2">
                  <div class="relative w-28">
                    <input v-model="overrideInputs[idx].courseT" type="number" :placeholder="row.detectedCourseT" class="w-full bg-flight-card border border-flight-border rounded-lg pl-3 pr-7 py-1.5 text-white text-xs font-mono focus:outline-none focus:border-flight-accent transition-colors" />
                    <span class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs font-mono pointer-events-none">°</span>
                  </div>
                  <button @click="fillFromRollout(idx)" title="Compute course from post-touchdown rollout track" class="bg-flight-card hover:bg-slate-800 text-white font-bold py-1.5 px-3 rounded-lg transition-colors uppercase tracking-widest text-[9px] border border-flight-border whitespace-nowrap"><i class="fa-solid fa-route mr-1"></i>From Rollout</button>
                </div>
              </div>
              <div class="flex flex-col gap-1">
                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest ml-1">Glideslope</span>
                <div class="relative w-24">
                  <input v-model="overrideInputs[idx].gsAngle" type="number" step="0.1" placeholder="3.0" class="w-full bg-flight-card border border-flight-border rounded-lg pl-3 pr-7 py-1.5 text-white text-xs font-mono focus:outline-none focus:border-flight-accent transition-colors" />
                  <span class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs font-mono pointer-events-none">°</span>
                </div>
              </div>
              <button @click="applyOverride(idx)" class="bg-flight-card hover:bg-slate-800 text-white font-bold py-1.5 px-3 rounded-lg transition-colors uppercase tracking-widest text-[9px] border border-flight-border self-end">Apply</button>
            </div>
            <div v-else></div>
            <button @click="showEvents = !showEvents" :class="['font-bold py-1.5 px-3 rounded-lg transition-colors uppercase tracking-widest text-[9px] border whitespace-nowrap', showEvents ? 'bg-flight-accent/20 text-flight-accent border-flight-accent/50' : 'bg-flight-card hover:bg-slate-800 text-slate-400 border-flight-border']">
              <i class="fa-solid fa-tags mr-1"></i> {{ showEvents ? 'Events: On' : 'Events: Off' }}
            </button>
          </div>

          <div class="flex gap-4" style="min-height: 400px">
            <div class="flex-1 bg-flight-sidebar border border-flight-border rounded-xl p-4 flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-[9px] font-black uppercase tracking-widest text-slate-500">Lateral Profile</span>
                <button @click="resetChart(idx, 0)" class="text-[9px] font-bold text-slate-500 hover:text-flight-accent transition-colors uppercase tracking-widest">Reset</button>
              </div>
              <div class="flex-1" style="min-height: 340px">
                <v-chart :ref="(el) => setChartRef(idx, 0, el)" style="width: 100%; height: 100%" :option="getLateralOptions(row)" autoresize />
              </div>
            </div>

            <div class="flex-1 bg-flight-sidebar border border-flight-border rounded-xl p-4 flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="text-[9px] font-black uppercase tracking-widest text-slate-500">Approach Profile</span>
                <button @click="resetChart(idx, 1)" class="text-[9px] font-bold text-slate-500 hover:text-flight-accent transition-colors uppercase tracking-widest">Reset</button>
              </div>
              <div class="flex-1" style="min-height: 340px">
                <v-chart :ref="(el) => setChartRef(idx, 1, el)" style="width: 100%; height: 100%" :option="getVerticalOptions(row)" autoresize />
              </div>
            </div>
          </div>
        </template>

        <div v-if="profileRows[idx] && !profileRows[idx].error" class="bg-flight-sidebar border border-flight-border rounded-xl p-4 flex flex-col gap-3">
          <div class="flex items-center justify-between">
            <span class="text-[9px] font-black uppercase tracking-widest text-slate-500">Runway Profile</span>
            <span class="text-[9px] text-slate-600 font-mono">
              {{ profileRows[idx].lengthM.toLocaleString() }}m × {{ profileRows[idx].widthM }}m
            </span>
          </div>
          <div style="height: 220px">
            <v-chart style="width: 100%; height: 100%" :option="buildProfileChartOption(profileRows[idx])" autoresize />
          </div>
          <div class="grid grid-cols-7 gap-3 pt-3 border-t border-flight-border/60">
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Rate</span>
              <span class="text-sm font-bold text-white font-mono">{{ fmtFpm(profileRows[idx].stats.rateFpm) }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">G-Force</span>
              <span class="text-sm font-bold text-white font-mono">{{ fmtG(profileRows[idx].stats.gForce) }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Runway</span>
              <span class="text-sm font-bold text-white font-mono">RW{{ profileRows[idx].runwayIdent }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">TD Point</span>
              <span class="text-sm font-bold text-white font-mono">{{ fmtM(profileRows[idx].stats.tdPointM) }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Speed</span>
              <span class="text-sm font-bold text-white font-mono">{{ fmtKt(profileRows[idx].stats.iasKt ?? profileRows[idx].stats.gsKt) }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Pitch</span>
              <span class="text-sm font-bold text-white font-mono">{{ fmtDeg(profileRows[idx].stats.pitch) }}</span>
            </div>
            <div class="flex flex-col gap-0.5">
              <span class="text-[9px] font-bold text-slate-500 uppercase tracking-widest">Roll</span>
              <span class="text-sm font-bold text-white font-mono">{{ fmtRoll(profileRows[idx].stats.roll) }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="profileRows[idx] && profileRows[idx].error" class="bg-flight-sidebar border border-flight-border rounded-xl p-4 flex items-center justify-center">
          <p class="text-amber-400/80 text-xs font-mono">Runway profile unavailable: {{ profileRows[idx].error }}</p>
        </div>
      </div>
    </template>
  </div>
</template>
