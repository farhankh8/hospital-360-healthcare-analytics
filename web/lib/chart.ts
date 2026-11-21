import type { EChartsOption } from 'echarts';
import type { ChartConfig, TableRow } from './types';
import { titleize } from './utils';

const LIGHT_PALETTE = ['#123B63', '#0E9384', '#16803C', '#D97706', '#C0392B', '#5B7DA6', '#7C6BB0', '#2C8CA8'];
const DARK_PALETTE = ['#5EA1D8', '#2DD4BF', '#4ADE80', '#FBBF24', '#F87171', '#A5B4FC', '#C4B5FD', '#67E8F9'];

interface ChartTheme {
  palette: string[];
  axisText: string;
  gridLine: string;
  tooltipBg: string;
  tooltipText: string;
  emptyText: string;
  zoomBorder: string;
}

function getChartTheme(isDark: boolean): ChartTheme {
  return isDark
    ? {
        palette: DARK_PALETTE,
        axisText: '#94A3B8',
        gridLine: '#334155',
        tooltipBg: '#1E293B',
        tooltipText: '#F1F5F9',
        emptyText: '#94A3B8',
        zoomBorder: '#334155',
      }
    : {
        palette: LIGHT_PALETTE,
        axisText: '#475569',
        gridLine: '#E2E8F0',
        tooltipBg: '#0B2545',
        tooltipText: '#F8FAFC',
        emptyText: '#64748B',
        zoomBorder: '#E2E8F0',
      };
}

export function extractRows(data: unknown, dataKey: string): TableRow[] {
  if (Array.isArray(data)) return data as TableRow[];
  if (data && typeof data === 'object') {
    const object = data as Record<string, unknown>;
    if (dataKey && Array.isArray(object[dataKey])) return object[dataKey] as TableRow[];
    const firstArray = Object.values(object).find(Array.isArray);
    if (firstArray) return firstArray as TableRow[];
  }
  return [];
}

function isNumeric(value: unknown): boolean {
  if (typeof value === 'number') return Number.isFinite(value);
  if (typeof value === 'string') return value.trim() !== '' && !Number.isNaN(Number(value));
  return false;
}

function unique(values: unknown[]): string[] {
  return Array.from(new Set(values.map((value) => String(value ?? ''))));
}

function baseTooltip(axis: boolean, theme: ChartTheme): Record<string, unknown> {
  return axis
    ? {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: theme.tooltipBg,
        borderWidth: 0,
        textStyle: { color: theme.tooltipText, fontSize: 12 },
      }
    : {
        trigger: 'item',
        backgroundColor: theme.tooltipBg,
        borderWidth: 0,
        textStyle: { color: theme.tooltipText, fontSize: 12 },
      };
}

function baseLegend(theme: ChartTheme): Record<string, unknown> {
  return { type: 'scroll', top: 4, textStyle: { color: theme.axisText, fontSize: 11 }, icon: 'roundRect', itemWidth: 12, itemHeight: 8 };
}

export interface ChartBuildResult {
  option: EChartsOption;
  rows: TableRow[];
  categories: string[];
}

