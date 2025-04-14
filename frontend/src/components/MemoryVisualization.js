import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './MemoryVisualization.css';

const MemoryVisualization = ({ stepData, language }) => {
  const svgRef = useRef(null);

  useEffect(() => {
    if (!stepData || !stepData.variables || !svgRef.current) return;

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

    // 提取变量数据
    const variables = Object.entries(stepData.variables).map(([name, value]) => ({
      name,
      value,
      type: getVariableType(value, language)
    }));

    // 如果没有变量，显示提示信息
    if (variables.length === 0) {
      g.append('text')
        .attr('x', (width - margin.left - margin.right) / 2)
        .attr('y', (height - margin.top - margin.bottom) / 2)
        .attr('text-anchor', 'middle')
        .text('没有可视化的内存数据');
      return;
    }

    // 区分基本类型和引用类型
    const primitiveVars = variables.filter(v => v.type === 'primitive');
    const referenceVars = variables.filter(v => v.type === 'reference');

    // 绘制内存模型
    // 栈区域 - 存储基本类型和引用
    const stackHeight = height - margin.top - margin.bottom;
    const stackWidth = (width - margin.left - margin.right) * 0.45;
    
    // 堆区域 - 存储引用类型的实际数据
    const heapHeight = stackHeight;
    const heapWidth = stackWidth;
    const heapX = stackWidth + 50;

    // 绘制栈区域背景
    g.append('rect')
      .attr('x', 0)
      .attr('y', 0)
      .attr('width', stackWidth)
      .attr('height', stackHeight)
      .attr('fill', '#e6f7ff')
      .attr('stroke', '#1890ff')
      .attr('stroke-width', 2)
      .attr('rx', 5)
      .attr('ry', 5);

    // 绘制堆区域背景
    g.append('rect')
      .attr('x', heapX)
      .attr('y', 0)
      .attr('width', heapWidth)
      .attr('height', heapHeight)
      .attr('fill', '#f6ffed')
      .attr('stroke', '#52c41a')
      .attr('stroke-width', 2)
      .attr('rx', 5)
      .attr('ry', 5);

    // 添加标签
    g.append('text')
      .attr('x', stackWidth / 2)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .attr('font-weight', 'bold')
      .text('栈 (Stack)');

    g.append('text')
      .attr('x', heapX + heapWidth / 2)
      .attr('y', -5)
      .attr('text-anchor', 'middle')
      .attr('font-weight', 'bold')
      .text('堆 (Heap)');

    // 在栈中绘制变量
    const cellHeight = 40;
    const cellPadding = 10;
    const maxStackItems = Math.floor(stackHeight / (cellHeight + cellPadding));
    const stackItems = [...primitiveVars, ...referenceVars].slice(0, maxStackItems);

    // 绘制栈中的变量
    const stackCells = g.selectAll('.stack-cell')
      .data(stackItems)
      .enter()
      .append('g')
      .attr('class', 'stack-cell')
      .attr('transform', (d, i) => `translate(10, ${i * (cellHeight + cellPadding) + 10})`);

    // 绘制变量框
    stackCells.append('rect')
      .attr('width', stackWidth - 20)
      .attr('height', cellHeight)
      .attr('fill', d => d.type === 'primitive' ? '#bae7ff' : '#d9f7be')
      .attr('stroke', d => d.type === 'primitive' ? '#1890ff' : '#52c41a')
      .attr('stroke-width', 1)
      .attr('rx', 3)
      .attr('ry', 3);

    // 添加变量名
    stackCells.append('text')
      .attr('x', 10)
      .attr('y', cellHeight / 2)
      .attr('dy', '.3em')
      .attr('font-weight', 'bold')
      .text(d => d.name);

    // 添加变量值
    stackCells.append('text')
      .attr('x', stackWidth - 30)
      .attr('y', cellHeight / 2)
      .attr('dy', '.3em')
      .attr('text-anchor', 'end')
      .text(d => d.type === 'primitive' ? d.value : '引用 →');

    // 在堆中绘制引用类型变量
    if (referenceVars.length > 0) {
      const heapCells = g.selectAll('.heap-cell')
        .data(referenceVars)
        .enter()
        .append('g')
        .attr('class', 'heap-cell')
        .attr('transform', (d, i) => `translate(${heapX + 10}, ${i * (cellHeight + cellPadding) + 10})`);

      // 绘制对象框
      heapCells.append('rect')
        .attr('width', heapWidth - 20)
        .attr('height', cellHeight)
        .attr('fill', '#f9f0ff')
        .attr('stroke', '#722ed1')
        .attr('stroke-width', 1)
        .attr('rx', 3)
        .attr('ry', 3);

      // 添加对象值
      heapCells.append('text')
        .attr('x', 10)
        .attr('y', cellHeight / 2)
        .attr('dy', '.3em')
        .text(d => d.value);

      // 绘制从栈到堆的连接线
      g.selectAll('.reference-line')
        .data(referenceVars)
        .enter()
        .append('path')
        .attr('class', 'reference-line')
        .attr('d', (d, i) => {
          const stackIndex = stackItems.findIndex(item => item.name === d.name);
          if (stackIndex === -1) return '';
          
          const startX = stackWidth - 10;
          const startY = stackIndex * (cellHeight + cellPadding) + 10 + cellHeight / 2;
          const endX = heapX + 10;
          const endY = i * (cellHeight + cellPadding) + 10 + cellHeight / 2;
          
          return `M ${startX} ${startY} C ${startX + 30} ${startY}, ${endX - 30} ${endY}, ${endX} ${endY}`;
        })
        .attr('fill', 'none')
        .attr('stroke', '#722ed1')
        .attr('stroke-width', 2)
        .attr('marker-end', 'url(#arrow)');

      // 添加箭头标记
      svg.append('defs').append('marker')
        .attr('id', 'arrow')
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 8)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', '#722ed1');
    }

  }, [stepData, language]);

  // 辅助函数：判断变量类型
  const getVariableType = (value, language) => {
    if (!value) return 'primitive';
    
    // 移除字符串的引号
    const cleanValue = value.replace(/^['"]|['"]$/g, '');
    
    // 判断是否为基本类型
    if (
      /^\d+(\.\d+)?$/.test(cleanValue) || // 数字
      /^(True|False|true|false)$/.test(cleanValue) || // 布尔值
      /^None$|^null$|^undefined$/.test(cleanValue) || // 空值
      (language === 'python' && /^'.*'$|^".*"$/.test(value)) || // Python字符串
      (language === 'c' && /^'.'$/.test(value)) // C字符
    ) {
      return 'primitive';
    }
    
    return 'reference';
  };

  return (
    <div className="memory-container">
      <svg ref={svgRef} className="memory-svg"></svg>
    </div>
  );
};

export default MemoryVisualization;