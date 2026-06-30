import { useEffect, useRef } from 'react'

export default function BackgroundBlobs() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    let t = 0

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const blobs = [
      { x: 0.75, y: 0.1,  r: 0.38, color: [91, 157, 184],  speed: 0.0007, amp: 0.07 },
      { x: 0.15, y: 0.55, r: 0.32, color: [134, 193, 173], speed: 0.0005, amp: 0.06 },
      { x: 0.5,  y: 0.35, r: 0.28, color: [180, 148, 220], speed: 0.0009, amp: 0.05 },
      { x: 0.85, y: 0.7,  r: 0.22, color: [228, 180, 130], speed: 0.0006, amp: 0.08 },
      { x: 0.2,  y: 0.15, r: 0.20, color: [100, 200, 220], speed: 0.0008, amp: 0.06 },
      { x: 0.6,  y: 0.85, r: 0.25, color: [220, 130, 180], speed: 0.0004, amp: 0.07 },
    ]

    const draw = () => {
      t++
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const W = canvas.width
      const H = canvas.height

      blobs.forEach((b, i) => {
        const phase = i * 1.3
        const bx = (b.x + Math.sin(t * b.speed + phase) * b.amp) * W
        const by = (b.y + Math.cos(t * b.speed * 0.7 + phase) * b.amp) * H
        const br = b.r * Math.min(W, H)

        const grad = ctx.createRadialGradient(bx, by, 0, bx, by, br)
        grad.addColorStop(0,   `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.28)`)
        grad.addColorStop(0.4, `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0.14)`)
        grad.addColorStop(1,   `rgba(${b.color[0]},${b.color[1]},${b.color[2]},0)`)

        ctx.beginPath()
        ctx.arc(bx, by, br, 0, Math.PI * 2)
        ctx.fillStyle = grad
        ctx.fill()
      })

      // Aurora shimmer strip
      const shimX = ((Math.sin(t * 0.0004) + 1) / 2) * W
      const shimGrad = ctx.createLinearGradient(shimX - 200, 0, shimX + 200, H * 0.6)
      shimGrad.addColorStop(0,   'rgba(180,210,255,0)')
      shimGrad.addColorStop(0.4, 'rgba(200,230,255,0.07)')
      shimGrad.addColorStop(0.6, 'rgba(180,210,255,0.04)')
      shimGrad.addColorStop(1,   'rgba(180,210,255,0)')
      ctx.fillStyle = shimGrad
      ctx.fillRect(0, 0, W, H * 0.7)

      animId = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <div className="bg-blobs" aria-hidden="true">
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          filter: 'blur(32px)',
        }}
      />
      <div className="grain-overlay" />
    </div>
  )
}