/** Convert any of the documented API chart payload shapes into an ECharts option. */
export function buildChartOption(config: ChartConfig, data: unknown, isDark = false): ChartBuildResult {
  const theme = getChartTheme(isDark);
  const rows = extractRows(data, config.dataKey);
  const first = rows[0] || {};
  const keys = Object.keys(first);
  const numericKeys = keys.filter((key) => isNumeric(first[key]));
  const categoryKeys = keys.filter((key) => !isNumeric(first[key]));
  const defaultCategory = config.xKey || categoryKeys[0] || keys[0] || '';
  const defaultValue = config.valueKey || numericKeys.find((key) => key !== defaultCategory) || numericKeys[0] || '';
  const common = { color: theme.palette, animationDuration: 450 };

  if (!rows.length) {
    return {
      option: { ...common, graphic: { type: 'text', left: 'center', top: 'middle', style: { text: 'No data', fill: theme.emptyText } } } as unknown as EChartsOption,
      rows,
      categories: [],
    };
  }

  // Heatmap: x / y / value (object rows or [x, y, value] triples).
  if (config.type === 'heatmap') {
    const objectRows = rows.filter((row) => row && typeof row === 'object' && !Array.isArray(row));
    const xKey = config.xKey || Object.keys(objectRows[0] || {})[0] || 'x';
    const yKey = config.yKey || Object.keys(objectRows[0] || {}).find((key) => key !== xKey) || 'y';
    const valueKey = config.valueKey || numericKeys.find((key) => key !== xKey && key !== yKey) || 'value';
    const xCats = unique(objectRows.map((row) => row[xKey]));
    const yCats = unique(objectRows.map((row) => row[yKey]));
    const values = objectRows.map((row) => [xCats.indexOf(String(row[xKey] ?? '')), yCats.indexOf(String(row[yKey] ?? '')), Number(row[valueKey] ?? 0)]);
    const option = {
      ...common,
      tooltip: {
        ...baseTooltip(false, theme),
        formatter: (params: { data: [number, number, number] }) => `${xCats[params.data[0]]} · ${yCats[params.data[1]]}: <b>${params.data[2]}</b>`,
      },
      grid: { left: 110, right: 30, top: 20, bottom: 60, containLabel: true },
      xAxis: { type: 'category', data: xCats, axisLabel: { color: theme.axisText, rotate: xCats.length > 8 ? 35 : 0 }, axisLine: { lineStyle: { color: theme.gridLine } } },
      yAxis: { type: 'category', data: yCats, axisLabel: { color: theme.axisText }, axisLine: { lineStyle: { color: theme.gridLine } } },
      visualMap: { min: 0, max: Math.max(...values.map((item) => item[2]), 1), calculable: true, orient: 'horizontal', left: 'center', bottom: 4, textStyle: { color: theme.axisText } },
      series: [{ type: 'heatmap', data: values, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.2)' } } }],
    } as Record<string, unknown>;
    return { option: option as unknown as EChartsOption, rows, categories: xCats };
  }

  // Pie / donut.
  if (config.type === 'pie' || config.type === 'donut') {
    const data = rows.map((row) => ({ name: String(row[defaultCategory] ?? ''), value: Number(row[defaultValue] ?? 0) }));
    const option = {
      ...common,
      tooltip: { ...baseTooltip(false, theme), formatter: '{b}: <b>{c}</b> ({d}%)' },
      legend: { ...baseLegend(theme), orient: 'vertical', right: 8, top: 'middle' },
      series: [
        {
          type: 'pie',
          radius: config.type === 'donut' ? ['42%', '70%'] : '68%',
          center: ['42%', '52%'],
          data,
          label: { color: theme.axisText, fontSize: 11 },
        },
      ],
    } as Record<string, unknown>;
    return { option: option as unknown as EChartsOption, rows, categories: data.map((item) => item.name) };
  }

  // Radar: indicators are the numeric columns, values are taken from the first row.
  if (config.type === 'radar') {
    const indicators = numericKeys.map((key) => ({ name: titleize(key), max: Math.max(...rows.map((row) => Number(row[key]) || 0), 1) }));
    const values = numericKeys.map((key) => Number(first[key]) || 0);
    const option = {
      ...common,
      tooltip: baseTooltip(false, theme),
      legend: baseLegend(theme),
      radar: { indicator: indicators, center: ['50%', '56%'], radius: '62%', axisName: { color: theme.axisText, fontSize: 11 }, splitLine: { lineStyle: { color: theme.gridLine } } },
      series: [{ type: 'radar', data: [{ value: values, name: titleize(defaultCategory) || 'Values', areaStyle: { opacity: 0.18 } }] }],
    } as Record<string, unknown>;
    return { option: option as unknown as EChartsOption, rows, categories: numericKeys };
  }

  // Line / area / bar / stacked bar / horizontal bar.
  const categories = rows.map((row) => String(row[defaultCategory] ?? ''));
  const seriesKeys = (config.seriesKeys?.length ? config.seriesKeys : numericKeys.filter((key) => key !== defaultCategory)).filter((key) => keys.includes(key));
  const isBar = config.type.includes('bar');
  const isStacked = config.type === 'stacked-bar';
  const horizontal = config.type === 'horizontal-bar';
  const withZoom = (config.type === 'line' || config.type === 'area') && categories.length > 12;

  const series = (seriesKeys.length ? seriesKeys : [defaultValue]).map((key) => ({
    name: titleize(key),
    type: config.type === 'area' ? 'line' : config.type === 'stacked-bar' || config.type === 'horizontal-bar' ? 'bar' : config.type === 'line' ? 'line' : 'bar',
    stack: isStacked ? 'total' : undefined,
    smooth: config.type === 'line' || config.type === 'area',
    showSymbol: categories.length <= 24,
    symbolSize: 6,
    areaStyle: config.type === 'area' ? { opacity: 0.16 } : undefined,
    barMaxWidth: 28,
    data: rows.map((row) => Number(row[key] ?? 0)),
    itemStyle: { borderRadius: isBar && !horizontal ? [3, 3, 0, 0] : undefined },
  }));

  const categoryAxis = {
    type: 'category',
    data: categories,
    axisLabel: { color: theme.axisText, rotate: categories.length > 10 && !horizontal ? 30 : 0, hideOverlap: true },
    axisLine: { lineStyle: { color: theme.gridLine } },
  };
  const valueAxis = {
    type: 'value',
    axisLabel: { color: theme.axisText, formatter: (value: number) => (Math.abs(value) >= 1000 ? `${(value / 1000).toFixed(0)}k` : String(value)) },
    splitLine: { lineStyle: { color: theme.gridLine, type: 'dashed' } },
  };

  const option = {
    ...common,
    tooltip: baseTooltip(true, theme),
    legend: series.length > 1 ? baseLegend(theme) : undefined,
    grid: { left: 16, right: 24, top: series.length > 1 ? 44 : 20, bottom: withZoom ? 62 : 40, containLabel: true },
    xAxis: horizontal ? valueAxis : categoryAxis,
    yAxis: horizontal ? { ...categoryAxis, inverse: true } : valueAxis,
    dataZoom: withZoom
      ? [
          { type: 'inside', xAxisIndex: 0 },
          { type: 'slider', xAxisIndex: 0, height: 18, bottom: 8, borderColor: theme.gridLine, textStyle: { color: theme.axisText, fontSize: 10 } },
        ]
      : undefined,
    series,
  } as Record<string, unknown>;

  return { option: option as unknown as EChartsOption, rows, categories };
}
