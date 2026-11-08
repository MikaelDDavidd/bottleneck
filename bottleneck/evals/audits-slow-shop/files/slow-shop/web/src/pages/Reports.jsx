import React from 'react';
import Chart from 'chart.js/auto';

export default function Reports() {
  return <canvas id="sales" ref={(el) => el && new Chart(el, { type: 'bar', data: { labels: [], datasets: [] } })} />;
}
