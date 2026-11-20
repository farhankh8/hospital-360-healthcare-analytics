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
    chartRef.current?.setOption(option, true);
  }, [option]);

  return <div ref={containerRef} className={className} style={{ width: '100%', height }} role="img" aria-label="Analytics chart" />;
}
