/**
 * 数字滚动（count-up，借鉴苗圃杯 animateCount 的 rAF+easeOutCubic 思路）。
 * 只用于展示真实后端指标；prefers-reduced-motion 时直接渲染终值。
 */

import { useEffect, useRef, useState } from 'react'

interface CountUpProps {
  value: number
  /** 小数位；null 值不渲染动画（由调用方传占位文本）。 */
  decimals?: number
  durationMs?: number
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

export function CountUp({ value, decimals = 2, durationMs = 900 }: CountUpProps) {
  const [display, setDisplay] = useState(0)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduced) {
      setDisplay(value)
      return
    }
    const startedAt = performance.now()
    const tick = (now: number) => {
      const progress = Math.min(1, (now - startedAt) / durationMs)
      setDisplay(value * easeOutCubic(progress))
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick)
      }
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [value, durationMs])

  return <>{display.toFixed(decimals)}</>
}
