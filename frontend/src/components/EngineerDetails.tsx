import { useState } from 'react'

import type { FlowStep } from '../domain/flow'

interface EngineerDetailsProps {
  step: FlowStep
}

export function EngineerDetails({ step }: EngineerDetailsProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <section className="engineer-details">
      <button
        className="engineer-details__toggle"
        type="button"
        aria-expanded={expanded}
        aria-label={expanded ? '收起工程师详情' : '展开工程师详情'}
        onClick={() => setExpanded((value) => !value)}
      >
        <span>
          <small>ENGINEER VIEW</small>
          <strong>工程接口与追溯信息</strong>
        </span>
        <span>{expanded ? '收起工程师详情' : '展开工程师详情'}</span>
      </button>

      {expanded ? (
        <div className="engineer-details__body">
          <dl>
            <div>
              <dt>工程输入</dt>
              <dd>{step.input}</dd>
            </div>
            <div>
              <dt>工程输出</dt>
              <dd>{step.output}</dd>
            </div>
            <div>
              <dt>追溯产物</dt>
              <dd>{step.artifact}</dd>
            </div>
            <div>
              <dt>数据级别</dt>
              <dd>标准场景演示 · 非实验结果</dd>
            </div>
          </dl>
          <div className="contract-preview" aria-label="工程数据预览">
            <span>{'{'}</span>
            <code>"schema_version": "h00.v1"</code>
            <code>"source_kind": "synthetic_fixture"</code>
            <code>"artifact": "{step.artifact}"</code>
            <span>{'}'}</span>
          </div>
        </div>
      ) : null}
    </section>
  )
}
