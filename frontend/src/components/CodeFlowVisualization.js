import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './CodeFlowVisualization.css';

const CodeFlowVisualization = ({ codeStructure, currentStep }) => {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!codeStructure || !svgRef.current) return;

    // 清除之前的可视化
    d3.select(svgRef.current).selectAll('*').remove();

    // 设置SVG尺寸和边距
    const width = 600;
    const height = 400;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    // 创建SVG
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // 创建主容器
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // 合并所有代码结构元素
    const allElements = [
      ...codeStructure.functions.map(f => ({ ...f, type: 'function' })),
      ...codeStructure.classes.map(c => ({ ...c, type: 'class' })),
      ...codeStructure.loops.map(l => ({ ...l, type: 'loop' })),
      ...codeStructure.conditionals.map(c => ({ ...c, type: 'conditional' }))
    ].sort((a, b) => a.line - b.line);

    // 如果没有元素，显示提示信息
    if (allElements.length === 0) {
      g.append('text')
        .attr('x', (width - margin.left - margin.right) / 2)
        .attr('y', (height - margin.top - margin.bottom) / 2)
        .attr('text-anchor', 'middle')
        .text('没有可视化的代码结构');
      return;
    }

    // 创建垂直布局
    const yScale = d3.scaleLinear()
      .domain([0, allElements.length - 1])
      .range([0, height - margin.top - margin.bottom]);

    // 绘制连接线
    g.selectAll('.connection')
      .data(allElements.slice(0, -1))
      .enter()
      .append('line')
      .attr('class', 'connection')
      .attr('x1', width / 2 - margin.left - margin.right)
      .attr('y1', (d, i) => yScale(i) + 25)
      .attr('x2', width / 2 - margin.left - margin.right)
      .attr('y2', (d, i) => yScale(i + 1))
      .attr('stroke', '#999')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '5,5');

    // 绘制节点
    const nodes = g.selectAll('.node')
      .data(allElements)
      .enter()
      .append('g')
      .attr('class', 'node')
      .attr('transform', (d, i) => `translate(${width / 2 - margin.left - margin.right}, ${yScale(i)})`);

    // 为节点添加圆形背景
    nodes.append('circle')
      .attr('r', 20)
      .attr('fill', d => {
        // 根据节点类型设置不同颜色
        switch (d.type) {
          case 'function': return '#4285F4';
          case 'class': return '#34A853';
          case 'loop': return '#FBBC05';
          case 'conditional': return '#EA4335';
          default: return '#999';
        }
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    // 为节点添加图标或文本
    nodes.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '.3em')
      .attr('fill', 'white')
      .text(d => {
        switch (d.type) {
          case 'function': return 'F';
          case 'class': return 'C';
          case 'loop': return 'L';
          case 'conditional': return d.type === 'if' ? 'I' : d.type === 'else' ? 'E' : '?';
          default: return '?';
        }
      });

    // 为节点添加标签
    nodes.append('text')
      .attr('x', 30)
      .attr('dy', '.3em')
      .attr('text-anchor', 'start')
      .text(d => d.name || d.type);

    // 高亮当前执行步骤
    if (currentStep && currentStep.line) {
      const currentLine = currentStep.line;
      const closestElement = allElements.reduce((prev, curr) => {
        return (Math.abs(curr.line - currentLine) < Math.abs(prev.line - currentLine)) ? curr : prev;
      }, allElements[0]);

      const index = allElements.indexOf(closestElement);
      if (index !== -1) {
        g.append('circle')
          .attr('cx', width / 2 - margin.left - margin.right)
          .attr('cy', yScale(index))
          .attr('r', 25)
          .attr('fill', 'none')
          .attr('stroke', '#FF5722')
          .attr('stroke-width', 3)
          .attr('stroke-dasharray', '5,5')
          .attr('class', 'current-step-highlight');
      }
    }

  }, [codeStructure, currentStep]);

  return (
    <div className="code-flow-container">
      <svg ref={svgRef} className="code-flow-svg"></svg>
    </div>
  );
};

export default CodeFlowVisualization;