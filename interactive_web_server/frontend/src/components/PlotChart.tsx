import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

interface PlotChartProps {
  data: any[];
  layout?: any;
  config?: any;
  className?: string;
  style?: React.CSSProperties;
}

export default function PlotChart({ data, layout = {}, config = {}, className = '', style }: PlotChartProps) {
  const divRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!divRef.current) return;

    const defaultConfig = {
      displayModeBar: true,
      displaylogo: false,
      responsive: true,
      ...config,
    };

    Plotly.newPlot(divRef.current, data, layout, defaultConfig);

    return () => {
      if (divRef.current) {
        Plotly.purge(divRef.current);
      }
    };
  }, [data, layout, config]);

  useEffect(() => {
    const handleResize = () => {
      if (divRef.current) {
        Plotly.Plots.resize(divRef.current);
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return <div ref={divRef} className={className} style={style} />;
}
