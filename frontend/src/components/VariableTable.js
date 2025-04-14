import React from 'react';
import './VariableTable.css';

const VariableTable = ({ stepData }) => {
  // 如果没有步骤数据或变量数据，显示提示信息
  if (!stepData || !stepData.variables || Object.keys(stepData.variables).length === 0) {
    return (
      <div className="variable-table-container empty-table">
        <p>没有可用的变量数据</p>
      </div>
    );
  }

  // 获取变量数据
  const variables = Object.entries(stepData.variables).map(([name, value]) => ({
    name,
    value,
    type: getVariableType(value)
  }));

  return (
    <div className="variable-table-container">
      <table className="variable-table">
        <thead>
          <tr>
            <th>变量名</th>
            <th>类型</th>
            <th>值</th>
          </tr>
        </thead>
        <tbody>
          {variables.map((variable, index) => (
            <tr key={index} className={variable.type === 'reference' ? 'reference-type' : 'primitive-type'}>
              <td>{variable.name}</td>
              <td>{formatType(variable.type, variable.value)}</td>
              <td className="variable-value">{variable.value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// 辅助函数：判断变量类型
const getVariableType = (value) => {
  if (!value) return 'primitive';
  
  // 移除字符串的引号
  const cleanValue = value.replace(/^['"]|['"]$/g, '');
  
  // 判断是否为基本类型
  if (
    /^\d+(\.\d+)?$/.test(cleanValue) || // 数字
    /^(True|False|true|false)$/.test(cleanValue) || // 布尔值
    /^None$|^null$|^undefined$/.test(cleanValue) || // 空值
    /^'.*'$|^".*"$/.test(value) // 字符串
  ) {
    return 'primitive';
  }
  
  return 'reference';
};

// 辅助函数：格式化类型显示
const formatType = (type, value) => {
  if (type === 'primitive') {
    if (/^\d+(\.\d+)?$/.test(value.replace(/^['"]|['"]$/g, ''))) {
      return '数字';
    } else if (/^(True|False|true|false)$/.test(value.replace(/^['"]|['"]$/g, ''))) {
      return '布尔值';
    } else if (/^None$|^null$|^undefined$/.test(value.replace(/^['"]|['"]$/g, ''))) {
      return '空值';
    } else if (/^'.*'$|^".*"$/.test(value)) {
      return '字符串';
    }
    return '基本类型';
  }
  
  if (value.includes('list') || value.includes('array')) {
    return '列表/数组';
  } else if (value.includes('dict') || value.includes('object')) {
    return '字典/对象';
  } else if (value.includes('function')) {
    return '函数';
  }
  
  return '引用类型';
};

export default VariableTable;