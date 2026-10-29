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
          <strong>工程师详情与契约证据</strong>
        </span>
        <span>{expanded ? '收起工程师详情' : '展开工程师详情'}</span>
      </button>

      {expanded ? (
        <div className="engineer-details__body">
          <dl>
            <div>
              <dt>输入契约</dt>
              <dd>{step.input}</dd>
            </div>
            <div>
              <dt>输出契约</dt>
              <dd>{step.output}</dd>
            </div>
            <div>
              <dt>证据产物</dt>
              <dd>{step.artifact}</dd>
            </div>
            <div>
              <dt>数据级别</dt>
              <dd>契约样例 · 非实验结果</dd>
            </div>
          </dl>
          <div className="contract-preview" aria-label="契约样例预览">
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
