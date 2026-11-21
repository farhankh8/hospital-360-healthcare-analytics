'use client';

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';

export interface EChartProps {
  option: EChartsOption;
  height?: number | string;
  className?: string;
  onClick?: (params: Record<string, unknown>) => void;
  onDataZoom?: (params: Record<string, unknown>) => void;
}

export default function EChart({ option, height = 320, className, onClick, onDataZoom }: EChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const clickRef = useRef(onClick);
  const zoomRef = useRef(onDataZoom);
  clickRef.current = onClick;
  zoomRef.current = onDataZoom;

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const chart = echarts.init(element, undefined, { renderer: 'canvas' });
    chartRef.current = chart;

    const handleClick = (params: unknown) => clickRef.current?.(params as Record<string, unknown>);
    const handleZoom = (params: unknown) => zoomRef.current?.(params as Record<string, unknown>);
    chart.on('click', handleClick);
    chart.on('datazoom', handleZoom);

    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(element);

    return () => {
      observer.disconnect();
      chart.off('click', handleClick);
      chart.off('datazoom', handleZoom);
      chart.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const numericHeight = typeof height === 'number' ? height : parseInt(String(height), 10) || 320;
    const showToolbox = numericHeight > 80;
    const base: EChartsOption = {
      toolbox: showToolbox ? {
        show: true,
        right: 8,
        top: 0,
        iconStyle: { borderColor: '#64748B' },
        emphasis: { iconStyle: { borderColor: '#0F766E' } },
        feature: {
          dataZoom: { yAxisIndex: 'none', title: { zoom: 'Zoom', back: 'Reset zoom' } },
          dataView: { readOnly: true, title: 'View data', lang: ['Data', 'Close', 'Refresh'] },
          restore: { title: 'Restore' },
          saveAsImage: { title: 'Download image', pixelRatio: 2 },
        },
      } : { show: false },
    };
    const hasToolbox = option && typeof option === 'object' && 'toolbox' in option;
    const merged = hasToolbox || !showToolbox ? option : { ...base, ...option, toolbox: (base as any).toolbox };
    chartRef.current?.setOption(merged, true);
  }, [option, height]);

  return <div ref={containerRef} className={className} style={{ width: '100%', height }} role="img" aria-label="Analytics chart" />;
}
