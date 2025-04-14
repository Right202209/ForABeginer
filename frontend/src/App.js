import React, { useState, useEffect } from 'react';
import { Controlled as CodeMirror } from 'react-codemirror2';
import axios from 'axios';
import 'codemirror/lib/codemirror.css';
import 'codemirror/theme/material.css';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/mode/python/python';
import 'codemirror/mode/clike/clike';
import './App.css';
import CodeFlowVisualization from './components/CodeFlowVisualization';
import MemoryVisualization from './components/MemoryVisualization';
import VariableTable from './components/VariableTable';

function App() {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(0);
  const [breakpoints, setBreakpoints] = useState(new Set());
  const [isDebugMode, setIsDebugMode] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // 示例代码
  const pythonExample = `# 创建一个列表并进行基本操作
numbers = [64, 34, 25, 12, 22, 11, 90]

# 冒泡排序函数
def bubble_sort(arr):
    n = len(arr)
    # 外层循环控制排序轮数
    for i in range(n):
        # 内层循环进行相邻元素比较和交换
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]

# 对列表进行排序
print("原始列表:", numbers)
bubble_sort(numbers)
print("排序后:", numbers)`;

  const cExample = `#include <stdio.h>

int factorial(int n) {
    // 基本情况：0和1的阶乘为1
    if (n <= 1)
        return 1;
    // 递归计算阶乘
    else
        return n * factorial(n-1);
}

int main() {
    int number = 5;
    int result = factorial(number);
    printf("%d的阶乘是%d\n", number, result);
    return 0;
}`;

  useEffect(() => {
    // 根据选择的语言设置示例代码
    setCode(language === 'python' ? pythonExample : cExample);
  }, [language]);

  useEffect(() => {
    if (result && result.execution_trace) {
      setTotalSteps(result.execution_trace.length);
      setCurrentStep(0);
      if (result.paused_at) {
        setIsPaused(true);
      }
    }
  }, [result]);

  const handleGutterClick = (editor, lineNumber) => {
    const newBreakpoints = new Set(breakpoints);
    if (newBreakpoints.has(lineNumber)) {
      newBreakpoints.delete(lineNumber);
      editor.removeLineClass(lineNumber, 'gutter', 'breakpoint');
    } else {
      newBreakpoints.add(lineNumber);
      editor.addLineClass(lineNumber, 'gutter', 'breakpoint');
    }
    setBreakpoints(newBreakpoints);
  };

  const handleDebugRun = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setIsDebugMode(true);
    setIsPaused(false);
    
    try {
      const response = await axios.post('http://localhost:5000/analyze', {
        code,
        language,
        debug: true,
        breakpoints: Array.from(breakpoints)
      });
      
      setResult(response.data);
    } catch (err) {
      console.error('Error analyzing code:', err);
      setError(err.response?.data?.error || err.message || 'An error occurred while analyzing the code');
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = async () => {
    if (!isPaused || !result) return;
    
    try {
      const response = await axios.post('http://localhost:5000/continue', {
        session_id: result.session_id
      });
      
      setResult(response.data);
      setIsPaused(false);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'An error occurred while continuing execution');
    }
  };

  const handleRunCode = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setIsDebugMode(false);
    setIsPaused(false);
    
    try {
      const response = await axios.post('http://localhost:5000/analyze', {
        code,
        language
      });
      
      setResult(response.data);
    } catch (err) {
      console.error('Error analyzing code:', err);
      setError(err.response?.data?.error || err.message || 'An error occurred while analyzing the code');
    } finally {
      setLoading(false);
    }
  };

  const handleStepForward = () => {
    if (currentStep < totalSteps - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleStepBackward = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleReset = () => {
    setCurrentStep(0);
  };

  const getCurrentStepData = () => {
    if (!result || !result.execution_trace || result.execution_trace.length === 0) {
      return null;
    }
    return result.execution_trace[currentStep];
  };

  return (
    <div className="container">
      <div className="header">
        <h1>代码可视化演示</h1>
        <p>输入C或Python代码，查看代码逻辑和内存状态的可视化展示</p>
      </div>
      
      <div className="select-container">
        <label htmlFor="language-select">选择语言: </label>
        <select 
          id="language-select"
          value={language} 
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="python">Python</option>
          <option value="c">C</option>
        </select>
      </div>
      
      <div className="code-editor">
        <CodeMirror
          value={code}
          options={{
            mode: language === 'python' ? 'python' : 'text/x-csrc',
            theme: 'material',
            lineNumbers: true,
            lineWrapping: true,
            gutters: ['CodeMirror-linenumbers', 'breakpoints']
          }}
          onGutterClick={(editor, lineNumber) => handleGutterClick(editor, lineNumber - 1)}
          onBeforeChange={(editor, data, value) => {
            setCode(value);
          }}
        />
      </div>
      
      <div className="controls">
        <button onClick={isDebugMode ? handleDebugRun : handleRunCode} disabled={loading || !code.trim()}>
          {loading ? '运行中...' : isDebugMode ? '调试运行' : '运行代码'}
        </button>
        <button onClick={() => setIsDebugMode(!isDebugMode)}>
          {isDebugMode ? '退出调试' : '进入调试'}
        </button>
        {isDebugMode && isPaused && (
          <button onClick={handleContinue} disabled={!isPaused}>
            继续执行
          </button>
        )}
      </div>
      
      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}
      
      {loading && <div className="loading">分析代码中...</div>}
      
      {result && (
        <>
          <div className="visualization-container">
            <div className="visualization-panel">
              <h3>代码流程可视化</h3>
              <CodeFlowVisualization 
                codeStructure={result.code_structure} 
                currentStep={getCurrentStepData()} 
              />
            </div>
            
            <div className="visualization-panel">
              <h3>内存状态可视化</h3>
              <MemoryVisualization 
                stepData={getCurrentStepData()} 
                language={language}
              />
            </div>
          </div>
          
          <div className="visualization-panel">
            <h3>变量状态</h3>
            <VariableTable stepData={getCurrentStepData()} />
            
            <div className="step-controls">
              <button onClick={handleReset} disabled={currentStep === 0}>
                重置
              </button>
              <button onClick={handleStepBackward} disabled={currentStep === 0}>
                上一步
              </button>
              <span>{`步骤 ${currentStep + 1} / ${totalSteps}`}</span>
              <button onClick={handleStepForward} disabled={currentStep === totalSteps - 1}>
                下一步
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default App;