import Link from "next/link"

interface AppSlugPageProps {
  params: Promise<{ slug: string }>
}

export default async function AppSlugPage({ params }: AppSlugPageProps) {
  const { slug } = await params

  return (
    <div className="container mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight">App: {slug}</h1>
      <p className="mt-2 text-muted-foreground">This experience is coming soon.</p>

      <div className="mt-6 rounded-lg border p-4">
        <p className="text-sm text-muted-foreground">
          You can return to the apps hub, or try the Spore Tracker which is already live.
        </p>
        <div className="mt-4 flex gap-3">
          <Link className="underline" href="/apps">
            Back to Apps
          </Link>
          <Link className="underline" href="/apps/spore-tracker">
            Open Spore Tracker
          </Link>
        </div>
      </div>
    </div>
  )
}


