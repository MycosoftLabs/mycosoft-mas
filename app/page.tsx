import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="container py-12">
        <h1 className="text-4xl font-bold mb-2">Mycosoft MAS</h1>
        <p className="text-muted-foreground mb-8">Multi-agent orchestration, MYCA dashboard, and workflow automation.</p>

        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/myca">Open MYCA</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/n8n">Open n8n</Link>
          </Button>
        </div>
      </div>
    </main>
  )
}
