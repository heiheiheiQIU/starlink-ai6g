/**
 * 演示旁白＋聚光灯（借鉴苗圃杯 demo-mode 的零依赖实现）：
 * - 聚光灯：全屏半透明蒙层用 clip-path 沿目标元素外接矩形"挖洞"（无 canvas 依赖）；
 * - 旁白卡：固定右侧，标题+大白话说明+步骤计数，随步骤切换；
 * - 目标元素缺失时每 300ms 重试（上限 20 次）；resize 时重算；
 * - 全局 prefers-reduced-motion 已把过渡降为 1ms，无需额外处理。
 */

import { useEffect, useRef, useState } from 'react'

import type { FlowStep } from '../domain/flow'

interface DemoOverlayProps {
  visible: boolean
  step: FlowStep
  stepNumber: number
  total: number
  /** 聚光灯目标元素选择器；默认高亮主舞台面板。 */
  targetSelector?: string
}

function holePolygon(rect: DOMRect, viewportWidth: number, viewportHeight: number): string {
  const pad = 12
  const x = Math.max(0, rect.left - pad)
  const y = Math.max(0, rect.top - pad)
  const right = Math.min(viewportWidth, rect.right + pad)
  const bottom = Math.min(viewportHeight, rect.bottom + pad)
  // 外框顺时针 + 洞逆时针，nonzero 规则形成挖空
  return [
    '0 0', `${viewportWidth}px 0`, `${viewportWidth}px ${viewportHeight}px`,
    `0 ${viewportHeight}px`, '0 0',
    `${x}px ${y}px`, `${x}px ${bottom}px`, `${right}px ${bottom}px`,
    `${right}px ${y}px`, `${x}px ${y}px`,
  ].join(', ')
}

export function DemoOverlay({ visible, step, stepNumber, total, targetSelector = '.stage-panel' }: DemoOverlayProps) {
  const [clipPath, setClipPath] = useState<string>('none')
  const retriesRef = useRef(0)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!visible) {
      setClipPath('none')
      return
    }

    const recompute = () => {
      const target = document.querySelector(targetSelector)
      if (!(target instanceof HTMLElement)) {
        if (retriesRef.current < 20) {
          retriesRef.current += 1
          timerRef.current = window.setTimeout(recompute, 300)
        }
        return
      }
      retriesRef.current = 0
      const rect = target.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) {
        timerRef.current = window.setTimeout(recompute, 300)
        return
      }
      setClipPath(
        `polygon(${holePolygon(rect, window.innerWidth, window.innerHeight)})`,
      )
    }

    // 滚动（含内层容器滚动）与缩放都要重算挖窗位置；rAF 节流避免抖动
    let rafId = 0
    const schedule = () => {
      if (rafId !== 0) return
      rafId = window.requestAnimationFrame(() => {
        rafId = 0
        recompute()
      })
    }

    recompute()
    window.addEventListener('scroll', schedule, { capture: true, passive: true })
    window.addEventListener('resize', schedule)
    return () => {
      window.removeEventListener('scroll', schedule, { capture: true })
      window.removeEventListener('resize', schedule)
      if (rafId !== 0) window.cancelAnimationFrame(rafId)
      if (timerRef.current !== null) window.clearTimeout(timerRef.current)
    }
  }, [visible, step.id, targetSelector])

  if (!visible) return null

  return (
    <>
      <div className="demo-spotlight" style={{ clipPath }} aria-hidden="true" data-testid="demo-spotlight" />
      <aside className="demo-narration" role="dialog" aria-label="演示旁白">
        <p className="demo-narration__kicker">DEMO · {String(stepNumber).padStart(2, '0')} / {String(total).padStart(2, '0')}</p>
        <h3>{step.title}</h3>
        <p className="demo-narration__text">{step.narration}</p>
      </aside>
    </>
  )
}
